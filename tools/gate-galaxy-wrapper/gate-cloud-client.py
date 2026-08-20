import base64
import requests
import logging
import json
import argparse
import sys

from pathlib import Path

import time

from typing import Optional

from json import JSONDecoder
from functools import partial

logger = logging.getLogger(__name__)

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


class GateClient:

    def __init__(self, args, credentials):
        self.prev_rate_limit_remaining = -1
        self.request_start_time: Optional[float] = None

        self.endpoint = args.endpoint

        logger.info("Using GATE Cloud endpoint: %s", self.endpoint)
        
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "text/plain"
        self.session.headers["Accept"] = "application/json"
        if credentials:
            auth_header = "Basic " + base64.b64encode(bytes(credentials, "utf-8")).decode("ascii")
            self.session.headers["Authorization"] = auth_header


    def handle_rate_limit(self, response: requests.Response) -> float:
        # Logic:
        #
        # - if we've already hit the rate limit or quota then just wait until the retry time
        # - otherwise take the max of this request cost and the difference between remaining rate limit
        #   after this request and the remaining rate limit after the previous call (which might be more than
        #   one call used up if there's another run going in parallel)
        # - divide the time until rate limit reset by this number to get the wait time between calls that should
        #   "use up" that rate limit precisely by the reset time, and multiply by 1.05 so we don't actually hit
        #   the limit
        # - actual wait time before starting the next call is then this time minus "now" plus the time that
        #   this request _started_ (so we're limiting the start-to-start times rather than the end-to-start)
        # - if the final result is less than 0, return 0 (i.e. no need to wait at all)
        try:
            if (response.status_code == 429 or response.status_code == 402) and ("retry-after" in response.headers):
                # already hit the rate limit
                logger.info("Rate limit reached - waiting %s seconds", response.headers["retry-after"])
                return float(response.headers["retry-after"])

            try:
                this_rate_limit_remaining = int(response.headers["x-gate-rate-limit-calls"])
                time_until_reset = int(response.headers["x-gate-rate-limit-reset"])
            except ValueError:
                return 0.0

            used_limit_since_last_call = 1
            if 0 < self.prev_rate_limit_remaining < this_rate_limit_remaining:
                used_limit_since_last_call = this_rate_limit_remaining - self.prev_rate_limit_remaining
            self.prev_rate_limit_remaining = this_rate_limit_remaining

            wait_time_until_next_call = (
                (time_until_reset / this_rate_limit_remaining) * used_limit_since_last_call * 1.05
            )
            if self.request_start_time:
                wait_time_until_next_call += self.request_start_time - time.perf_counter()

            if wait_time_until_next_call > 0:
                return wait_time_until_next_call
            else:
                return 0.0
        finally:
            response.close()


    def run(self, in_file, out_file):
        logger.info("Reading input file '%s'", in_file)

        with open(out_file, "w") as file:
        
            with in_file.open() as f:    
                for file_content in json_parse(f):
        
                    text = file_content["text"]

                    # setup counters to deal with rate limiting
                    rate_limit_failures = 0
                    wait_before_next_call = 0.0


                    while True:

                        self.request_start_time = time.perf_counter()
                        
                        response = self.session.post(self.endpoint, data=text)

                        if response.status_code == 200:
                            gate_json = response.json()

                            spans = []

                            for entity_type, entities in gate_json["entities"].items():
                                for entity in entities:
                                    indices = entity.pop("indices")

                                    spans.append({
                                        "label": entity_type,
                                        "start": indices[0],
                                        "end": indices[1],
                                        "span_text": text[indices[0]:indices[1]],
                                        "features": entity
                                    })
                            break
                        elif response.status_code == 429 or response.status_code == 402:
                            # Rate limit or quota has been hit
                            rate_limit_failures += 1
                            if rate_limit_failures > 5:
                                # something is very wrong, give up
                                logger.error(response.text)
                                sys.exit(1)
                            wait_before_next_call = self.handle_rate_limit(response)
                        else:
                            # Genuine error response
                            logger.error(response.text)
                            sys.exi(1)

                        if wait_before_next_call > 5.0:
                            logger.info(
                                "Waiting %.2f seconds before next API call for rate limiting",
                                wait_before_next_call,
                            )
                        time.sleep(wait_before_next_call)


                    if "spans" in file_content:
                        file_content["spans"].extend(spans)
                    else:
                        file_content["spans"] = spans

                    file.write(f"{json.dumps(file_content)}\n")


def main():
    parser = argparse.ArgumentParser("GATE Cloud Client")

    parser.add_argument(
        "--endpoint",
        required=True,
        help="GATE Cloud endpoint to call, typically copied from the 'Use this pipeline' section on GATE Cloud.",
    )

    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input JSON File to process"
    )

    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output JSON File "
    )

    creds_group = parser.add_argument_group("API credentials", "Provide credentials for the GATE Cloud API.")
    creds_group.add_argument("--api-key", help="API key ID from cloud.gate.ac.uk")
    creds_group.add_argument("--api-password", help="API key password from cloud.gate.ac.uk")

    args = parser.parse_args()

    credentials = f"{args.api_key}:{args.api_password}" if args.api_key and args.api_password else None

    client = GateClient(args, credentials)

    client.run(Path(args.input.strip()), Path(args.output.strip()))

if __name__ == "__main__":
    main()