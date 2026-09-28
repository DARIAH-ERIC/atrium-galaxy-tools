FROM quay.io/galaxyproject/galaxy-min:26.1.1

USER root
RUN /galaxy/server/.venv/bin/python -m pip install --no-cache-dir iiif-fsspec==0.1.1 \
    && /galaxy/server/.venv/bin/python -c "import iiif_fsspec"

USER galaxy
