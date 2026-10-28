import easyocr
import sys
import json
from os import listdir
from os.path import isfile, join
import warnings

import argparse

import cv2

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


    def get_image_dimensions(image_path):
        """Reads the image to get pixel dimensions"""
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Could not load image at {image_path}")
        height, width, _ = img.shape
        return width, height


    def write_txt(self, out_file, pages):
        """Write the OCR result out as plain text"""

        text = []

        for page in pages:
            text.append(" ".join([r[1] for r in page]))

        with open(out_file+".txt", "w") as f:
            f.write("\n\n".join(text))


    def write_jsonl(self, out_file, pages):
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
        choices=['txt',"jsonl"],
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
            write_output(args.output, pages)
    else:
        client.write_jsonl(args.output, pages)