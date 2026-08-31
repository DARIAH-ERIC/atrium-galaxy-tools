import json
from pathlib import Path
from typing import Literal
import argparse

from spacy.tokens import Doc
from spacy.language import Language
from datetime import datetime as DT # for timestamps
from components import DocSummary, SpanScorer
from ATRIUM_T4_1_2_IE_pipeline import create_configured_pipeline

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

def run_pipeline(nlp: Language, input_data: dict={}) -> Doc: 
    # run the IE pipeline on the 'text' property of the input
    doc = nlp(input_data.get("text",""))
    # add calculated scores to spans
    sections = list(input_data.get("sections", []))    
    scorer = SpanScorer(nlp, sections=sections)
    doc = scorer(doc)
    # return the document
    return doc

def generate_report(
    doc: Doc,
    metadata: dict={},
    sections: list = []) -> dict:
    
    summary = DocSummary(doc, metadata=metadata)
    
    report = summary.report_to_json() 
    report["sections"] = sections

    return report

# run configured information extraction pipeline on specified set of input documents
def run_information_extraction(
    nlp: Language,          # pre-configured spaCy pipeline 
    input_path: Path,       # path to input JSON file
    output_path: Path,      # path to output JSON file
    ): 
    
    entry = input_path
    
    print(f"Reading file '{entry.name}'...")
    #file_content = get_file_content(entry)

    with open(output_path, "w") as file:

        with entry.open() as f:    
            for file_content in json_parse(f):

                # get any existing metadata from the input file       
                old_metadata: dict = file_content.get("meta", {})      
                # set up new metadata to include in the output
                new_metadata: dict = {
                    #"identifier": entry.name,
                    "title": "vocabulary-based IE results",
                    #"description": f"vocabulary-based information extraction results for file '{entry.name}'",
                    #"creator": __file__, 
                    #"created": DT.now().isoformat(),
                    "pipeline": nlp.pipe_names,
                    #"input_file_name": entry.name
                }
                # merge with existing metadata in input_file_content 
                metadata: dict = {**old_metadata, **new_metadata}
                file_content["meta"] = metadata
                
                # run the IE pipeline on the 'text' property of the input 
                print(f"Running IE pipeline on '{entry.name}'...")        
                doc = run_pipeline(nlp, file_content)

                # write results to output file
                #output_file_name = Path(output_path).joinpath(f"ie-output-{slugify(entry.name)}")
                output_file_name = output_path
                print(f"Creating report '{output_file_name}'...")  
                ts_out = DT.now()        
                
                report = generate_report(
                    doc=doc,
                    metadata=file_content.get("meta",{}),
                    sections=file_content.get("sections", []))

                file.write(f"{json.dumps(report)}\n")
    
    print(f"finished creating report in {DT.now() - ts_out}")

    print(f"Finished running {__file__}")


if __name__ == "__main__":
    
    # initiate the input arguments parser
    parser = argparse.ArgumentParser(
        prog=__file__, description="ATRIUM T4.1.2 IE Component")

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
    
    # parse and clean command line arguments
    args = parser.parse_args()
    input_path: Path = Path(args.input.strip())
    output_path: Path = Path(args.output.strip())
    
    # create the spaCy pipeline to use
    print("Creating configured pipeline")
    pipeline = create_configured_pipeline() 
    print("Created configured pipeline")

    # run the pipeline using cleaned input args
    print("Running information extraction")
    run_information_extraction(
        nlp = pipeline,
        input_path = input_path,
        output_path = output_path
    )
    print("Finished information extraction")