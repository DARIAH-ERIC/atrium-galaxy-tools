import easyocr
import sys
import json
from os import listdir
from os.path import isfile, join
import warnings

import argparse

import cv2
import xml.etree.ElementTree as ET
from xml.dom import minidom

# strangely EasyOCR pins the memory even when we set GPU to false which
# results in a warning message, so we supress it to avoid confusding people
warnings.filterwarnings(
    "ignore",
    message=".*'pin_memory' argument is set as true but no accelerator is found.*",
)

class EasyOCR:

    def __init__(self, args):
        self.paragraphs = args.paragraphs
        self.reader = easyocr.Reader(args.language, gpu=args.gpu)


    def process(self, in_file):

        return self.reader.readtext(in_file,paragraph=self.paragraphs)


    def get_image_dimensions(self, image_path):
        """Reads the image to get pixel dimensions"""
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Could not load image at {image_path}")
        height, width, _ = img.shape
        return width, height


    def write_txt(self, in_files, out_file, pages):
        """Write the OCR result out as plain text"""

        text = []

        for page in pages:
            text.append(" ".join([r[1] for r in page]))

        with open(out_file+".txt", "w") as f:
            f.write("\n\n".join(text))


    def write_jsonl(self, in_files, out_file, pages):
        """Write the OCR result out as TIDES JSONL"""
        
        with open(out_file+".json", "w") as f:
            for page in pages:

                bounding_boxes = []
                text = ""
        
                for r in page:
                    bounding_boxes.append({
                        "content": r[1],
                        "box": r[0]
                    })
                    text = text + " " + r[1]
        
                document = {
                    "meta": {
                        "bounding_boxes": bounding_boxes
                    },
                    "text": text.strip()
                }

                f.write(f"{json.dumps(document, default=int)}\n")


    def write_alto(self, in_files, out_file, pages):
        """Writes the OCR result as ALTO XML"""

        # note that this was generated mostly by Google Gemini.
        # it looks like it works but it needs testing properly
        # and the output validating against the ALTO schema

        # 2. Build Base XML Structure (ALTO v3 Namespace)
        ns = "http://loc.gov"
        ET.register_namespace("", ns)

        root = ET.Element(
            f"{{{ns}}}alto",
            {
                "xmlns:xsi": "http://w3.org",
                "xsi:schemaLocation": f"{ns} http://loc.gov",
            },
        )

        # Description Section (Metadata)
        description = ET.SubElement(root, f"{{{ns}}}Description")
        measurement = ET.SubElement(description, f"{{{ns}}}MeasurementUnit")
        measurement.text = "pixel"

        # Layout Section (This container will host all our separate pages)
        layout = ET.SubElement(root, f"{{{ns}}}Layout")

        source_info = ET.SubElement(description, f"{{{ns}}}sourceImageInformation")

        for page_idx, image_path in enumerate(in_files):

            # Get metadata per image file
            img_width, img_height = self.get_image_dimensions(image_path)

            # Create a new Page element
            page = ET.SubElement(
                layout,
                f"{{{ns}}}Page",
                {
                    "ID": f"PAGE_{page_idx}",
                    "HEIGHT": str(img_height),
                    "WIDTH": str(img_width),
                    "PHYSICAL_IMG_NR": str(page_idx),
                },
            )

            # Canvas bounding box wrapper
            print_space = ET.SubElement(
                page,
                f"{{{ns}}}PrintSpace",
                {
                    "HEIGHT": str(img_height),
                    "WIDTH": str(img_width),
                    "HPOS": "0",
                    "VPOS": "0",
                },
            )

            # Core paragraph block segment
            text_block = ET.SubElement(
                print_space,
                f"{{{ns}}}TextBlock",
                {
                    "ID": f"BLOCK_P{page_idx}_B0",
                    "HEIGHT": str(img_height),
                    "WIDTH": str(img_width),
                    "HPOS": "0",
                    "VPOS": "0",
                },
            )

            # Run model inference on active file target
            ocr_results = pages[page_idx]

            # 4. Map EasyOCR items into this page's layout
            for line_idx, (bbox, text, confidence) in enumerate(ocr_results):
                xs = [pt[0] for pt in bbox]
                ys = [pt[1] for pt in bbox]

                hpos = int(min(xs))
                vpos = int(min(ys))
                width = int(max(xs) - hpos)
                height = int(max(ys) - vpos)

                # Generate individual TextLine
                text_line = ET.SubElement(
                    text_block,
                    f"{{{ns}}}TextLine",
                    {
                        "ID": f"LINE_P{page_idx}_{line_idx}",
                        "HPOS": str(hpos),
                        "VPOS": str(vpos),
                        "WIDTH": str(width),
                        "HEIGHT": str(height),
                    },
                )

                # Generate matching underlying element text string
                ET.SubElement(
                    text_line,
                    f"{{{ns}}}String",
                    {
                        "ID": f"STR_P{page_idx}_{line_idx}",
                        "CONTENT": text,
                        "WC": f"{confidence:.4f}",
                        "HPOS": str(hpos),
                        "VPOS": str(vpos),
                        "WIDTH": str(width),
                        "HEIGHT": str(height),
                    },
                )

        # 5. Format & Save output XML with pretty indentation
        xml_str = ET.tostring(root, encoding="utf-8")
        parsed_xml = minidom.parseString(xml_str)
        pretty_xml_str = parsed_xml.toprettyxml(indent="    ", encoding="utf-8")

        with open(out_file+".xml", "wb") as f:
            f.write(pretty_xml_str)


    def write_hocr(self, in_files, out_file, pages):
        
        # 1. Create Root Node (html) with namespaces
        # Note: ElementTree handles the default namespace via the '{}' prefix pattern or registering it
        XHTML_NS = "http://www.w3.org/1999/xhtml"
        ET.register_namespace('', XHTML_NS)
        
        root = ET.Element(f"{{{XHTML_NS}}}html", attrib={
            "lang": "en",
            f"{{http://www.w3.org/1999/xhtml}}lang": "en"
        })
        
        # 2. Build Head
        head = ET.SubElement(root, f"{{{XHTML_NS}}}head")
        title = ET.SubElement(head, f"{{{XHTML_NS}}}title")
        title.text = "EasyOCR to hOCR Conversion"
        
        ET.SubElement(head, f"{{{XHTML_NS}}}meta", attrib={"http-equiv": "Content-Type", "content": "text/html;charset=utf-8"})
        ET.SubElement(head, f"{{{XHTML_NS}}}meta", attrib={"name": "ocr-system", "content": "EasyOCR"})
        ET.SubElement(head, f"{{{XHTML_NS}}}meta", attrib={"name": "ocr-capabilities", "content": "ocr_page ocr_carea ocr_line ocrx_word"})
        
        # 3. Build Body and Page Frame
        body = ET.SubElement(root, f"{{{XHTML_NS}}}body")

        for page_idx, image_path in enumerate(in_files):
        
            # Get metadata per image file
            img_width, img_height = self.get_image_dimensions(image_path)

            page_title = f"image '{image_path}'; bbox 0 0 {img_width} {img_height}; ppageno 0"
            page_div = ET.SubElement(body, f"{{{XHTML_NS}}}div", attrib={"class": "ocr_page", "id": "page_1", "title": page_title})

            # Run model inference on active file target
            ocr_results = pages[page_idx]
            
            # 4. Parse EasyOCR boxes into XML Elements
            for idx, (bbox, text, confidence) in enumerate(ocr_results):
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                x_min, y_min = int(min(x_coords)), int(min(y_coords))
                x_max, y_max = int(max(x_coords)), int(max(y_coords))
                
                bbox_str = f"bbox {x_min} {y_min} {x_max} {y_max}"
                
                carea = ET.SubElement(page_div, f"{{{XHTML_NS}}}p", attrib={"class": "ocr_carea", "id": f"block_1_{idx}", "title": bbox_str})
                line = ET.SubElement(carea, f"{{{XHTML_NS}}}span", attrib={"class": "ocr_line", "id": f"line_1_{idx}", "title": bbox_str})
                
                word_title = f"{bbox_str}; x_wconf {int(confidence * 100)}"
                word = ET.SubElement(line, f"{{{XHTML_NS}}}span", attrib={"class": "ocrx_word", "id": f"word_1_{idx}", "title": word_title})
                word.text = text # Safe formatting automatically applied here
            
        # 5. Serialize to string
        # We use indent() for human-readable pretty-printing (Python 3.9+)
        try:
            ET.indent(root, space="  ", level=0)
        except AttributeError:
            pass # Fallback for Python versions older than 3.9
            
        raw_xml = ET.tostring(root, encoding="utf-8", method="xml").decode("utf-8")
        
        # 6. Append Doctype manually since ElementTree serialization skips XHTML standard doctypes
        doctype = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://w3.org">\n'
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'

        with open(out_file+".hocr", "w") as f:
            f.write(xml_declaration + doctype + raw_xml)



if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="EasyOCR", description="Extract text from an image using EasyOCR")

    parser.add_argument("--input", 
        action="append",
        required=True,
        help="Image file to process")
    
    parser.add_argument("--output",
        required=True,
        help="base filename to write to (extension will be added based on output format)")

    parser.add_argument("--format",
        action="append",
        choices=['txt',"jsonl","alto","hocr"],
        help="the output formats to write (if not specified JSONL will be produced)")
        
    parser.add_argument("--paragraphs", action="store_true",
        help="Group text into pragraphs (default is to treat each line separately)")
    parser.add_argument("--gpu", action="store_true",
        help="Use GPU for OCR (default is to use CPU)")

    parser.add_argument("--language", action="append",
        required=True,
        help="Language models to use for OCR ")

    args = parser.parse_args()

    client = EasyOCR(args);

    pages = [client.process(in_file) for in_file in args.input]

    if args.format:
        for f in args.format:
            write_output = getattr(client, f"write_{f}")
            write_output(args.input, args.output, pages)
    else:
        client.write_jsonl(args.input, args.output, pages)