import json
from pathlib import Path
from typing import Literal
import argparse

from components import DocSummary

from ATRIUM_T3_4_IE_pipeline import get_configured_pipeline

from json import JSONDecoder
from functools import partial

# https://stackoverflow.com/a/21709058
def json_parse(fileobj, decoder=JSONDecoder(), buffersize=2048):
    buffer = ''
    for chunk in iter(partial(fileobj.read, buffersize), ''):
        buffer += chunk
        while buffer:
            try:
                result, index = decoder.raw_decode(buffer)
                yield result
                buffer = buffer[index:].lstrip()
            except ValueError:
                # Not enough data to decode, read more
                break

def process(input_path: Path, output_path: Path, language: Literal["en", "fr", "de", "es"] = "en"):

    print(language)
    
    nlp = get_configured_pipeline(language)

    with open(output_path, "w") as file:

        with input_path.open() as f:

            for record in json_parse(f):
            
                text = record.get("text", "")        

                if(len(text) > 0):            
                    # get the spans identified by the pipeline
                    doc = nlp(text)            
                    summary = DocSummary(doc)
                    if "spans" in record: 
                        record["spans"].extend(summary.spans_to_list())
                    else:
                        record["spans"] = summary.spans_to_list()

                file.write(f"{json.dumps(record)}\n")

if __name__ == "__main__":
    
    # initiate the input arguments parser
    parser = argparse.ArgumentParser(
        prog=__file__, description="ATRIUM T3.4 Temporal IE Component")

    # add long and short argument descriptions for input file path (directory containing files to be processed)
    parser.add_argument(
        "--input", "-i", 
        required=True,
        help="Input JSON File to process")
    
    # add long and short argument descriptions for output file path (directory to write processed files to)
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output JSON file")

    parser.add_argument(
        "--language", "-l",
        required=False,
        choices=["en", "fr", "de", "es"],
        default="en",
        help="Language to use for processing (default is 'en')")
    
    # parse and clean command line arguments
    args = parser.parse_args()
    input_path: Path = Path(args.input.strip())
    output_path: Path = Path(args.output.strip())
    
    # create the spaCy pipeline to use
    process(input_path, output_path, language=args.language)