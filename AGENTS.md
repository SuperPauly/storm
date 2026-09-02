# Repository Guide

## Scope and Priorities

- This file applies to the entire repository.
- Preserve the public `knowledge_storm` API, serialized output formats, citation behavior, and the ability to resume STORM stages from prior artifacts.
- Keep changes focused. `CONTRIBUTING.md` currently welcomes new language-model integrations, retrieval/search integrations, and Demo Light enhancements, and explicitly asks contributors not to submit broad refactors.
- Never commit credentials, local vector stores, generated articles, model caches, or run logs.

## Project Map

- `knowledge_storm/interface.py`: shared contracts for information, articles, retrievers, pipeline modules, LM configuration, engines, and Co-STORM agents.
- `knowledge_storm/storm_wiki/`: the four-stage STORM pipeline. `engine.py` orchestrates research, outline generation, article generation, and polishing; `modules/` contains the DSPy implementations and callbacks.
- `knowledge_storm/collaborative_storm/`: Co-STORM orchestration. `engine.py` owns warm start, turn policy, stepping, serialization, and report generation; `modules/` owns experts, moderator behavior, grounded QA, mind-map insertion, and report writing.
- `knowledge_storm/dataclass.py`: Co-STORM conversation, knowledge-node, and knowledge-base state. Tree structure, citation UUIDs, and `to_dict`/`from_dict` compatibility are persistent contracts.
- `knowledge_storm/storm_wiki/modules/storm_dataclass.py`: STORM conversation tables, article trees, citation reindexing, and artifact serialization.
- `knowledge_storm/lm.py`, `rm.py`, and `encoder.py`: provider integrations for generation, search/retrieval, and embeddings.
- `knowledge_storm/utils.py`: API-key loading, vector-store setup, text/citation cleanup, file I/O, and web-page extraction.
- `examples/`: executable provider and retriever examples; run these from the repository root because they load `secrets.toml` by relative path.
- `frontend/demo_light/`: the Streamlit UI and its additional dependencies. It consumes the same per-topic STORM artifacts as the CLI pipeline.
- `.github/workflows/`: Black formatting checks and the manually triggered package build/publish workflow.

## Environment and Setup

- Supported Python is 3.10 or newer; project docs and CI use Python 3.11. Some examples use structural pattern matching, so do not restore Python 3.9 compatibility accidentally.
- Standard source setup:
  ```bash
  conda create -n storm python=3.11
  conda activate storm
  pip install -r requirements.txt
  ```
- Demo Light needs a second dependency set:
  ```bash
  pip install -e .
  pip install -r frontend/demo_light/requirements.txt
  ```
- The editable install makes the local `knowledge_storm` package importable when Streamlit is launched from `frontend/demo_light`; installing the published package is an alternative when local package edits are not needed.
- Install the repository's formatter hook with `pip install pre-commit && pre-commit install` when preparing commits.
- Root examples read provider settings from ignored `secrets.toml` through `knowledge_storm.utils.load_api_key`. Demo Light reads `frontend/demo_light/.streamlit/secrets.toml` through `st.secrets`.
- Use only the credentials required by the selected LM, embedding provider, and retriever. Common settings include `OPENAI_API_KEY`, `OPENAI_API_TYPE`, Azure endpoint/version/key values, `ENCODER_API_TYPE`, and provider-specific search keys.
- Do not print, log, hard-code, or add real keys to fixtures. Keep example values obvious placeholders.

## Core Contracts

### STORM

- `STORMWikiRunner.run()` supports independent stage flags. A disabled stage means the runner loads the corresponding artifact from `<output_dir>/<sanitized_topic>/`; preserve this resume behavior when changing filenames or stage boundaries.
- Research writes `conversation_log.json` and `raw_search_results.json`.
- Outline generation writes `direct_gen_outline.txt` and `storm_gen_outline.txt`.
- Article generation writes `storm_gen_article.txt` and `url_to_info.json`; polishing writes `storm_gen_article_polished.txt`.
- `post_run()` writes `run_config.json` and `llm_call_history.jsonl`. Treat all run artifacts as generated data, not repository source.
- Topic directories replace spaces and `/` with `_` and pass through `truncate_filename`; keep CLI and UI discovery aligned with this convention.
- Preserve callback events when altering stage flow so Streamlit progress reporting and external handlers continue to work.

### Co-STORM

- The normal lifecycle is `warm_start()`, repeated `step(...)` calls, optional `knowledge_base.reorganize()`, then `generate_report()`.
- `CoStormRunner.to_dict()`/`from_dict()`, `RunnerArgument`, `ConversationTurn`, `KnowledgeNode`, and `KnowledgeBase` form a serialized-state boundary. Additive changes should remain readable from older dumps when practical.
- The knowledge base is a mutable tree shared by concurrent insertion paths. Preserve its lock-protected information insertion, parent/child links, citation UUID mappings, placement metadata, and cleanup/reorganization order.
- The example writes `report.md`, `instance_dump.json`, and `log.json` directly under its output directory.

### Provider Integrations

- Retriever implementations in `knowledge_storm/rm.py` are DSPy retrievers. Their callable path must accept one query or a list, honor `exclude_urls`, and return dictionaries containing `url`, `title`, `description`, and `snippets` (a list of strings).
- Keep retriever usage accounting compatible with `get_usage_and_reset()`. `interface.Retriever` calls providers concurrently, strips source citations from snippets, converts results through `Information.from_dict`, and records the originating query in `meta`.
- LM configuration attributes that participate in automatic validation/accounting use the `_lm` suffix. Compatible LM wrappers expose history/configuration data and, where supported, `get_usage_and_reset()`.
- Follow the interface's `_rm` naming convention for retrieval-model attributes, and do not bypass the existing LM/RM usage-reset paths when adding providers.
- Preserve input order when adding concurrent retrieval or embedding work, bound workers by the relevant runner argument, and avoid shared mutable provider state without synchronization.
- External providers, web scraping, Qdrant, and embeddings are network-, credential-, and sometimes cost-dependent. Do not use live runs as routine verification unless the task explicitly authorizes them.

## Coding Guidance

- Follow the existing Python style and format Python with Black. The enforced CI scope is `knowledge_storm/`.
- `knowledge_storm/__init__.py` re-exports the package surface with wildcard imports; treat changes to exported names and import-time dependencies as public compatibility changes.
- Prefer the public interfaces and module boundaries in `knowledge_storm/interface.py` over coupling engines to a specific provider.
- Keep DSPy signatures declarative and put orchestration/state changes in their surrounding module classes.
- Maintain citation syntax (`[n]`), URL identity, article heading structure, and `Information.to_dict()`/`from_dict()` field names; downstream rendering and resume logic parse these formats directly.
- Preserve output ordering where results are assembled from `ThreadPoolExecutor`; nondeterministic ordering can change citations, sections, and serialized state.
- When adding an LM, follow neighboring wrappers in `knowledge_storm/lm.py` and add an example under `examples/` that documents required keys and observable output.
- When adding a retriever, follow neighboring classes in `knowledge_storm/rm.py`, validate its required configuration early, support source filtering, account for query usage, and include a focused input/output example.
- For Demo Light changes, keep Streamlit session-state keys and the `DEMO_WORKING_DIR` artifact layout compatible with `demo_util.py`, `CreateNewArticle.py`, and `MyArticles.py`.
- Avoid drive-by reformatting or dependency changes. If a dependency is needed by the importable package, update root `requirements.txt`; UI-only dependencies belong in `frontend/demo_light/requirements.txt`.

## Verification

- There is currently no committed automated test suite or pytest configuration. Do not claim `pytest` coverage that does not exist; add focused tests when introducing logic that can be exercised without paid external services.
- Run the checks appropriate to the changed area from the repository root:
  ```bash
  black --check knowledge_storm
  python -m compileall -q knowledge_storm examples frontend/demo_light
  ```
- For formatting fixes, use `black knowledge_storm`. Format example or frontend files you changed as well, but avoid unrelated churn.
- For provider changes, use mocked or recorded responses to verify single-query, multi-query, exclusion, malformed/empty response, and usage-reset behavior before any authorized live smoke test.
- For STORM orchestration changes, verify both a full stage path and resume paths that load existing artifacts. Do not overwrite valuable user output; use a temporary output directory.
- For Co-STORM state changes, round-trip `to_dict()` through JSON and `from_dict()`, then verify conversation history, experts, knowledge-tree structure, citation mappings, and report generation inputs.
- For Demo Light changes, start from `frontend/demo_light` with `streamlit run storm.py` only when the required local secrets are available, and manually check article creation, progress callbacks, article listing, citations, and prior-artifact loading.
- For release work, keep the version in `setup.py` synchronized with `knowledge_storm/__init__.py`; the package workflow checks equality before `python setup.py sdist bdist_wheel` and publication.

## Repository Hygiene

- Inspect `git status` before and after work and preserve unrelated edits.
- `secrets.toml`, `.env` files, `*results/`, logs, virtual environments, build output, and egg metadata are ignored for a reason. Do not force-add them.
- `DEMO_WORKING_DIR`, vector stores, and custom output directories may not all be covered by ignore rules; check staged files explicitly.
- Update README/example documentation when changing public setup, required keys, CLI flags, provider support, artifact names, or user-visible workflows.
