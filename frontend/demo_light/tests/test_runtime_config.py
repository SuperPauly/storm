import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

DEMO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_DIR))

from runtime_config import (  # noqa: E402
    AppSettings,
    ConfigurationError,
    LMSelection,
    RetrieverSelection,
    build_lm_configs,
    build_retriever,
    configuration_fingerprint,
    discover_models,
)


class _CatalogHandler(BaseHTTPRequestHandler):
    response_status = 200
    response_body = {"data": [{"id": "vendor/model-b"}, {"id": "vendor/model-a"}]}
    received_headers = {}

    def do_GET(self):
        type(self).received_headers = dict(self.headers.items())
        body = json.dumps(type(self).response_body).encode("utf-8")
        self.send_response(type(self).response_status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


class RuntimeConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _CatalogHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.catalog_url = f"http://127.0.0.1:{cls.server.server_port}/models"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_settings_use_safe_defaults(self):
        settings = AppSettings.from_env({})

        self.assertEqual(settings.default_lm_provider, "openai_compatible")
        self.assertEqual(settings.default_retriever, "duckduckgo")
        self.assertEqual(settings.openai_api_base, "https://openrouter.ai/api/v1")
        self.assertEqual(
            settings.openai_models_url, "https://openrouter.ai/api/v1/models"
        )
        self.assertEqual(settings.qdrant_device, "cpu")
        self.assertEqual(settings.max_conv_turn, 3)
        self.assertEqual(settings.retrieve_top_k, 5)

    def test_settings_reject_out_of_range_integer(self):
        with self.assertRaisesRegex(ConfigurationError, "STORM_MAX_CONV_TURN"):
            AppSettings.from_env({"STORM_MAX_CONV_TURN": "0"})

    def test_settings_reject_invalid_boolean(self):
        with self.assertRaisesRegex(ConfigurationError, "STORM_REMOVE_DUPLICATE"):
            AppSettings.from_env({"STORM_REMOVE_DUPLICATE": "sometimes"})

    def test_openai_model_discovery_sorts_ids_and_sends_bearer_header(self):
        _CatalogHandler.response_status = 200
        _CatalogHandler.response_body = {
            "data": [{"id": "vendor/model-b"}, {"id": "vendor/model-a"}]
        }
        selection = LMSelection(
            provider="openai_compatible",
            model="manual-model",
            api_base="https://example.invalid/v1",
            api_key="secret-openai-key",
            models_url=self.catalog_url,
        )

        models = discover_models(selection, timeout_seconds=2)

        self.assertEqual(models, ["vendor/model-a", "vendor/model-b"])
        self.assertEqual(
            _CatalogHandler.received_headers.get("Authorization"),
            "Bearer secret-openai-key",
        )

    def test_anthropic_model_discovery_accepts_string_items_and_sends_headers(self):
        _CatalogHandler.response_status = 200
        _CatalogHandler.response_body = {"models": ["claude-z", "claude-a"]}
        selection = LMSelection(
            provider="anthropic_compatible",
            model="claude-manual",
            api_base="https://example.invalid",
            api_key="secret-anthropic-key",
            models_url=self.catalog_url,
            anthropic_version="2023-06-01",
        )

        models = discover_models(selection, timeout_seconds=2)

        self.assertEqual(models, ["claude-a", "claude-z"])
        received_headers = {
            key.lower(): value
            for key, value in _CatalogHandler.received_headers.items()
        }
        self.assertEqual(received_headers.get("x-api-key"), "secret-anthropic-key")
        self.assertEqual(received_headers.get("anthropic-version"), "2023-06-01")

    def test_model_discovery_error_does_not_expose_key(self):
        _CatalogHandler.response_status = 401
        _CatalogHandler.response_body = {"error": "unauthorized"}
        selection = LMSelection(
            provider="openai_compatible",
            model="manual-model",
            api_base="https://example.invalid/v1",
            api_key="never-print-this-key",
            models_url=self.catalog_url,
        )

        with self.assertRaises(ConfigurationError) as raised:
            discover_models(selection, timeout_seconds=2)

        self.assertNotIn("never-print-this-key", str(raised.exception))

    def test_lm_config_requires_manual_model_when_discovery_is_unavailable(self):
        settings = AppSettings.from_env({})
        selection = settings.lm_selection("openai_compatible", "")

        with self.assertRaisesRegex(ConfigurationError, "model"):
            build_lm_configs(selection)

    def test_retriever_requires_provider_credentials(self):
        settings = AppSettings.from_env({})

        with self.assertRaisesRegex(ConfigurationError, "YDC_API_KEY"):
            build_retriever(RetrieverSelection("you"), settings)

    def test_vector_retriever_requires_existing_collection_configuration(self):
        settings = AppSettings.from_env({})

        with self.assertRaisesRegex(ConfigurationError, "QDRANT_COLLECTION_NAME"):
            build_retriever(RetrieverSelection("vector"), settings)

    def test_configuration_fingerprint_changes_without_containing_credentials(self):
        settings = AppSettings.from_env({"OPENAI_COMPAT_API_KEY": "top-secret"})
        lm = settings.lm_selection("openai_compatible", "vendor/model-a")
        first = configuration_fingerprint(
            lm, RetrieverSelection("duckduckgo"), settings
        )
        second = configuration_fingerprint(lm, RetrieverSelection("bing"), settings)

        self.assertNotEqual(first, second)
        self.assertNotIn("top-secret", first)


if __name__ == "__main__":
    unittest.main()
