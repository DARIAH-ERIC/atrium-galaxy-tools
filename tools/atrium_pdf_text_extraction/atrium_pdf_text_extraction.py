#raw
import json
import argparse
from typing import IO, Any
from pathlib import Path
from pypdf import PdfReader
def convert(file: str|IO[Any]|Path):
    """Extracts the text in a PDF file into a dict that can be saved as JSON
    Specifically it extracts the text from a PDF one page at a time, storing
    the text into a single string and recording offset information about certain
    section types. Currently the sections are page, body, and end_matter.
    Args:
        file: A File object or an object that supports the standard read
              and seek methods similar to a File object. Could also be a
              string representing a path to a PDF file.
    Returns:
        A dict with top level elements meta, text, and sections.
    """
    # this will hold all the text we extract from the PDF
    text = ""
    # holds the section annotations
    sections = []
    # the start offset of the current page
    page_start = 0
    # the offset where the end matter starts
    end_matter_start = -1
    # read in the PDF file ready for processing
    reader = PdfReader(file)
    for number, page in enumerate(reader.pages, start=1):
        # although it may seem odd to process each page in turn
        # we do this as apparently it works better for multi-column
        # PDFs rather than just pulling the full text context.
        # extract the text for this page
        page_text = page.extract_text()
        # the offset of the end of the page must be the offset of
        # the start of the page plus the length of the extracted text
        page_end = page_start + len(page_text)
        # add a section describing the page
        sections.append({"start": page_start, "end": page_end, "type": "page", "number": number})
        if end_matter_start == -1:
            # if we are still in the main body of the article then...
            # find the offsets of any of the end matter section titles
            offsets = [page_text.find(title) for title in ["BIBLIOGRAPHY", "REFERENCES", "APPENDIX"]]
            offsets = list(filter(lambda x: (x != -1), offsets))
            if len(offsets) > 0:
                # if we've found the start of the end matter then...
                # record the body section
                sections.append({"start": 0, "end": page_start + min(offsets), "type": "body"})
                # record where then end matter starts so we can add a section for it
                # once we get top the end of the document
                end_matter_start = page_start + min(offsets)
        # add the text to the end of everything we'd collected from previous pages
        # plus two new line separators just for clarity purposes. Note that those
        # two characters aren't included in the offsets for the page section
        text = text + page_text + "\n\n"
        # work out where the next page starts ready for processing it
        page_start = len(text)
    # we will have added two extra new line characters to the end of the document
    # which we might as well strip of rather than leaving them randomly hanging
    text = text.rstrip()
    # if we found some end matter then add a section describing it
    if end_matter_start != -1:
        sections.append({"start": end_matter_start, "end": len(text), "type": "end_matter"})
    # return a dict in the agreed format that we can then dump to JSON
    return {
        "meta": {
            "ocr": False
        },
        "text": text,
        "sections": sections
    }
if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="ATRIUM PDF Text Extraction")
    parser.add_argument("--pdf",
        help="PDF to extract text from", required=True)
    parser.add_argument("--json",
        help="JSON file to write output into", required=True)
    parser.add_argument("--ocr", action="store_true",
        help="Run OCR before extracting text")
    args = parser.parse_args()
    if args.ocr:
        # we've been asked to OCR the PDF prior to extracting the text
        import tempfile
        import ocrmypdf
        with tempfile.TemporaryFile() as tmpFile:
            # we're going to store the updated PDF into a tmp file
            # and we are forcing a redo of the OCR and hence ignoring
            # any existing text in there
            ocrmypdf.ocr(args.pdf, tmpFile, redo_ocr=True)
            # now do the extraction as befoe
            result = convert(tmpFile)
            # make sure we use the original PDF filename in the output
            #result["meta"]["filename"] = args.pdf
            result["meta"]["ocr"] = True
    else:
        # just process the PDF file as normal
        result = convert(args.pdf)

    with open(args.json, "w", encoding="utf-8") as f:
        f.write(f"{json.dumps(result)}\n")
#end raw
