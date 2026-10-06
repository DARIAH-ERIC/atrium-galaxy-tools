FROM quay.io/galaxyproject/galaxy-min:26.1.1

USER root
RUN /galaxy/server/.venv/bin/python -m pip install --no-cache-dir iiif-fsspec==0.1.1 \
    && /galaxy/server/.venv/bin/python -c "import iiif_fsspec"

USER galaxy

# Download the three different flavours of data for use with Tesseract.
# Note that even with these included in the image the Data Table will still
# need to be updated to reference these folders.
ADD --chown=galaxy:galaxy https://github.com/tesseract-ocr/tessdata.git /galaxy/server/database/tool-data/tesseract/tessdata
ADD --chown=galaxy:galaxy https://github.com/tesseract-ocr/tessdata_best.git /galaxy/server/database/tool-data/tesseract/tessdata_best
ADD --chown=galaxy:galaxy https://github.com/tesseract-ocr/tessdata_fast.git /galaxy/server/database/tool-data/tesseract/tessdata_fast