"""Registre des fournisseurs LLM : modèles, URLs, clés et pool explicite.

Couvre aussi le ``LLMRouter`` (pool multi-fournisseurs + vote : majorité,
tie-break santé et cooldown simple).
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import litellm
import pytest

import DeepBl4nder.llm as llm

_LLM_ENV_VARS = [
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "NVIDIA_API_KEY",
    "OPENROUTER_API_KEY",
    "CLOUDFLARE_API_KEY",
]


@pytest.fixture(autouse=True)
def _reset_router(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le singleton routeur est recréé avant/après chaque test (.env isolé).

    La découverte réseau des modèles est désactivée par défaut : aucun test
    ne doit dépendre du réseau ; les tests dédiés la réactivent explicitement.
    """
    monkeypatch.setenv("DeepBl4nder_DISCOVER_MODELS", "off")
    llm.reset_router()
    yield
    llm.reset_router()


def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralise toutes les clés d'API (le .env de dev les définit toutes)."""
    for var in _LLM_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


class _StubClient:
    """Faux client LLM (call/acall) avec échecs injectables et réponse fixe."""

    def __init__(self, model: str, failures: list[Exception] | None = None, answer: str | None = None) -> None:
        self.model = model
        self._failures = list(failures or [])
        self.answer = answer
        self.calls = 0

    def _invoke(self) -> dict[str, str]:
        self.calls += 1
        if self._failures:
            raise self._failures.pop(0)
        return {"model": self.answer or self.model, "ok": "true"}

    def call(self, messages: list[dict], tools=None, output_model=None, **kwargs: object) -> dict[str, str]:
        return self._invoke()

    async def acall(self, messages: list[dict], tools=None, output_model=None, **kwargs: object) -> dict[str, str]:
        return self._invoke()


def test_providers_registry_has_expected_providers() -> None:
    assert set(llm.PROVIDERS) == {"gemini", "groq", "nvidia", "openrouter", "cloudflare"}


def test_each_provider_has_key_env_and_models() -> None:
    for pid, provider in llm.PROVIDERS.items():
        assert provider.id == pid
        assert provider.api_key_env
        assert provider.base_url.startswith("http")
        assert provider.models
        assert provider.default_model() == provider.models[0]


def test_cloudflare_base_url_resolves_account_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct-123")
    assert llm.PROVIDERS["cloudflare"].resolved_base_url() == (
        "https://api.cloudflare.com/client/v4/accounts/acct-123/ai/v1"
    )
    cfg = llm.PROVIDERS["cloudflare"].config()
    assert cfg["base_url"] == "https://api.cloudflare.com/client/v4/accounts/acct-123/ai/v1"


def test_gemini_provider_details() -> None:
    gemini = llm.PROVIDERS["gemini"]
    assert gemini.api_key_env == "GEMINI_API_KEY"
    assert gemini.default_model() == "gemini/gemini-3.6-flash"


def test_get_provider_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Fournisseur LLM inconnu"):
        llm.get_provider("introuvable")


def test_provider_model_fixed_in_registry() -> None:
    """Le modèle actif est celui du registre : plus de surcharge .env."""
    assert llm.PROVIDERS["gemini"].model() == "gemini/gemini-3.6-flash"
    assert llm.PROVIDERS["groq"].model() == "groq/openai/gpt-oss-120b"


def test_provider_api_key_uses_dedicated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "cle-groq")
    assert llm.PROVIDERS["groq"].api_key() == "cle-groq"
    assert llm.PROVIDERS["groq"].is_available() is True
    assert llm.PROVIDERS["gemini"].api_key() is None
    assert llm.PROVIDERS["gemini"].is_available() is False


def test_no_env_config_helpers_remain() -> None:
    """Plus de fonctions ni de dict liés à l'environnement : tout est dans
    ``PROVIDERS`` et la sélection est explicite (``provider_ids``)."""
    for name in (
        "provider_from_env",
        "model_from_env",
        "api_key_from_env",
        "api_base_from_env",
        "use_fake_llm",
        "provider_config",
        "MODELS_DICT",
    ):
        assert not hasattr(llm, name)


def test_build_llm_fake_mode() -> None:
    client = llm.build_llm(fake=True)
    assert client is not None


def test_build_llm_missing_key_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm.build_llm(provider_ids=["groq"])


def test_provider_config_hides_key_value() -> None:
    cfg = llm.PROVIDERS["gemini"].config()
    assert cfg["id"] == "gemini"
    assert "api_key" not in cfg
    assert isinstance(cfg["api_key_configured"], bool)
    assert cfg["model"]
    assert cfg["base_url"]


def test_provider_methods_model_key_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """La classe LLMProvider porte toute la logique (pas de fonctions module)."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "cle-gemini")
    gemini = llm.PROVIDERS["gemini"]
    groq = llm.PROVIDERS["groq"]
    assert gemini.model() == "gemini/gemini-3.6-flash"
    assert gemini.api_key() == "cle-gemini"
    assert gemini.api_key_env == "GEMINI_API_KEY"
    assert gemini.is_available() is True
    assert groq.is_available() is False
    assert gemini.api_base() is None
    assert gemini.resolved_base_url() == gemini.base_url
    assert gemini.config()["model"] == gemini.model()


# ------------------------------------------------------------ classification


def test_classify_context_overflow() -> None:
    assert llm._classify_error(
        RuntimeError("400 maximum context length is 128000 tokens")
    ) == "context"
    assert llm._classify_error(RuntimeError("429 rate limit")) == "rate_limit"
    assert llm._classify_error(RuntimeError("boom")) == "transient"


def test_classify_openrouter_credit_error_is_quota_not_context() -> None:
    """Un manque de crédits OpenRouter (402) est un problème de quota,
    PAS une fenêtre de contexte : le vote continue avec les autres."""
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


# ------------------------------------------------------------- LLMRouter


def test_router_pool_defaults_to_available_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter()
    assert [p.id for p in router.providers()] == ["gemini", "groq"]


def test_router_explicit_provider_ids_strict_order(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "k1")
    monkeypatch.setenv("NVIDIA_API_KEY", "k2")
    monkeypatch.setenv("GEMINI_API_KEY", "k3")
    router = llm.LLMRouter(provider_ids=["groq", "nvidia"])
    assert [p.id for p in router.providers()] == ["groq", "nvidia"]


def test_router_explicit_ids_require_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pool strict : un fournisseur sans clé d'API est exclu."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k1")
    monkeypatch.setenv("GEMINI_API_KEY", "k2")
    router = llm.LLMRouter(provider_ids=["openrouter", "gemini"])
    assert [p.id for p in router.providers()] == ["openrouter", "gemini"]


def test_router_no_keys_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm.LLMRouter(provider_ids=["groq"])


def test_router_models_for_single_active_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un fournisseur n'a qu'un seul modèle actif : celui du registre."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    router = llm.LLMRouter(provider_ids=["gemini"])
    assert router.models_for(llm.PROVIDERS["gemini"]) == ["gemini/gemini-3.6-flash"]
    assert router.model == "gemini/gemini-3.6-flash"


def test_router_model_is_string_attribute(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nooa lit ``llm_client.model`` et l'injecte dans LLMComplete(model_name=...)
    qui exige un str : le routeur doit exposer un attribut, pas une méthode."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    router = llm.LLMRouter(provider_ids=["gemini"])
    assert isinstance(router.model, str)
    assert not callable(router.model)
    assert llm.model_name_of(router) == "gemini/gemini-3.6-flash"


def test_router_no_rotation_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plus de rotation random/adaptive : la sélection passe par le vote."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter()
    assert router.routing_stats()["rotation"] == "vote"


def test_router_majority_answer_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    """Réponses identiques = majorité : c'est la réponse retenue (1er appel)."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model, answer="consensus")
    )
    result = router.call([{"role": "user", "content": "a"}])
    assert result["model"] == "consensus"
    stats = {p["id"]: p for p in router.routing_stats()["providers"]}
    assert stats["gemini"]["successes"] == 1
    assert stats["groq"]["successes"] == 1


def test_router_tracks_actual_last_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    """last_provider_id / last_model reflètent le vainqueur réel du vote,
    pas la config statique du pool (sinon le front affiche un faux modèle)."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    registry = {"gemini/gemini-3.6-flash": [RuntimeError("429 rate limit")]}
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model))
    )
    # Avant tout appel : pas de décision.
    assert router.last_provider_id is None
    assert router.last_model is None
    # Gemini échoue (429) → groq répond seul et gagne le vote.
    router.call([{"role": "user", "content": "a"}])
    assert router.last_provider_id == "groq"
    assert router.last_model == "groq/openai/gpt-oss-120b"
    assert router.model == "gemini/gemini-3.6-flash"  # config statique inchangée


def test_router_all_providers_vote_every_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Même sur le premier appel, chaque fournisseur est consulté (le vote)."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model)
    )
    for _ in range(5):
        router.call([{"role": "user", "content": "a"}])
    stats = {p["id"]: p for p in router.routing_stats()["providers"]}
    assert stats["gemini"]["successes"] == 5
    assert stats["groq"]["successes"] == 5
    # Égalité de signature impossible ici (réponses différentes) : le
    # premier du pool départage à santé égale.
    assert stats["gemini"]["wins"] == 5


def test_router_failed_provider_lets_others_vote(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un 429 sur gemini : groq répond quand même et l'emporte."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    registry = {"gemini/gemini-3.6-flash": [RuntimeError("429 rate limit")]}
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model))
    )
    result = router.call([{"role": "user", "content": "a"}])
    assert result["model"] == "groq/openai/gpt-oss-120b"
    stats = {p["id"]: p for p in router.routing_stats()["providers"]}
    assert stats["gemini"]["failures"] == 1
    assert stats["gemini"]["last_error"] == "429 rate limit"
    assert stats["groq"]["successes"] == 1


def test_router_credit_error_lets_others_vote(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un échec OpenRouter 402 (crédits) est un quota : les autres votent."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    registry = {
        "gemini/gemini-3.6-flash": [
            RuntimeError('OpenrouterException - {"code":402,"message":"Prompt '
                         'tokens limit exceeded: 10335 > 6390 (openrouter_credits)"}')
        ]
    }
    clock = [1000.0]
    router = llm.LLMRouter(
        cooldown=10,
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model)),
        clock=lambda: clock[0],
    )
    result = router.call([{"role": "user", "content": "a"}])
    assert result["model"] == "groq/openai/gpt-oss-120b"
    gemini_stats = router.provider_stats(router.providers()[0])
    assert gemini_stats["failures"] == 1
    assert gemini_stats["cooldown_remaining_s"] == pytest.approx(10.0)


def test_router_context_error_on_one_provider_others_still_vote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un dépassement de contexte sur un fournisseur n'empêche pas les autres
    de voter (leurs fenêtres de contexte peuvent différer)."""
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
    result = router.call([{"role": "user", "content": "a"}])
    assert result["model"] == "groq/openai/gpt-oss-120b"
    gemini_stats = router.provider_stats(router.providers()[0])
    assert gemini_stats["failures"] == 1


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
    """Le print d'échec (glyphe ⚠) ne doit jamais casser le routage.

    Régression : sur console Windows cp1252, `print("⚠ ...")` levait
    UnicodeEncodeError à l'intérieur du handler d'échec et le run mourait.
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
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model))
    )
    result = router.call([{"role": "user", "content": "a"}])
    assert result["model"] == "groq/openai/gpt-oss-120b"


def test_router_cooldown_skips_provider_then_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Après un échec : cooldown simple, le fournisseur est exclu du vote puis
    réintégré automatiquement quand il refroidit."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    registry = {"gemini/gemini-3.6-flash": [RuntimeError("429 rate limit")]}
    clock = [1000.0]
    router = llm.LLMRouter(
        cooldown=10,
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model)),
        clock=lambda: clock[0],
    )
    # Appel 1 : gemini échoue (429) -> cooldown 10 s, groq l'emporte.
    result = router.call([{"role": "user", "content": "a"}])
    assert result["model"] == "groq/openai/gpt-oss-120b"
    gemini_stats = router.provider_stats(router.providers()[0])
    assert gemini_stats["cooldown_remaining_s"] == pytest.approx(10.0)
    # Appel 2 : gemini en cooldown -> exclu du vote, seul groq répond.
    result = router.call([{"role": "user", "content": "b"}])
    assert result["model"] == "groq/openai/gpt-oss-120b"
    assert router.provider_stats(router.providers()[0])["successes"] == 0
    # Appel 3 : cooldown expiré -> gemini vote de nouveau (sa santé remonte).
    clock[0] = 2000.0
    result = router.call([{"role": "user", "content": "c"}])
    assert router.provider_stats(router.providers()[0])["successes"] == 1
    assert result["model"] == "groq/openai/gpt-oss-120b"


def test_router_cooldown_uniform_across_error_kinds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cooldown simple : même durée, quel que soit le type d'erreur."""
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
    router.call([{"role": "user", "content": "a"}])
    gemini_stats = router.provider_stats(router.providers()[0])
    assert gemini_stats["cooldown_remaining_s"] == pytest.approx(10.0)


def test_router_tie_break_favors_most_voted_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """À signatures égales (aucune majorité), la santé historique départage."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model)
    )
    gemini, groq = router.providers()
    # groq a historiquement gagné plus de votes que gemini.
    for _ in range(5):
        router._record_win(groq.id)
    router._record_win(gemini.id)
    result = router.call([{"role": "user", "content": "a"}])
    assert result["model"] == "groq/openai/gpt-oss-120b"


def test_router_acall_vote_async(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    registry = {"gemini/gemini-3.6-flash": [RuntimeError("429 rate limit")]}
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model, registry.get(model))
    )
    result = asyncio.run(router.acall([{"role": "user", "content": "a"}]))
    assert result["model"] == "groq/openai/gpt-oss-120b"


def test_router_stats_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter()
    stats = router.routing_stats()
    assert stats["rotation"] == "vote"
    assert stats["pool"] == ["gemini", "groq"]
    assert [p["id"] for p in stats["providers"]] == ["gemini", "groq"]
    provider = stats["providers"][0]
    assert provider["model"]
    assert provider["base_url"].startswith("http")
    assert provider["successes"] == 0
    assert provider["failures"] == 0
    assert provider["last_error"] is None
    assert "api_key" not in provider


def test_module_routing_stats_uninitialized() -> None:
    llm.reset_router()
    stats = llm.routing_stats()
    assert stats["rotation"] == "uninitialized"
    assert stats["pool"] == []
    assert stats["providers"] == []


def test_get_router_returns_shared_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    first = llm.get_router()
    second = llm.get_router()
    assert first is second
    llm.reset_router()
    third = llm.get_router()
    assert third is not first


def test_router_health_tracked_per_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """La santé est keyée par fournisseur (un seul modèle actif chacun)."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter(
        client_factory=lambda model, **kw: _StubClient(model)
    )
    gemini = router.providers()[0]
    router._record_failure(gemini, RuntimeError("404 model not found"))
    router._record_success(gemini)
    assert router._health_for("gemini").failures == 1
    assert router._health_for("gemini").successes == 1
    assert router._health_for("groq").successes == 0


def test_router_stats_shape_includes_model_breakdown(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    router = llm.LLMRouter()
    provider = router.routing_stats()["providers"][0]
    assert provider["successes"] == 0
    assert provider["failures"] == 0
    assert provider["last_error"] is None
    assert "models" in provider
    assert provider["models"][0]["model"] == "gemini/gemini-3.6-flash"
    assert "api_key" not in provider


# ------------------------------------------------------------ mode fallback


def test_fallback_mode_calls_single_healthy_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mode production : un seul fournisseur sain sollicité par appel (quotas)."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")

    calls: list[str] = []

    def factory(model: str, **kw: object) -> Any:
        class _Healthy:
            async def acall(self, messages, tools=None, output_model=None, **kw2):
                calls.append(model)
                return {"model": model}

        return _Healthy()

    router = llm.LLMRouter(client_factory=factory, mode="fallback")
    router.call([{"role": "user", "content": "a"}])
    router.call([{"role": "user", "content": "b"}])
    assert calls == [
        "gemini/gemini-3.6-flash",
        "gemini/gemini-3.6-flash",
    ]  # groq jamais consulté
    assert router.routing_stats()["rotation"] == "fallback"


def test_fallback_mode_moves_to_next_provider_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Échec du premier fournisseur → suivant de la liste ; cooldown respecté."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")

    def factory(model: str, **kw: object) -> Any:
        class _Flaky:
            async def acall(self, messages, tools=None, output_model=None, **kw2):
                if model.startswith("gemini"):
                    raise RuntimeError("429 resource exhausted")
                return {"model": model}

        return _Flaky()

    router = llm.LLMRouter(client_factory=factory, mode="fallback")
    result = router.call([{"role": "user", "content": "a"}])
    assert str(result["model"]).startswith("groq/")
    assert router.last_provider_id == "groq"
    stats = {p["id"]: p for p in router.routing_stats()["providers"]}
    assert stats["gemini"]["failures"] == 1
    assert stats["groq"]["successes"] == 1

    # Deuxième appel : gemini est en cooldown → groq directement.
    result2 = router.call([{"role": "user", "content": "b"}])
    assert str(result2["model"]).startswith("groq/")


# ------------------------------------------------- correctifs audit 2026-08


def test_nvidia_default_model_is_live_llama() -> None:
    """deepseek-r1 est décommissionné chez NVIDIA (404 en direct) ; le modèle
    par défaut du pool doit être llama-3.3-70b, vérifié actif."""
    assert llm.PROVIDERS["nvidia"].default_model() == "nvidia_nim/meta/llama-3.3-70b-instruct"
    assert all("deepseek" not in m for m in llm.PROVIDERS["nvidia"].models)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            'AiError: you have used up your daily free allocation of 10,000 neurons, '
            "please upgrade to Cloudflare's Workers Paid plan",
            "rate_limit",
        ),
        (
            "litellm.APIConnectionError: CloudflareException - "
            '{"errors":[{"message":"AiError: monthly free allocation exceeded"}]}',
            "rate_limit",
        ),
    ],
)
def test_cloudflare_daily_quota_is_rate_limit(message: str, expected: str) -> None:
    """Le quota quotidien Cloudflare arrive enveloppé dans APIConnectionError :
    il doit être classé rate_limit (état du compte), pas transient (réseau)."""
    assert llm._classify_error(RuntimeError(message)) == expected


class _AffordStub:
    """Client qui refuse max_tokens trop grand puis accepte le plafond.

    ``afford=None`` : aucun refus (fournisseur sain quel que soit max_tokens).
    """

    def __init__(self, model: str, afford: int | None) -> None:
        self.model = model
        self._afford = afford
        self.max_tokens_seen: list[int | None] = []

    async def acall(self, messages, tools=None, output_model=None, **kwargs):
        self.max_tokens_seen.append(kwargs.get("max_tokens"))
        requested = kwargs.get("max_tokens")
        if self._afford is not None and requested is not None and requested > self._afford:
            raise RuntimeError(
                f"This request requires more credits. You requested up to "
                f"{requested} tokens, but can only afford {self._afford}. "
                "To increase, visit https://openrouter.ai/settings/credits"
            )
        return {"model": self.model}


def test_afford_cap_parses_provider_message() -> None:
    # Formulation réelle d'OpenRouter (contient le marqueur "requires more
    # credits" qui la classe rate_limit).
    err = RuntimeError(
        'APIError: OpenrouterException - {"error":{"message":"This request '
        "requires more credits, or fewer max_tokens. You requested up to 16384 "
        'tokens, but can only afford 516."}}'
    )
    assert llm._afford_cap(err) == 516
    # Non applicable hors erreur de quota/billing.
    assert llm._afford_cap(RuntimeError("connection reset")) is None
    assert llm._afford_cap(RuntimeError("context length exceeded, can only afford 10")) is None


def test_fallback_downgrades_max_tokens_within_credit_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenRouter : max_tokens=16384 > solde → une nouvelle tentative à la
    valeur annoncée ('can only afford N') au lieu d'exclure le fournisseur."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k2")
    stubs: dict[str, _AffordStub] = {}

    def factory(model: str, **kw: object) -> Any:
        # Gemini sain (aucun plafond), OpenRouter limité à 2048 tokens.
        afford = None if model.startswith("gemini") else 2048
        stub = _AffordStub(model, afford=afford)
        stubs[model] = stub
        return stub

    router = llm.LLMRouter(client_factory=factory, mode="fallback")
    result = router.call([{"role": "user", "content": "a"}], max_tokens=16384)
    gemini_stub = stubs["gemini/gemini-3.6-flash"]
    openrouter_stub: _AffordStub | None = stubs.get("openrouter/meta-llama/llama-3.3-70b-instruct")
    # Gemini sain répond au premier essai sans repli.
    assert result["model"] == "gemini/gemini-3.6-flash"
    assert gemini_stub.max_tokens_seen == [16384]
    # OpenRouter jamais consulté (aucun client instancié).
    assert openrouter_stub is None


def test_fallback_downgrade_retries_openrouter_at_affordable_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k1")

    def factory(model: str, **kw: object) -> Any:
        return _AffordStub(model, afford=4096)

    router = llm.LLMRouter(client_factory=factory, mode="fallback")
    result = router.call([{"role": "user", "content": "a"}], max_tokens=16384)
    assert result["model"] == "openrouter/meta-llama/llama-3.3-70b-instruct"


def test_fallback_no_downgrade_below_min_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plafond annoncé < _MIN_DOWNGRADE_TOKENS : sortie tronquée inutilisable
    → on abandonne le fournisseur plutôt que de produire du contenu cassé."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k1")

    def factory(model: str, **kw: object) -> Any:
        return _AffordStub(model, afford=516)

    router = llm.LLMRouter(client_factory=factory, mode="fallback")
    with pytest.raises(RuntimeError, match="can only afford"):
        router.call([{"role": "user", "content": "a"}], max_tokens=16384)


# ------------------------------------------ découverte dynamique des modèles


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def test_select_models_rules_filter_and_rank() -> None:
    rule = llm.MODEL_SELECTION_RULES["gemini"]
    raw = [
        "models/gemini-2.0-flash",
        "models/text-embedding-004",
        "models/gemini-1.5-pro",
        "models/imagen-3.0-generate-002",
        "models/gemini-2.5-flash",
    ]
    chosen = llm.select_models(raw, rule)
    # Flash d'abord (préférence n°0), versions récentes avant anciennes,
    # préfixe natif "models/" retiré, embeddings/imagen exclus.
    assert chosen == (
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
    )


def test_select_models_prefers_newest_within_same_tier() -> None:
    """Même rang de préférence → génération la plus récente d'abord : les
    listings annoncent des modèles fermés aux nouveaux comptes (2.5) alors
    que la génération courante (3.6) reste servie."""
    rule = llm.MODEL_SELECTION_RULES["gemini"]
    raw = [
        "models/gemini-2.5-flash",
        "models/gemini-3.1-flash-lite",
        "models/gemini-3.6-flash",
    ]
    assert llm.select_models(raw, rule)[0] == "gemini-3.6-flash"


def test_nvidia_rules_drop_dead_deepseek_route() -> None:
    rule = llm.MODEL_SELECTION_RULES["nvidia"]
    raw = [
        "deepseek-ai/deepseek-r1",
        "meta/llama-3.3-70b-instruct",
        "meta/llama-3.1-405b-instruct",
        "nvidia/nv-embedqa-e5-v5",
    ]
    assert llm.select_models(raw, rule) == ("meta/llama-3.3-70b-instruct",)


def test_discover_models_parses_openai_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    provider = llm.PROVIDERS["groq"]
    captured: dict[str, Any] = {}

    def fake_get(url: str, headers=None, timeout=None) -> llm.httpx.Response:
        captured["url"] = url
        return _FakeResponse(
            {
                "data": [
                    {"id": "groq/openai/gpt-oss-120b"},
                    {"id": ""},
                    {"nope": True},
                ]
            }
        )

    monkeypatch.setattr(llm.httpx, "get", fake_get)
    ids = llm.discover_models(provider)
    assert ids == ("groq/openai/gpt-oss-120b",)
    assert captured["url"].endswith("/models")


def test_discover_models_failure_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def boom(url: str, headers=None, timeout=None) -> llm.httpx.Response:
        raise llm.httpx.ConnectError("network down")

    monkeypatch.setattr(llm.httpx, "get", boom)
    assert llm.discover_models(llm.PROVIDERS["gemini"]) is None


def test_router_uses_discovered_models(monkeypatch: pytest.MonkeyPatch) -> None:
    """La découverte remplace la liste statique (modèle décommissionné inclus)
    et recompose les identifiants natifs au format litellm."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")

    def fake_get(url: str, headers=None, timeout=None) -> llm.httpx.Response:
        return _FakeResponse(
            {
                "data": [
                    {"id": "models/gemini-x-flash"},
                    {"id": "models/gemini-y-pro"},
                    {"id": "models/text-embedding-1"},
                ]
            }
        )

    monkeypatch.setattr(llm.httpx, "get", fake_get)

    seen_models: list[str] = []

    def factory(model: str, **kw: object) -> Any:
        seen_models.append(model)
        return _StubClient(model)

    router = llm.LLMRouter(client_factory=factory, discover=True)
    # Le statique gemini/gemini-3.6-flash est absent de la découverte →
    # remplacé ; le préfixe "models/" natif est retiré puis re-préfixé litellm.
    assert router.model == "gemini/gemini-x-flash"
    router.call([{"role": "user", "content": "a"}])
    assert seen_models == ["gemini/gemini-x-flash"]
    stats = router.routing_stats()["providers"][0]
    assert stats["model"] == "gemini/gemini-x-flash"
    assert stats["models_source"] == "découverte"


def test_discover_models_cloudflare_uses_search_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloudflare : le listing vit sous /client/v4/accounts/{id}/ai/models
    search (clé 'result', champ 'name'), pas sur /ai/v1/models (405)."""
    monkeypatch.delenv("CLOUDFLARE_API_KEY", raising=False)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct-42")
    calls: list[str] = []

    class _Resp:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self._payload

    def fake_get(url: str, headers=None, timeout=None) -> llm.httpx.Response:
        calls.append(url)
        return _Resp({"result": [{"name": "@cf/meta/llama-3.3-70b-instruct"}]})

    monkeypatch.setattr(llm.httpx, "get", fake_get)
    ids = llm.discover_models(llm.PROVIDERS["cloudflare"])
    assert ids == ("@cf/meta/llama-3.3-70b-instruct",)
    assert len(calls) == 1
    assert calls[0].endswith("/accounts/acct-42/ai/models/search")


def test_compose_litellm_ids_prefixes_native_ids() -> None:
    provider = llm.PROVIDERS["nvidia"]
    rule = selection_rule = llm.selection_rule_for("nvidia")
    composed = llm.compose_litellm_ids(
        provider, ("meta/llama-3.3-70b-instruct",), rule
    )
    assert composed == ("nvidia_nim/meta/llama-3.3-70b-instruct",)


def test_router_falls_back_to_static_when_discovery_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Réseau mort au démarrage : les listes statiques prennent le relais."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")

    def boom(url: str, headers=None, timeout=None) -> llm.httpx.Response:
        raise llm.httpx.ConnectError("offline")

    monkeypatch.setattr(llm.httpx, "get", boom)
    router = llm.LLMRouter(client_factory=lambda m, **kw: _StubClient(m), discover=True)
    assert router.model == "gemini/gemini-3.6-flash"
    stats = router.routing_stats()["providers"][0]
    assert stats["models_source"] == "statique"


# ------------------------------------------ rotation intra-fournisseur


def test_fallback_rotates_to_next_candidate_on_transient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3.7-flash saturé (503) → le fournisseur essaie son candidat suivant
    AVANT de basculer chez un autre fournisseur."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    seen: list[str] = []

    def factory(model: str, **kw: object) -> Any:
        seen.append(model)

        class _Client:
            async def acall(self, messages, tools=None, output_model=None, **kw2):
                if model == "gemini/a":
                    raise RuntimeError(
                        "ServiceUnavailableError: 503 high demand, try again later"
                    )
                return {"model": model}

        return _Client()

    router = llm.LLMRouter(client_factory=factory, mode="fallback")
    router._active_models["gemini"] = ("gemini/a", "gemini/b")  # candidats découverts

    result = router.call([{"role": "user", "content": "a"}])
    # Rotation interne : les deux candidats gemini essayés, groq épargné.
    assert seen == ["gemini/a", "gemini/b"]
    assert result["model"] == "gemini/b"
    assert router.last_provider_id == "gemini"


def test_fallback_no_rotation_on_account_level_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quota/TPM : les autres modèles du même compte échoueraient pareil →
    passage direct au fournisseur suivant sans gaspiller d'essais."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEY", "k2")
    seen: list[str] = []

    def factory(model: str, **kw: object) -> Any:
        seen.append(model)

        class _Client:
            async def acall(self, messages, tools=None, output_model=None, **kw2):
                if model.startswith("gemini"):
                    raise RuntimeError(
                        "RateLimitError: Request too large, TPM limit 8000, "
                        "please reduce your message size"
                    )
                return {"model": model}

        return _Client()

    router = llm.LLMRouter(client_factory=factory, mode="fallback")
    router._active_models["gemini"] = ("gemini/a", "gemini/b")

    result = router.call([{"role": "user", "content": "a"}])
    # Un seul essai gemini (erreur de compte) puis bascule groq immédiate.
    assert seen == ["gemini/a", "groq/openai/gpt-oss-120b"]
    assert router.last_provider_id == "groq"
    assert result["model"] == "groq/openai/gpt-oss-120b"
