# Shared runtime image for all ATRIUM Galaxy tools.
#
# The goal of this image is to provide one stable execution environment for
# the local ATRIUM tools when they are executed by Galaxy's Kubernetes runner.
#
# Galaxy mounts the actual tool source code from:
#   /galaxy/server/database/local_tools
#
# Therefore this image deliberately does NOT copy the Galaxy XML wrappers or
# Python tool source code into the container. It only provides the runtime
# dependencies required by those tools.
#
# NOTE ABOUT PYTHON VERSION:
# Some current ATRIUM wrappers require Python 3.14.6, while the NER tool and
# spaCy Data Manager require Python 3.12.x. A single runtime image should use
# one Python version, so the wrappers should ideally be aligned to the same
# supported Python release.
#
# Python 3.12.13 is used here because it matches the NER/runtime stack and is
# generally a safer common denominator for spaCy/transformers dependencies.
FROM python:3.12.13-slim


# Install system-level runtime dependencies.
#
# These are mainly required by OCRmyPDF and Tesseract-based PDF processing.
#
# tesseract-ocr:
#   OCR engine used by atrium_pdf_text_extraction.
#
# ghostscript:
#   Used internally by OCRmyPDF for PDF processing.
#
# qpdf:
#   Used by OCRmyPDF for PDF validation and manipulation.
#
# pngquant / unpaper:
#   Optional image preprocessing utilities used by OCR workflows.
#
# libgl1 / libglib2.0-0:
#   Common runtime libraries required by Python imaging/NLP packages and
#   their native extensions.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        ghostscript \
        qpdf \
        pngquant \
        unpaper \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*


# Install all Python dependencies required by the current ATRIUM tools.
#
# The versions are based on the <requirements> sections in the Galaxy XML
# wrappers in the atrium-galaxy-tools repository.
#
# Keeping the versions pinned makes the runtime reproducible and avoids a
# tool silently changing behaviour when upstream packages publish new
# releases.
RUN python -m pip install --no-cache-dir \
    spacy==3.8.14 \
    spacy-transformers==1.4.0 \
    click==8.4.1 \
    pandas==3.0.3 \
    jsonpath-ng==1.8.0 \
    regex==2026.5.9 \
    unidecode==1.4.0 \
    requests==2.34.2 \
    pypdf==6.1.3 \
    ocrmypdf==17.7.0 \
    fpdf2==2.8.4 \
    huggingface_hub==0.36.0 \
    transformers==4.53.2


# Install the default English spaCy model used by the IE tools.
#
# In Galaxy this model is declared as:
#   spacy-model-en_core_web_sm 3.8.0
#
# The pip/package naming is different from the Galaxy/Conda package name,
# therefore we install it through spaCy itself.
#
# If model installation is fully delegated to the Galaxy spaCy Data Manager,
# this step can be removed later.
RUN python -m spacy download en_core_web_sm


# Validate the Python runtime during the image build.
#
# This intentionally fails the Docker build if one of the core ATRIUM
# dependencies cannot be imported. That is much better than discovering a
# missing dependency only after Galaxy launches a Kubernetes job.
RUN python - <<'PY'
import sys

import click
import pandas
import jsonpath_ng
import regex
import requests
import pypdf
import ocrmypdf
import fpdf
import spacy
import spacy_transformers
import huggingface_hub
import transformers

print("Python:", sys.version)
print("spaCy:", spacy.__version__)
print("pypdf:", pypdf.__version__)
print("OCRmyPDF:", ocrmypdf.__version__)
print("Transformers:", transformers.__version__)
print("ATRIUM Python runtime dependency check: OK")
PY


# Verify that the OCR executable is also present.
RUN tesseract --version | head -1


# Galaxy's Kubernetes runner provides the actual command that should be
# executed for each tool.
#
# We therefore remove any application-specific entrypoint and leave the image
# as a generic runtime container.
ENTRYPOINT []

CMD ["/bin/bash"]