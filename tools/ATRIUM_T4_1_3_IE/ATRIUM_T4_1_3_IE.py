import json
import spacy # for text processing
from spacy.tokens import Span

import os

import argparse

from components import DocSummary # custom vocabulary-based components
from components.Util import read_json_file # for reading supplementary lists from JSON files

from json import JSONDecoder
from functools import partial
from pathlib import Path

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


# check if a given span exists in a list of spans
# comparing start/end positions and label
def span_exists(span: dict, lst: list) -> bool:
   return any(
        item["start"] == span.get("start", 0)
        and item["end"] == span.get("end", 0) 
        and item["label"] == span.get("label", "") for item in lst
    )           


if __name__ == '__main__':

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

    # default vocabulary patterns defined here
    # these may be overriden by local files 
    vocab_folder = os.path.join(os.path.dirname(__file__),"vocabularies")

    # set up default base pipeline (English)
    nlp = spacy.load("en_core_web_sm", disable = ['ner'])
    supp_list_act = read_json_file(f"{vocab_folder}/supp_list_AAT_ACTIVITIES.json")
    
    # add custom pipeline components
    nlp.add_pipe("text_normalizer", before = "tagger")

    # object types (from FISH object types vocabulary)
    nlp.add_pipe(
        "vocabulary_ruler", 
        name = "fish_event_types_ruler",
        last = True, 
        config = {
            "default_label": "FISH_EVENT",
            "lemmatize": True,
            "min_lemm_length": 4,
            "min_term_length": 3,
            "patt_list": read_json_file(f"{vocab_folder}/patterns_FISH_agl_et_20260513.json")
        }
    ) 

    nlp.add_pipe(
        "vocabulary_ruler", 
        name = "fish_arch_sciences_ruler",
        last = True, 
        config = {
            "default_label": "FISH_ARCHSCIENCE",
            "lemmatize": True,
            "min_lemm_length": 4,
            "min_term_length": 3,
            "patt_list": read_json_file(f"{vocab_folder}/patterns_FISH_560_20260513.json")
        }
    ) 

    nlp.add_pipe(
        "vocabulary_ruler", 
        name = "fish_sctivities_ruler",
        last = True, 
        config = {
            "default_label": "AAT_ACTIVITY",
            "lemmatize": True,
            "min_lemm_length": 4,
            "min_term_length": 3,
            "patt_list": read_json_file(f"{vocab_folder}/patterns_AAT_ACTIVITIES_20231018.json")
        }
    ) 
    
    nlp.add_pipe("child_span_remover", last=True) 

    input_path: Path = Path(args.input.strip())
    output_path: Path = Path(args.output.strip())

    with open(output_path, "w") as file:

        with input_path.open() as f:    
            for item in json_parse(f):

                identifier = item.get("meta", {}).get("id", "").strip()
                text = item.get("text", "")
                # run pipeline against input text
                doc = nlp(text)

                # display HTML summary of results (see below)
                summary = DocSummary(doc)

                # add new spans to the existing spans array,
                # checking for duplicates (in case multiple runs)
                the_spans: list = item.get("spans", []) 
                new_spans = summary.spans_to_list()
                for span in new_spans:
                    if not span_exists(span, the_spans):
                        the_spans.append(span)
                item["spans"] = the_spans
                #item["tokens2"] = summary.tokens_to_list()

                file.write(f"{json.dumps(item)}\n")