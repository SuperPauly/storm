FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app
COPY . /app

RUN python -m pip install --upgrade pip \
    && python -m pip install --index-url https://download.pytorch.org/whl/cpu torch \
    && python -m pip install . \
    && python -m pip install -r frontend/demo_light/requirements.txt \
    && python -m pip uninstall --yes wheel \
    && useradd --create-home --uid 10001 storm \
    && mkdir -p /app/frontend/demo_light/DEMO_WORKING_DIR /data/vector_store \
    && chown -R storm:storm /app/frontend/demo_light/DEMO_WORKING_DIR /data /home/storm

USER storm
WORKDIR /app/frontend/demo_light
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"

CMD ["streamlit", "run", "storm.py", "--server.address=0.0.0.0", "--server.port=8501"]
