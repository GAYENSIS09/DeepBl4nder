"""Registre des fournisseurs LLM : modèles, URLs, clés et sélection par .env.

Couvre aussi le ``LLMRouter`` (pool multi-fournisseurs, rotation random/adaptive,
failover et cooldown) introduit pour être robuste au rate limiting.
"""

from __future__ import annotations

import asyncio

import httpx
import litellm
import pytest

import deepblender.llm as llm

_LLM_ENV_VARS = [
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "NVIDIA_API_KEY",
    "OPENROUTER_API_KEY",
    "CLOUDFLARE_API_KEY",
    "LLM_API_KEY",
    "LLM_PROVIDER",
    "LLM_PROVIDERS",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "LLM_ROTATION",
    "LLM_COOLDOWN_SECONDS",
    "DEEPBLENDER_LLM_BASE_URL",
    "GEMINI_LLM_MODEL",
    "GROQ_MODEL",
    "NVIDIA_MODEL",
    "OPENROUTER_MODEL",
    "CLOUDFLARE_MODEL",
]


@pytest.fixture(autouse=True)
def _reset_router() -> None:
    """Le singleton routeur est recréé avant/après chaque test (.env isolé)."""
    llm.reset_router()
    yield
    llm.reset_router()


def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralise toutes les variables LLM (le .env de dev les définit toutes)."""
    for var in _LLM_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


class _StubClient:
    """Faux client LLM (call/acall) avec échecs injectables, séquencés."""

    def __init__(self, model: str, failures: list[Exception] | None = None) -> None:
        self.model = model
        self._failures = list(failures or [])
        self.calls = 0

    def _invoke(self) -> dict[str, str]:
        self.calls += 1
        if self._failures:
            raise self._failures.pop(0)
        return {"model": self.model, "ok": "true"}

    def call(self, messages: list[dict], tools=None, output_model=None, **kwargs: object) -> dict[str, str]:
        return self._invoke()

    async def acall(self, messages: list[dict], tools=None, output_model=None, **kwargs: object) -> dict[str, str]:
        return self._invoke()



def test_providers_registry_has_expected_providers() -> None:
    assert set(llm.PROVIDERS) == {"gemini", "groq", "nvidia", "openrouter", "cloudflare", "local"}


def test_each_provider_has_key_env_and_models() -> None:
    for pid, provider in llm.PROVIDERS.items():
        assert provider.id == pid
        assert provider.api_key_env
        assert provider.base_url.startswith("http")
        assert provider.models
        assert provider.default_model() == provider.models[0]


def test_cloudflare_base_url_resolves_account_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct-123")
    assert llm.resolved_base_url(llm.PROVIDERS["cloudflare"]) == (
        "https://api.cloudflare.com/client/v4/accounts/acct-123/ai/v1"
    )
    cfg = llm.provider_config(llm.PROVIDERS["cloudflare"])
    assert cfg["base_url"] == "https://api.cloudflare.com/client/v4/accounts/acct-123/ai/v1"


def test_gemini_provider_details() -> None:
    gemini = llm.PROVIDERS["gemini"]
    assert gemini.api_key_env == "GEMINI_API_KEY"
    assert gemini.default_model() == "gemini/gemini-3.6-flash"


def test_provider_from_env_defaults_to_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert llm.provider_from_env() == "gemini"


def test_provider_from_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert llm.provider_from_env() == "groq"


def test_get_provider_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Fournisseur LLM inconnu"):
        llm.get_provider("introuvable")


def test_model_from_env_default_and_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_LLM_MODEL", raising=False)
    assert llm.model_from_env() == "gemini/gemini-3.6-flash"

    monkeypatch.setenv("LLM_MODEL", "gemini/gemini-2.5-pro")
    assert llm.model_from_env() == "gemini/gemini-2.5-pro"

    monkeypatch.delenv("LLM_MODEL")
    monkeypatch.setenv("GROQ_MODEL", "groq/llama-3.1-8b-instant")
    assert llm.model_from_env(llm.PROVIDERS["groq"]) == "groq/llama-3.1-8b-instant"


def test_api_key_from_env_uses_provider_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "cle-groq")
    assert llm.api_key_from_env(llm.PROVIDERS["groq"]) == "cle-groq"


def test_api_key_override_global(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "cle-globale")
    monkeypatch.setenv("GEMINI_API_KEY", "cle-gemini")
    assert llm.api_key_from_env() == "cle-globale"


def test_api_base_from_env_custom(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:1234/v1")
    assert llm.api_base_from_env() == "http://localhost:1234/v1"


def test_api_base_from_env_local_default() -> None:
    assert llm.api_base_from_env(llm.PROVIDERS["local"]) == "http://localhost:11434/v1"


def test_fallback_models_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Les modèles de secours (env ou module) n'existent plus : c'est du bruit."""
    monkeypatch.setenv("LLM_FALLBACK_MODELS", "gemini/gemini-2.0-flash, groq/llama-3.3-70b-versatile")
    assert not hasattr(llm, "fallback_models_from_env")
    assert not hasattr(llm, "FALLBACK_MODELS")


def test_use_fake_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPBLENDER_FAKE_LLM", "1")
    assert llm.use_fake_llm() is True
    monkeypatch.setenv("DEEPBLENDER_FAKE_LLM", "off")
    assert llm.use_fake_llm() is False


def test_build_llm_fake_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPBLENDER_FAKE_LLM", "1")
    client = llm.build_llm()
    assert client is not None


def test_build_llm_missing_key_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm.build_llm()


def test_provider_config_hides_key_value() -> None:
    cfg = llm.provider_config(llm.PROVIDERS["gemini"])
    assert cfg["id"] == "gemini"
    assert "api_key" not in cfg
    assert isinstance(cfg["api_key_configured"], bool)
    assert cfg["model"]
    assert cfg["base_url"]


def test_models_dict_backward_compatible() -> None:
    assert llm.MODELS_DICT["gemini"] == list(llm.PROVIDERS["gemini"].models)


# ------------------------------------------------------------- LLMRouter


def test_router_pool_from_env_uses_configured_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter()
    assert [p.id for p in router.providers()] == ["gemini", "groq"]


def test_router_llm_providers_env_explicit_order(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDERS", "groq, nvidia")
    monkeypatch.setenv("GROQ_API_KEY", "k1")
    monkeypatch.setenv("NVIDIA_API_KEY", "k2")
    monkeypatch.setenv("GEMINI_API_KEY", "k3")
    router = llm.LLMRouter()
    assert [p.id for p in router.providers()] == ["groq", "nvidia"]


def test_router_primary_first_then_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k1")
    monkeypatch.setenv("GEMINI_API_KEY", "k2")
    router = llm.LLMRouter()
    assert [p.id for p in router.providers()] == ["openrouter", "gemini"]


def test_router_no_keys_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm.LLMRouter()


def test_router_default_rotation_is_adaptive(monkeypatch: pytest.MonkeyPatch) -> None:
    """Seuls ``random`` et ``adaptive`` existent ; toute autre valeur retombe sur adaptive."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    assert llm.LLMRouter().rotation == "adaptive"
    assert llm.LLMRouter(rotation="random").rotation == "random"
    assert llm.LLMRouter(rotation="round_robin").rotation == "adaptive"
    assert llm.LLMRouter(rotation="failover").rotation == "adaptive"
    assert llm.LLMRouter(rotation="least_used").rotation == "adaptive"


def test_router_failover_on_first_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    monkeypatch.setenv("GEMINI_MODEL", "gemini/gemini-3.6-flash")
    registry = {"gemini/gemini-3.6-flash": [RuntimeError("429 rate limit")]}
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model))
    )
    # Ordre forcé (gemini puis groq) : isole le failover, peu importe la rotation.
    router._ordered_candidates = lambda now: router.providers()
    result = router.call([{"role": "user", "content": "a"}])
    assert result["model"] == "groq/llama-3.3-70b-versatile"
    stats = {p["id"]: p for p in router.routing_stats()["providers"]}
    assert stats["gemini"]["failures"] == 1
    assert stats["gemini"]["last_error"] == "429 rate limit"
    assert stats["groq"]["successes"] == 1


def test_classify_context_overflow() -> None:
    assert llm._classify_error(
        RuntimeError("400 maximum context length is 128000 tokens")
    ) == "context"
    assert llm._classify_error(RuntimeError("429 rate limit")) == "rate_limit"
    assert llm._classify_error(RuntimeError("boom")) == "transient"


def test_classify_openrouter_credit_error_is_quota_not_context() -> None:
    """Un manque de crédits OpenRouter (402) est un problème de quota,
    PAS une fenêtre de contexte : le failover doit continuer."""
    err = RuntimeError(
        'litellm.APIError: OpenrouterException - {"error":{"message":"Prompt '
        'tokens limit exceeded: 10335 > 6390. To increase, visit '
        'https://openrouter.ai/settings/credits and upgrade to a paid '
        'account","code":402,"metadata":{"limit_source":"openrouter_credits"}}}'
    )
    assert llm._classify_error(err) == "rate_limit"


def test_classify_litellm_exception_types() -> None:
    """Le type d'exception litellm prime sur le contenu du message."""
    assert llm._classify_error(
        litellm.RateLimitError("429 rate limit", "gemini", "gemini/gemini-3.6-flash")
    ) == "rate_limit"
    assert llm._classify_error(
        litellm.AuthenticationError("invalid api key", "gemini", "gemini/gemini-3.6-flash")
    ) == "auth"
    assert llm._classify_error(
        litellm.PermissionDeniedError(
            "quota exceeded",
            "gemini",
            "gemini/gemini-3.6-flash",
            response=httpx.Response(403, request=httpx.Request("POST", "https://x/v1")),
        )
    ) == "auth"
    assert llm._classify_error(
        litellm.NotFoundError("model not found", "gemini", "gemini/bogus")
    ) == "model"
    assert llm._classify_error(
        litellm.ContextWindowExceededError(
            "ctx len exceeded", "gemini/gemini-3.6-flash", "gemini"
        )
    ) == "context"
    assert llm._classify_error(
        litellm.APIConnectionError("connection reset", "gemini", "gemini/gemini-3.6-flash")
    ) == "transient"


def test_classify_litellm_status_code_fallback() -> None:
    """Sans type explicite, le code HTTP porté par l'exception décide."""
    assert llm._classify_error(
        litellm.APIError(402, "Prompt tokens limit exceeded: 10335 > 6390 "
                              "(openrouter_credits)", "openrouter", "openrouter/x")
    ) == "rate_limit"
    assert llm._classify_error(
        litellm.APIError(503, "upstream overloaded", "gemini", "gemini/x")
    ) == "transient"
    # 400 est ambigu : le message tranche.
    assert llm._classify_error(
        litellm.BadRequestError(
            "This model's maximum context length is 128000 tokens",
            "gemini/gemini-3.6-flash",
            "gemini",
        )
    ) == "context"


def test_classify_deprecated_model_wrapped_as_connection_error() -> None:
    """Cloudflare remonte un modèle déprécié sous forme d'APIConnectionError :
    ce n'est pas une panne réseau mais un problème de modèle déterministe."""
    err = litellm.APIConnectionError(
        'CloudflareException - {"errors":[{"message":"AiError: Model has been '
        'deprecated: @cf/meta/infire-llama-3.1-8b-instruct was deprecated on '
        '2026-05-30. See the model catalog for alternatives", "code":5028}],'
        '"success":false}',
        "cloudflare",
        "cloudflare/@cf/meta/llama-3.1-8b-instruct",
    )
    assert llm._classify_error(err) == "model"


def test_router_credit_error_fails_over(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un échec OpenRouter 402 (crédits) ne doit PAS avorter le failover."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    registry = {
        "gemini/gemini-3.6-flash": [
            RuntimeError('OpenrouterException - {"code":402,"message":"Prompt '
                         'tokens limit exceeded: 10335 > 6390 (openrouter_credits)"}')
        ]
    }
    router = llm.LLMRouter(
        cooldown=10,
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model)),
    )
    router._ordered_candidates = lambda now: router.providers()
    result = router.call([{"role": "user", "content": "a"}])
    assert result["model"] == "groq/llama-3.3-70b-versatile"
    gemini_stats = router.provider_stats(router.providers()[0])
    assert gemini_stats["failures"] == 1
    assert gemini_stats["cooldown_remaining_s"] == pytest.approx(50.0)


def test_router_context_overflow_aborts_without_burning_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un prompt trop long est déterministe : on arrête, pas de failover inutile."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    registry = {
        "gemini/gemini-3.6-flash": [
            RuntimeError("maximum context length is 128000 tokens")
        ]
    }
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model))
    )
    router._ordered_candidates = lambda now: router.providers()
    with pytest.raises(RuntimeError, match="trop long"):
        router.call([{"role": "user", "content": "a"}])
    # groq (qui aurait réussi) n'a jamais été essayé : aucun client créé.
    assert ("groq", "groq/llama-3.3-70b-versatile") not in router._clients


def test_router_all_fail_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model, [RuntimeError("boom")])
    )
    with pytest.raises(RuntimeError, match="boom"):
        router.call([{"role": "user", "content": "a"}])


def test_router_failover_survives_cp1252_console(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le print de bascule (glyphe ⚠) ne doit jamais casser le failover.

    Régression : sur console Windows cp1252, `print("⚠ ...")` levait
    UnicodeEncodeError à l'intérieur du handler d'échec et le run mourrait
    avant de basculer sur le fournisseur suivant.
    """
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")

    class _StrictCp1252:
        encoding = "cp1252"

        def write(self, text: str) -> int:
            text.encode("cp1252")
            return len(text)

        def flush(self) -> None:
            return None

    monkeypatch.setattr("sys.stdout", _StrictCp1252())

    registry = {"gemini/gemini-3.6-flash": [RuntimeError("429 rate limit")]}
    monkeypatch.setenv("GEMINI_MODEL", "gemini/gemini-3.6-flash")
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model))
    )
    router._ordered_candidates = lambda now: router.providers()
    result = router.call([{"role": "user", "content": "a"}])
    assert result["model"] == "groq/llama-3.3-70b-versatile"


def test_router_cooldown_skips_provider_then_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    registry = {"gemini/gemini-3.6-flash": [RuntimeError("429 rate limit")]}
    clock = [1000.0]
    monkeypatch.setenv("GEMINI_MODEL", "gemini/gemini-3.6-flash")
    router = llm.LLMRouter(
        cooldown=10,
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model)),
        clock=lambda: clock[0],
    )
    # Ordre forcé pour un premier appel déterministe : gemini échoue (rate
    # limit) -> cooldown 10*5=50 s, jusqu'à t=1050.
    real_candidates = router._ordered_candidates
    router._ordered_candidates = lambda now: router.providers()
    router.call([{"role": "user", "content": "a"}])
    gemini_stats = router.provider_stats(router.providers()[0])
    assert gemini_stats["cooldown_remaining_s"] == pytest.approx(50.0)
    # Appel 2 : gemini en cooldown -> skip réel (ordinal), on bascule sur groq
    router._ordered_candidates = real_candidates
    result = router.call([{"role": "user", "content": "b"}])
    assert result["model"] == "groq/llama-3.3-70b-versatile"
    # Appel 3 : cooldown expiré -> gemini est réintégré
    clock[0] = 2000.0
    router._ordered_candidates = lambda now: router.providers()
    result = router.call([{"role": "user", "content": "c"}])
    assert result["model"] == "gemini/gemini-3.6-flash"


def test_router_auth_error_gets_longer_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    registry = {"gemini/gemini-3.6-flash": [RuntimeError("401 invalid api key")]}
    clock = [1000.0]
    router = llm.LLMRouter(
        cooldown=10,
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model)),
        clock=lambda: clock[0],
    )
    router._ordered_candidates = lambda now: router.providers()
    router.call([{"role": "user", "content": "a"}])
    gemini_stats = router.provider_stats(router.providers()[0])
    assert gemini_stats["cooldown_remaining_s"] == pytest.approx(100.0)


def test_router_acall_failover_async(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    registry = {"gemini/gemini-3.6-flash": [RuntimeError("429 rate limit")]}
    monkeypatch.setenv("GEMINI_MODEL", "gemini/gemini-3.6-flash")
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model))
    )
    router._ordered_candidates = lambda now: router.providers()
    result = asyncio.run(router.acall([{"role": "user", "content": "a"}]))
    assert result["model"] == "groq/llama-3.3-70b-versatile"


def test_router_stats_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter(rotation="adaptive")
    stats = router.routing_stats()
    assert stats["rotation"] == "adaptive"
    assert stats["pool"] == ["gemini", "groq"]
    assert [p["id"] for p in stats["providers"]] == ["gemini", "groq"]
    provider = stats["providers"][0]
    assert provider["model"]
    assert provider["base_url"].startswith("http")
    assert provider["successes"] == 0
    assert provider["failures"] == 0
    assert provider["last_error"] is None
    assert "api_key" not in provider


def test_get_router_returns_shared_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    first = llm.get_router()
    second = llm.get_router()
    assert first is second
    llm.reset_router()
    third = llm.get_router()
    assert third is not first


def test_router_models_for_single_active_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un fournisseur n'a qu'un seul modèle actif ; les fallbacks sont ignorés."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("LLM_MODEL", "gemini/gemini-2.5-pro")
    monkeypatch.setenv(
        "LLM_FALLBACK_MODELS", "gemini/gemini-3.5-flash, groq/llama-3.3-70b-versatile"
    )
    router = llm.LLMRouter()
    assert router.models_for(llm.PROVIDERS["gemini"]) == ["gemini/gemini-2.5-pro"]


# -------------------------------------------------- rotations random/adaptive


def test_router_random_accepts_and_uses_all_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter(
        rotation="random", client_factory=lambda model, **kw: _StubClient(model)
    )
    assert router.rotation == "random"
    seen = {router.call([{"role": "user", "content": "a"}])["model"] for _ in range(20)}
    assert seen == {"gemini/gemini-3.6-flash", "groq/llama-3.3-70b-versatile"}


def test_router_adaptive_prefers_healthy_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """La pondération adaptative favorise le fournisseur sain sans exclure l'autre."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter(
        rotation="adaptive",
        cooldown=0.0,  # seule la pondération compte ici, pas le cooldown
        client_factory=lambda model, **kw: _StubClient(model),
    )
    gemini, groq = router.providers()
    # Santé amorcée de façon déterministe : gemini en échec, groq sain.
    router._record_failure(gemini, "gemini/gemini-3.6-flash", RuntimeError("500 transient"))
    router._record_success(groq, "groq/llama-3.3-70b-versatile")
    assert router._provider_weight(gemini) == pytest.approx(0.05)
    assert router._provider_weight(groq) == pytest.approx(1.05)
    # L'ordre de candidats est biaisé vers groq (tirage pondéré, sans mutation).
    import time as _time
    heads = {"gemini": 0, "groq": 0}
    for _ in range(100):
        first = router._ordered_candidates(_time.time())[0].id
        heads[first] += 1
    assert heads["groq"] > heads["gemini"] * 5
    assert heads["gemini"] > 0  # le sondage continue, gemini n'est jamais exclu


def test_router_adaptive_restores_trust_after_successes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le ratio succès/échec re-converge quand le fournisseur dégradé réussit.

    Comportement documenté : ``0.05 + succès/total``. Un fournisseur en échec
    est dépriorisé, mais chaque succès ultérieur restaure progressivement sa
    confiance (pas d'exclusion définitive).
    """
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter(
        rotation="adaptive",
        cooldown=0.0,
        client_factory=lambda model, **kw: _StubClient(model),
    )
    gemini, groq = router.providers()
    router._record_failure(gemini, "gemini/gemini-3.6-flash", RuntimeError("500 transient"))
    router._record_success(groq, "groq/llama-3.3-70b-versatile")
    assert router._provider_weight(gemini) == pytest.approx(0.05)
    for _ in range(40):
        router.call([{"role": "user", "content": "b"}])
    assert router._provider_weight(gemini) > 0.5


def test_router_health_tracked_per_model_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """La santé est keyée par (fournisseur, modèle), pas seulement fournisseur."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model)
    )
    gemini = router.providers()[0]
    router._record_failure(gemini, "gemini/gemini-2.5-pro", RuntimeError("404 model not found"))
    router._record_success(gemini, "gemini/gemini-3.6-flash")
    assert router._health_for("gemini", "gemini/gemini-2.5-pro").failures == 1
    assert router._health_for("gemini", "gemini/gemini-2.5-pro").successes == 0
    assert router._health_for("gemini", "gemini/gemini-3.6-flash").failures == 0
    assert router._health_for("gemini", "gemini/gemini-3.6-flash").successes == 1


def test_router_stats_shape_includes_model_breakdown(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter(rotation="adaptive")
    provider = router.routing_stats()["providers"][0]
    assert provider["successes"] == 0
    assert provider["failures"] == 0
    assert provider["last_error"] is None
    assert "models" in provider
    assert provider["models"][0]["model"] == "gemini/gemini-3.6-flash"
    assert "api_key" not in provider
