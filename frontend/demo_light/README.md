# STORM Minimal User Interface

This minimal Streamlit interface can create articles, show STORM's intermediate
research steps, display citations beside an article, and reopen saved articles.

## Setup
From the repository root, confirm that the external Docker network `pangolin`
exists and that `STORM_PANGOLIN_IP` in `.env` is available. Then start the
Dockerized UI:

```bash
docker compose up --build -d
```

Open `http://127.0.0.1:8501`. Articles and a local Qdrant store use named
volumes, so `docker compose down` does not remove them.

For a non-Docker development setup:

1. Install this repository with `pip install -e .`.
2. Install the UI dependencies with `pip install -r requirements.txt` from this
   directory.
3. Export the variables documented in the repository's `.env.example` or keep
   using a local `.streamlit/secrets.toml` file.
4. Run `streamlit run storm.py`.

The UI creates `DEMO_WORKING_DIR` beside `storm.py` to store its outputs.

## Customization

You can customize the `STORMWikiRunner` powering the user interface according to [the guidelines](https://github.com/stanford-oval/storm?tab=readme-ov-file#customize-storm) in the main README file.

The `STORMWikiRunner` is initialized in `set_storm_runner()` in
[demo_util.py](demo_util.py). Environment parsing, compatible API integration,
and retriever construction live in [runtime_config.py](runtime_config.py).
