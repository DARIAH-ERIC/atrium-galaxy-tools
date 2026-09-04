import easyocr
import sys
import json
from os import listdir
from os.path import isfile, join

import argparse

class EasyOCR:

    def __init__(self, args):
        self.reader = easyocr.Reader(['en'], gpu=args.gpu)

    def process(self, in_file, out_file, paragraphs=False):

        result = self.reader.readtext(in_file, paragraph=paragraphs)

        bounding_boxes = []
        text = ""

        for r in result:
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

        return document


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="EasyOCR", description="Extract text from an image using EasyOCR")

    parser.add_argument("--input", 
        action="append",
        help="Image file to process")
    parser.add_argument("--output",
        help="JSON file to write text into")
        
    parser.add_argument("--paragraphs", action="store_true",
        help="Group text into pragraphs (default is to treat each line separately)")
    parser.add_argument("--gpu", action="store_true",
        help="Use GPU for OCR (default is to use CPU)")

    args = parser.parse_args()

    client = EasyOCR(args);

    with open(args.output, "w") as f:
        for in_file in args.input:
            result = client.process(in_file, args.output, paragraphs=args.paragraphs)
            f.write(f"{json.dumps(result, default=int)}\n")
