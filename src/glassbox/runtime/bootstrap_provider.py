"""Provider and executor bootstrap helpers for runtime entrypoints."""

from collections.abc import Callable
from urllib.parse import urlparse

from glassbox.core.models import SessionRecord
from glassbox.llm.adapters import ModelProviderConfig
from glassbox.llm.adapters import PydanticAIModelAdapter
from glassbox.runtime.errors import ProviderRuntimeConfigFailure
from glassbox.runtime.errors import SessionRuntimeFailure
from glassbox.runtime.provider_config import ProviderSecretConfig
from glassbox.runtime.provider_config import RuntimeProviderConfig


def build_model_adapter(session: SessionRecord) -> PydanticAIModelAdapter:
    """Return the model adapter configured for the persisted session model."""

    provider, model_name = split_model_name(session.model_name)
    return PydanticAIModelAdapter(
        ModelProviderConfig(model_name=model_name, provider=provider)
    )


def build_model_executor_factory(
    provider_config: RuntimeProviderConfig,
    *,
    local_executor_builder: Callable[[SessionRecord], object],
    openai_executor_builder: Callable[..., object],
    anthropic_executor_builder: Callable[..., object],
) -> Callable[[SessionRecord], object]:
    """Return the executor factory for persisted session model selections."""

    def build_model_executor(session: SessionRecord) -> object:
        provider, model_name = split_model_name(session.model_name)
        if provider is None:
            return local_executor_builder(session)
        if provider == "openai":
            return build_provider_executor(
                session,
                provider_name="OpenAI",
                model_name=model_name,
                provider_secret_config=provider_config.openai,
                executor_builder=openai_executor_builder,
                local_executor_builder=local_executor_builder,
            )
        if provider == "anthropic":
            return build_provider_executor(
                session,
                provider_name="Anthropic",
                model_name=model_name,
                provider_secret_config=provider_config.anthropic,
                executor_builder=anthropic_executor_builder,
                local_executor_builder=local_executor_builder,
            )
        raise ProviderRuntimeConfigFailure(
            f"unsupported model provider configured for session: {provider}; "
            "use openai:MODEL, anthropic:MODEL, or an unprefixed local model, "
            "then rerun provider diagnostics before retrying",
            retryable=False,
        )

    return build_model_executor


def build_provider_executor(
    session: SessionRecord,
    *,
    provider_name: str,
    model_name: str,
    provider_secret_config: ProviderSecretConfig,
    executor_builder: Callable[..., object],
    local_executor_builder: Callable[[SessionRecord], object],
) -> object:
    """Return a provider-backed executor or the local fallback executor."""

    if not provider_secret_config.is_configured:
        return local_executor_builder(session)

    if provider_secret_config.api_key is None:
        raise ProviderRuntimeConfigFailure(
            f"missing {provider_name} API key for configured provider runtime; "
            f"set {provider_name.upper()}_API_KEY in the process environment or .env "
            "at --cwd, or remove partial provider overrides",
            retryable=False,
        )

    if provider_secret_config.base_url is not None:
        validate_provider_base_url(
            provider_name,
            provider_secret_config.base_url,
        )

    try:
        return executor_builder(
            model_name,
            api_key=provider_secret_config.api_key,
            base_url=provider_secret_config.base_url,
        )
    except SessionRuntimeFailure:
        raise
    except Exception as exc:
        raise ProviderRuntimeConfigFailure(
            f"invalid {provider_name} provider runtime config",
            retryable=False,
        ) from exc


def validate_provider_base_url(provider_name: str, base_url: str) -> None:
    """Validate the configured provider base URL before executor construction."""

    parsed_url = urlparse(base_url)
    if parsed_url.scheme not in {"http", "https"} or parsed_url.netloc == "":
        raise ProviderRuntimeConfigFailure(
            f"invalid {provider_name} base URL runtime config; use an http(s) URL "
            f"or remove {provider_name.upper()}_BASE_URL",
            retryable=False,
        )


def split_model_name(model_name: str) -> tuple[str | None, str]:
    """Split a persisted provider-prefixed model name into provider and model."""

    provider, separator, resolved_model_name = model_name.partition(":")
    if separator == "":
        return None, model_name
    return provider, resolved_model_name
