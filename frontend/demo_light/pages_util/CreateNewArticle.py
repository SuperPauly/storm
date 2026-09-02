import os
import time

import demo_util
import streamlit as st
from demo_util import (
    DemoFileIOHelper,
    DemoTextProcessingHelper,
    DemoUIHelper,
    truncate_filename,
)
from runtime_config import (
    AppSettings,
    ConfigurationError,
    LM_PROVIDERS,
    RETRIEVERS,
    RetrieverSelection,
    discover_models,
)

PROVIDER_LABELS = {
    "openai_compatible": "OpenAI-compatible (including OpenRouter)",
    "anthropic_compatible": "Anthropic Messages-compatible",
}
RETRIEVER_LABELS = {
    "duckduckgo": "DuckDuckGo (no key required)",
    "you": "You.com",
    "bing": "Bing",
    "brave": "Brave",
    "serper": "Serper",
    "tavily": "Tavily",
    "searxng": "SearXNG",
    "azure_ai_search": "Azure AI Search",
    "vector": "Existing Qdrant collection",
}


def _discover_models_cached(selection, settings):
    cache = st.session_state.setdefault("page3_model_cache", {})
    now = time.monotonic()
    cache_key = (selection.provider, selection.models_url)
    cached = cache.get(cache_key)
    if cached and now - cached["created"] <= settings.model_cache_ttl_seconds:
        return cached["models"], cached.get("error")
    try:
        models = discover_models(selection, settings.http_timeout_seconds)
        result = {"created": now, "models": models, "error": None}
    except ConfigurationError as error:
        result = {"created": now, "models": [], "error": str(error)}
    cache[cache_key] = result
    return result["models"], result["error"]


def handle_not_started(settings):
    if st.session_state["page3_write_article_state"] == "not started":
        _, search_form_column, _ = st.columns([2, 5, 2])
        with search_form_column:
            with st.form(key="search_form"):
                provider = st.selectbox(
                    "Language model API",
                    LM_PROVIDERS,
                    index=LM_PROVIDERS.index(settings.default_lm_provider),
                    format_func=PROVIDER_LABELS.get,
                )
                base_selection = settings.lm_selection(provider)
                discovered_models, discovery_error = _discover_models_cached(
                    base_selection, settings
                )
                if discovered_models:
                    model_options = discovered_models + ["Enter a model ID manually"]
                    default_model = base_selection.model
                    model_index = (
                        model_options.index(default_model)
                        if default_model in model_options
                        else len(model_options) - 1 if default_model else 0
                    )
                    selected_model = st.selectbox(
                        "Model", model_options, index=model_index
                    )
                    manual_model = ""
                    if selected_model == "Enter a model ID manually":
                        manual_model = st.text_input(
                            "Model ID", value=base_selection.model
                        )
                    model = manual_model or (
                        ""
                        if selected_model == "Enter a model ID manually"
                        else selected_model
                    )
                else:
                    st.caption(discovery_error or "Enter a model ID manually.")
                    model = st.text_input("Model ID", value=base_selection.model)

                retriever = st.selectbox(
                    "Search provider",
                    RETRIEVERS,
                    index=RETRIEVERS.index(settings.default_retriever),
                    format_func=RETRIEVER_LABELS.get,
                )
                # Text input for the search topic
                DemoUIHelper.st_markdown_adjust_size(
                    content="Enter the topic you want to learn in depth:", font_size=18
                )
                st.session_state["page3_topic"] = st.text_input(
                    label="page3_topic", label_visibility="collapsed"
                )
                pass_appropriateness_check = True

                # Submit button for the form
                submit_button = st.form_submit_button(label="Research")
                # only start new search when button is clicked, not started, or already finished previous one
                if submit_button and st.session_state["page3_write_article_state"] in [
                    "not started",
                    "show results",
                ]:
                    if not st.session_state["page3_topic"].strip():
                        pass_appropriateness_check = False
                        st.session_state["page3_warning_message"] = (
                            "topic could not be empty"
                        )

                    st.session_state["page3_topic_name_cleaned"] = (
                        st.session_state["page3_topic"]
                        .replace(" ", "_")
                        .replace("/", "_")
                    )
                    st.session_state["page3_topic_name_truncated"] = truncate_filename(
                        st.session_state["page3_topic_name_cleaned"]
                    )
                    if not pass_appropriateness_check:
                        st.session_state["page3_write_article_state"] = "not started"
                        alert = st.warning(
                            st.session_state["page3_warning_message"], icon="⚠️"
                        )
                        time.sleep(5)
                        alert.empty()
                    else:
                        st.session_state["page3_lm_selection"] = settings.lm_selection(
                            provider, model
                        )
                        st.session_state["page3_retriever_selection"] = (
                            RetrieverSelection(retriever)
                        )
                        st.session_state["page3_write_article_state"] = "initiated"


def handle_initiated(settings):
    if st.session_state["page3_write_article_state"] == "initiated":
        current_working_dir = os.path.join(demo_util.get_demo_dir(), "DEMO_WORKING_DIR")
        if not os.path.exists(current_working_dir):
            os.makedirs(current_working_dir)

        try:
            demo_util.set_storm_runner(
                st.session_state["page3_lm_selection"],
                st.session_state["page3_retriever_selection"],
                settings,
            )
        except (ConfigurationError, ImportError, RuntimeError, ValueError) as error:
            st.session_state["page3_write_article_state"] = "not started"
            st.error(f"Configuration error: {error}")
            return
        st.session_state["page3_current_working_dir"] = current_working_dir
        st.session_state["page3_write_article_state"] = "pre_writing"


def handle_pre_writing():
    if st.session_state["page3_write_article_state"] == "pre_writing":
        status = st.status(
            "I am brain**STORM**ing now to research the topic. (This may take 2-3 minutes.)"
        )
        st_callback_handler = demo_util.StreamlitCallbackHandler(status)
        with status:
            # STORM main gen outline
            st.session_state["runner"].run(
                topic=st.session_state["page3_topic"],
                do_research=True,
                do_generate_outline=True,
                do_generate_article=False,
                do_polish_article=False,
                callback_handler=st_callback_handler,
            )
            conversation_log_path = os.path.join(
                st.session_state["page3_current_working_dir"],
                st.session_state["page3_topic_name_truncated"],
                "conversation_log.json",
            )
            demo_util._display_persona_conversations(
                DemoFileIOHelper.read_json_file(conversation_log_path)
            )
            st.session_state["page3_write_article_state"] = "final_writing"
            status.update(label="brain**STORM**ing complete!", state="complete")


def handle_final_writing():
    if st.session_state["page3_write_article_state"] == "final_writing":
        # polish final article
        with st.status(
            "Now I will connect the information I found for your reference. (This may take 4-5 minutes.)"
        ) as status:
            st.info(
                "Now I will connect the information I found for your reference. (This may take 4-5 minutes.)"
            )
            st.session_state["runner"].run(
                topic=st.session_state["page3_topic"],
                do_research=False,
                do_generate_outline=False,
                do_generate_article=True,
                do_polish_article=True,
                remove_duplicate=st.session_state["runner_settings"].remove_duplicate,
            )
            # finish the session
            st.session_state["runner"].post_run()

            # update status bar
            st.session_state["page3_write_article_state"] = "prepare_to_show_result"
            status.update(label="information snythesis complete!", state="complete")


def handle_prepare_to_show_result():
    if st.session_state["page3_write_article_state"] == "prepare_to_show_result":
        _, show_result_col, _ = st.columns([4, 3, 4])
        with show_result_col:
            if st.button("show final article"):
                st.session_state["page3_write_article_state"] = "completed"
                st.rerun()


def handle_completed():
    if st.session_state["page3_write_article_state"] == "completed":
        # display polished article
        current_working_dir_paths = DemoFileIOHelper.read_structure_to_dict(
            st.session_state["page3_current_working_dir"]
        )
        current_article_file_path_dict = current_working_dir_paths[
            st.session_state["page3_topic_name_truncated"]
        ]
        demo_util.display_article_page(
            selected_article_name=st.session_state["page3_topic_name_cleaned"],
            selected_article_file_path_dict=current_article_file_path_dict,
            show_title=True,
            show_main_article=True,
        )


def create_new_article_page():
    demo_util.clear_other_page_session_state(page_index=3)

    try:
        settings = AppSettings.from_env()
    except ConfigurationError as error:
        st.error(f"Environment configuration error: {error}")
        return

    if "page3_write_article_state" not in st.session_state:
        st.session_state["page3_write_article_state"] = "not started"

    handle_not_started(settings)

    handle_initiated(settings)

    handle_pre_writing()

    handle_final_writing()

    handle_prepare_to_show_result()

    handle_completed()
