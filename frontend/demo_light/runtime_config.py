"""Environment-backed runtime configuration for the Demo Light web UI."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LM_PROVIDERS = ("openai_compatible", "anthropic_compatible")
RETRIEVERS = (
    "duckduckgo",
    "you",
    "bing",
    "brave",
    "serper",
    "tavily",
    "searxng",
    "azure_ai_search",
    "vector",
)


class ConfigurationError(ValueError):
    """Raised when the selected runtime configuration cannot be used."""


def _integer(
    env: Mapping[str, str], name: str, default: int, minimum: int, maximum: int
) -> int:
    raw = env.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer.") from error
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}.")
    return value


def _boolean(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name, str(default)).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false.")


@dataclass(frozen=True)
class LMSelection:
    provider: str
    model: str
    api_base: str
    api_key: str
    models_url: str = ""
    http_referer: str = ""
    app_title: str = "STORM Demo Light"
    anthropic_version: str = "2023-06-01"


@dataclass(frozen=True)
class RetrieverSelection:
    provider: str


@dataclass(frozen=True)
class AppSettings:
    default_lm_provider: str
    default_retriever: str
    model_cache_ttl_seconds: int
    http_timeout_seconds: int
    openai_api_base: str
    openai_api_key: str
    openai_models_url: str
    openai_default_model: str
    openrouter_http_referer: str
    openrouter_app_title: str
    anthropic_api_base: str
    anthropic_api_key: str
    anthropic_models_url: str
    anthropic_default_model: str
    anthropic_api_version: str
    ydc_api_key: str
    bing_api_key: str
    brave_api_key: str
    serper_api_key: str
    tavily_api_key: str
    searxng_api_url: str
    searxng_api_key: str
    azure_search_api_key: str
    azure_search_url: str
    azure_search_index: str
    qdrant_mode: str
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str
    qdrant_vector_store_path: str
    qdrant_embedding_model: str
    qdrant_device: str
    max_conv_turn: int
    max_perspective: int
    search_top_k: int
    retrieve_top_k: int
    max_thread_num: int
    remove_duplicate: bool

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "AppSettings":
        env = os.environ if env is None else env
        default_lm_provider = env.get(
            "STORM_DEFAULT_LM_PROVIDER", "openai_compatible"
        ).strip()
        default_retriever = env.get("STORM_DEFAULT_RETRIEVER", "duckduckgo").strip()
        qdrant_mode = env.get("QDRANT_MODE", "online").strip().lower()
        if default_lm_provider not in LM_PROVIDERS:
            raise ConfigurationError(
                f"STORM_DEFAULT_LM_PROVIDER must be one of: {', '.join(LM_PROVIDERS)}."
            )
        if default_retriever not in RETRIEVERS:
            raise ConfigurationError(
                f"STORM_DEFAULT_RETRIEVER must be one of: {', '.join(RETRIEVERS)}."
            )
        if qdrant_mode not in {"online", "offline"}:
            raise ConfigurationError("QDRANT_MODE must be online or offline.")

        return cls(
            default_lm_provider=default_lm_provider,
            default_retriever=default_retriever,
            model_cache_ttl_seconds=_integer(
                env, "STORM_MODEL_CACHE_TTL_SECONDS", 300, 0, 86400
            ),
            http_timeout_seconds=_integer(
                env, "STORM_HTTP_TIMEOUT_SECONDS", 10, 1, 120
            ),
            openai_api_base=env.get(
                "OPENAI_COMPAT_API_BASE", "https://openrouter.ai/api/v1"
            )
            .strip()
            .rstrip("/"),
            openai_api_key=env.get("OPENAI_COMPAT_API_KEY", "").strip(),
            openai_models_url=env.get(
                "OPENAI_COMPAT_MODELS_URL", "https://openrouter.ai/api/v1/models"
            ).strip(),
            openai_default_model=env.get("OPENAI_COMPAT_DEFAULT_MODEL", "").strip(),
            openrouter_http_referer=env.get("OPENROUTER_HTTP_REFERER", "").strip(),
            openrouter_app_title=env.get(
                "OPENROUTER_APP_TITLE", "STORM Demo Light"
            ).strip(),
            anthropic_api_base=env.get(
                "ANTHROPIC_COMPAT_API_BASE", "https://api.anthropic.com/v1"
            )
            .strip()
            .rstrip("/"),
            anthropic_api_key=env.get("ANTHROPIC_COMPAT_API_KEY", "").strip(),
            anthropic_models_url=env.get(
                "ANTHROPIC_COMPAT_MODELS_URL", "https://api.anthropic.com/v1/models"
            ).strip(),
            anthropic_default_model=env.get(
                "ANTHROPIC_COMPAT_DEFAULT_MODEL", ""
            ).strip(),
            anthropic_api_version=env.get(
                "ANTHROPIC_API_VERSION", "2023-06-01"
            ).strip(),
            ydc_api_key=env.get("YDC_API_KEY", "").strip(),
            bing_api_key=env.get("BING_SEARCH_API_KEY", "").strip(),
            brave_api_key=env.get("BRAVE_API_KEY", "").strip(),
            serper_api_key=env.get("SERPER_API_KEY", "").strip(),
            tavily_api_key=env.get("TAVILY_API_KEY", "").strip(),
            searxng_api_url=env.get("SEARXNG_API_URL", "").strip().rstrip("/"),
            searxng_api_key=env.get("SEARXNG_API_KEY", "").strip(),
            azure_search_api_key=env.get("AZURE_AI_SEARCH_API_KEY", "").strip(),
            azure_search_url=env.get("AZURE_AI_SEARCH_URL", "").strip().rstrip("/"),
            azure_search_index=env.get("AZURE_AI_SEARCH_INDEX_NAME", "").strip(),
            qdrant_mode=qdrant_mode,
            qdrant_url=env.get("QDRANT_URL", "").strip(),
            qdrant_api_key=env.get("QDRANT_API_KEY", "").strip(),
            qdrant_collection=env.get("QDRANT_COLLECTION_NAME", "").strip(),
            qdrant_vector_store_path=env.get(
                "QDRANT_VECTOR_STORE_PATH", "/data/vector_store"
            ).strip(),
            qdrant_embedding_model=env.get(
                "QDRANT_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            ).strip(),
            qdrant_device=env.get("QDRANT_DEVICE", "cpu").strip(),
            max_conv_turn=_integer(env, "STORM_MAX_CONV_TURN", 3, 1, 20),
            max_perspective=_integer(env, "STORM_MAX_PERSPECTIVE", 3, 1, 10),
            search_top_k=_integer(env, "STORM_SEARCH_TOP_K", 3, 1, 20),
            retrieve_top_k=_integer(env, "STORM_RETRIEVE_TOP_K", 5, 1, 50),
            max_thread_num=_integer(env, "STORM_MAX_THREAD_NUM", 10, 1, 100),
            remove_duplicate=_boolean(env, "STORM_REMOVE_DUPLICATE", False),
        )

    def lm_selection(self, provider: str, model: str = "") -> LMSelection:
        if provider == "openai_compatible":
            return LMSelection(
                provider=provider,
                model=model.strip() or self.openai_default_model,
                api_base=self.openai_api_base,
                api_key=self.openai_api_key,
                models_url=self.openai_models_url,
                http_referer=self.openrouter_http_referer,
                app_title=self.openrouter_app_title,
            )
        if provider == "anthropic_compatible":
            return LMSelection(
                provider=provider,
                model=model.strip() or self.anthropic_default_model,
                api_base=self.anthropic_api_base,
                api_key=self.anthropic_api_key,
                models_url=self.anthropic_models_url,
                anthropic_version=self.anthropic_api_version,
            )
        raise ConfigurationError(f"Unknown language model provider: {provider}.")


def _catalog_ids(payload: object) -> list[str]:
    if isinstance(payload, dict):
        values = payload.get("data", payload.get("models", []))
    else:
        values = payload
    if not isinstance(values, list):
        raise ConfigurationError(
            "The model catalog response does not contain a model list."
        )
    ids = []
    for item in values:
        if isinstance(item, str):
            ids.append(item)
        elif isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.append(item["id"])
    return sorted(set(ids))


def discover_models(selection: LMSelection, timeout_seconds: int = 10) -> list[str]:
    if not selection.models_url:
        raise ConfigurationError(
            "No model catalog URL is configured; enter a model ID manually."
        )
    headers = {"Accept": "application/json"}
    if selection.provider == "openai_compatible":
        if selection.api_key:
            headers["Authorization"] = f"Bearer {selection.api_key}"
        if selection.http_referer:
            headers["HTTP-Referer"] = selection.http_referer
        if selection.app_title:
            headers["X-OpenRouter-Title"] = selection.app_title
    elif selection.provider == "anthropic_compatible":
        if selection.api_key:
            headers["x-api-key"] = selection.api_key
        headers["anthropic-version"] = selection.anthropic_version
    else:
        raise ConfigurationError(
            f"Unknown language model provider: {selection.provider}."
        )

    try:
        with urlopen(
            Request(selection.models_url, headers=headers), timeout=timeout_seconds
        ) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        detail = (
            f"HTTP {error.code}"
            if isinstance(error, HTTPError)
            else type(error).__name__
        )
        raise ConfigurationError(
            f"Could not load the model catalog ({detail}); enter a model ID manually."
        ) from error
    models = _catalog_ids(payload)
    if not models:
        raise ConfigurationError(
            "The model catalog returned no model IDs; enter one manually."
        )
    return models


def _require(value: str, variable: str) -> str:
    if not value:
        raise ConfigurationError(f"Set {variable} before using this option.")
    return value


def _litellm_model_name(selection: LMSelection) -> str:
    model = _require(selection.model, "a model ID")
    if selection.provider == "openai_compatible":
        if "openrouter.ai" in selection.api_base and not model.startswith(
            "openrouter/"
        ):
            return f"openrouter/{model}"
        return model if model.startswith("openai/") else f"openai/{model}"
    return model if model.startswith("anthropic/") else f"anthropic/{model}"


def build_lm_configs(selection: LMSelection):
    _require(selection.model, "a model ID")
    _require(selection.api_base, "the compatible API base URL")
    _require(selection.api_key, "the compatible API key")

    from knowledge_storm import STORMWikiLMConfigs
    from knowledge_storm.lm import LitellmModel

    model_name = _litellm_model_name(selection)
    common = {"api_key": selection.api_key, "api_base": selection.api_base}
    if (
        selection.provider == "openai_compatible"
        and "openrouter.ai" in selection.api_base
    ):
        headers = {}
        if selection.http_referer:
            headers["HTTP-Referer"] = selection.http_referer
        if selection.app_title:
            headers["X-OpenRouter-Title"] = selection.app_title
        if headers:
            common["extra_headers"] = headers

    configs = STORMWikiLMConfigs()
    configs.set_conv_simulator_lm(
        LitellmModel(model=model_name, max_tokens=500, **common)
    )
    configs.set_question_asker_lm(
        LitellmModel(model=model_name, max_tokens=500, **common)
    )
    configs.set_outline_gen_lm(LitellmModel(model=model_name, max_tokens=400, **common))
    configs.set_article_gen_lm(LitellmModel(model=model_name, max_tokens=700, **common))
    configs.set_article_polish_lm(
        LitellmModel(model=model_name, max_tokens=4000, **common)
    )
    return configs


def build_retriever(selection: RetrieverSelection, settings: AppSettings):
    provider = selection.provider
    required = {
        "you": ((settings.ydc_api_key, "YDC_API_KEY"),),
        "bing": ((settings.bing_api_key, "BING_SEARCH_API_KEY"),),
        "brave": ((settings.brave_api_key, "BRAVE_API_KEY"),),
        "serper": ((settings.serper_api_key, "SERPER_API_KEY"),),
        "tavily": ((settings.tavily_api_key, "TAVILY_API_KEY"),),
        "searxng": ((settings.searxng_api_url, "SEARXNG_API_URL"),),
        "azure_ai_search": (
            (settings.azure_search_api_key, "AZURE_AI_SEARCH_API_KEY"),
            (settings.azure_search_url, "AZURE_AI_SEARCH_URL"),
            (settings.azure_search_index, "AZURE_AI_SEARCH_INDEX_NAME"),
        ),
        "vector": (
            (settings.qdrant_collection, "QDRANT_COLLECTION_NAME"),
            (settings.qdrant_embedding_model, "QDRANT_EMBEDDING_MODEL"),
        ),
    }
    for value, variable in required.get(provider, ()):
        _require(value, variable)
    if provider == "vector":
        if settings.qdrant_mode == "online":
            _require(settings.qdrant_url, "QDRANT_URL")
        else:
            _require(settings.qdrant_vector_store_path, "QDRANT_VECTOR_STORE_PATH")

    from knowledge_storm.rm import (
        AzureAISearch,
        BingSearch,
        BraveRM,
        DuckDuckGoSearchRM,
        SearXNG,
        SerperRM,
        TavilySearchRM,
        VectorRM,
        YouRM,
    )

    k = settings.search_top_k
    if provider == "duckduckgo":
        return DuckDuckGoSearchRM(k=k)
    if provider == "you":
        return YouRM(ydc_api_key=_require(settings.ydc_api_key, "YDC_API_KEY"), k=k)
    if provider == "bing":
        return BingSearch(
            bing_search_api_key=_require(settings.bing_api_key, "BING_SEARCH_API_KEY"),
            k=k,
        )
    if provider == "brave":
        return BraveRM(
            brave_search_api_key=_require(settings.brave_api_key, "BRAVE_API_KEY"), k=k
        )
    if provider == "serper":
        return SerperRM(
            serper_search_api_key=_require(settings.serper_api_key, "SERPER_API_KEY"),
            k=k,
        )
    if provider == "tavily":
        return TavilySearchRM(
            tavily_search_api_key=_require(settings.tavily_api_key, "TAVILY_API_KEY"),
            k=k,
        )
    if provider == "searxng":
        return SearXNG(
            searxng_api_url=_require(settings.searxng_api_url, "SEARXNG_API_URL"),
            searxng_api_key=settings.searxng_api_key or None,
            k=k,
        )
    if provider == "azure_ai_search":
        return AzureAISearch(
            azure_ai_search_api_key=_require(
                settings.azure_search_api_key, "AZURE_AI_SEARCH_API_KEY"
            ),
            azure_ai_search_url=_require(
                settings.azure_search_url, "AZURE_AI_SEARCH_URL"
            ),
            azure_ai_search_index_name=_require(
                settings.azure_search_index, "AZURE_AI_SEARCH_INDEX_NAME"
            ),
            k=k,
        )
    if provider == "vector":
        collection = _require(settings.qdrant_collection, "QDRANT_COLLECTION_NAME")
        embedding = _require(settings.qdrant_embedding_model, "QDRANT_EMBEDDING_MODEL")
        retriever = VectorRM(collection, embedding, device=settings.qdrant_device, k=k)
        if settings.qdrant_mode == "online":
            retriever.init_online_vector_db(
                _require(settings.qdrant_url, "QDRANT_URL"),
                settings.qdrant_api_key or None,
            )
        else:
            retriever.init_offline_vector_db(
                _require(settings.qdrant_vector_store_path, "QDRANT_VECTOR_STORE_PATH")
            )
        return retriever
    raise ConfigurationError(f"Unknown retriever: {provider}.")


def configuration_fingerprint(
    lm: LMSelection, retriever: RetrieverSelection, settings: AppSettings
) -> str:
    values = {
        "lm": {
            **asdict(lm),
            "api_key": hashlib.sha256(lm.api_key.encode()).hexdigest(),
        },
        "retriever": asdict(retriever),
        "runner": {
            "max_conv_turn": settings.max_conv_turn,
            "max_perspective": settings.max_perspective,
            "search_top_k": settings.search_top_k,
            "retrieve_top_k": settings.retrieve_top_k,
            "max_thread_num": settings.max_thread_num,
        },
        "retriever_credentials": hashlib.sha256(
            "|".join(
                (
                    settings.ydc_api_key,
                    settings.bing_api_key,
                    settings.brave_api_key,
                    settings.serper_api_key,
                    settings.tavily_api_key,
                    settings.searxng_api_key,
                    settings.azure_search_api_key,
                    settings.qdrant_api_key,
                )
            ).encode()
        ).hexdigest(),
        "qdrant": {
            "mode": settings.qdrant_mode,
            "url": settings.qdrant_url,
            "collection": settings.qdrant_collection,
            "path": settings.qdrant_vector_store_path,
            "embedding": settings.qdrant_embedding_model,
            "device": settings.qdrant_device,
        },
    }
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
