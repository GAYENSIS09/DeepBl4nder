"""Tests du socle SaaS : auth, RBAC, isolation multi-tenant, CRUD et pipeline."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from DeepBl4nder.api.app import create_app, sse_event_stream

PASSWORD = "mot-de-passe-123"


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(
        database_url=f"sqlite:///{tmp_path / 'saas.db'}",
        secret_key="test-secret",
        data_dir=str(tmp_path / "runs"),
    )
    with TestClient(app) as client:
        yield client


def _register(client: TestClient, email: str, full_name: str = "") -> str:
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": full_name},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _org(client: TestClient, token: str, name: str = "Studio A") -> dict[str, str]:
    resp = client.post("/api/organizations", json={"name": name}, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _workspace(client: TestClient, token: str, org_id: str) -> dict[str, str]:
    resp = client.post(f"/api/organizations/{org_id}/workspaces", json={"name": "Prod"}, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _project(client: TestClient, token: str, workspace_id: str) -> dict[str, str]:
    resp = client.post(
        f"/api/workspaces/{workspace_id}/projects",
        json={"name": "Ruelle", "description": "Test"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _production(client: TestClient, token: str, project_id: str) -> dict[str, str]:
    resp = client.post(
        f"/api/projects/{project_id}/productions",
        json={"name": "Rainy Alley", "brief": "Une ruelle sombre sous la pluie."},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_register_creates_default_org_and_workspace(client: TestClient) -> None:
    token = _register(client, "alice@example.com", "Alice")
    me = client.get("/api/me", headers=_auth(token))
    assert me.status_code == 200
    payload = me.json()
    assert payload["user"]["email"] == "alice@example.com"
    assert len(payload["memberships"]) == 1
    org_id = payload["memberships"][0]["organization_id"]
    assert payload["memberships"][0]["role"] == "owner"
    workspaces = client.get(f"/api/organizations/{org_id}/workspaces", headers=_auth(token))
    assert [ws["name"] for ws in workspaces.json()] == ["Default"]


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    _register(client, "bob@example.com")
    resp = client.post(
        "/api/auth/register",
        json={"email": "bob@example.com", "password": PASSWORD},
    )
    assert resp.status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/register",
        json={"email": "carol@example.com", "password": "short"},
    )
    assert resp.status_code == 422


def test_login_and_wrong_password(client: TestClient) -> None:
    _register(client, "dave@example.com")
    ok = client.post("/api/auth/login", json={"email": "dave@example.com", "password": PASSWORD})
    assert ok.status_code == 200
    assert ok.json()["token_type"] == "bearer"
    bad = client.post("/api/auth/login", json={"email": "dave@example.com", "password": "nope"})
    assert bad.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    resp = client.get("/api/me")
    assert resp.status_code == 401
    resp2 = client.get("/api/me", headers=_auth("not-a-token"))
    assert resp2.status_code == 401


def test_crud_org_workspace_project_production(client: TestClient) -> None:
    token = _register(client, "eva@example.com")
    org = _org(client, token)
    ws = _workspace(client, token, org["id"])
    project = _project(client, token, ws["id"])
    production = _production(client, token, project["id"])

    detail = client.get(f"/api/organizations/{org['id']}", headers=_auth(token))
    assert detail.status_code == 200
    assert detail.json()["role"] == "owner"
    assert len(detail.json()["members"]) == 1

    prods = client.get(f"/api/projects/{project['id']}/productions", headers=_auth(token))
    assert len(prods.json()) == 1
    assert prods.json()[0]["brief"] == "Une ruelle sombre sous la pluie."
    assert prods.json()[0]["status"] == "draft"

    single = client.get(f"/api/productions/{production['id']}", headers=_auth(token))
    assert single.status_code == 200
    assert single.json()["name"] == "Rainy Alley"


def test_tenant_isolation_between_users(client: TestClient) -> None:
    token_a = _register(client, "anna@example.com")
    token_b = _register(client, "bella@example.com")
    org_a = _org(client, token_a, "Studio A")
    ws_a = _workspace(client, token_a, org_a["id"])
    project_a = _project(client, token_a, ws_a["id"])
    production_a = _production(client, token_a, project_a["id"])

    # B ne voit aucune ressource de A (404, pas de fuite d'existence)
    assert client.get(f"/api/organizations/{org_a['id']}", headers=_auth(token_b)).status_code == 404
    assert (
        client.post(f"/api/organizations/{org_a['id']}/workspaces", json={"name": "X"}, headers=_auth(token_b)).status_code
        == 404
    )
    assert client.get(f"/api/workspaces/{ws_a['id']}/projects", headers=_auth(token_b)).status_code == 404
    assert client.get(f"/api/projects/{project_a['id']}", headers=_auth(token_b)).status_code == 404
    assert client.get(f"/api/projects/{project_a['id']}/productions", headers=_auth(token_b)).status_code == 404
    assert client.get(f"/api/productions/{production_a['id']}", headers=_auth(token_b)).status_code == 404

    # Les organisations listées par B ne contiennent pas celle de A
    orgs_b = client.get("/api/organizations", headers=_auth(token_b))
    assert [org["name"] for org in orgs_b.json()] == ["Bella Organization"]


def test_rbac_roles_gate_actions(client: TestClient) -> None:
    owner_token = _register(client, "owner@example.com", "Owner")
    org = _org(client, owner_token)

    # Inviter un éditeur et un viewer (owner)
    add_editor = client.post(
        f"/api/organizations/{org['id']}/members",
        json={"email": "editor@example.com", "role": "editor"},
        headers=_auth(owner_token),
    )
    assert add_editor.status_code == 201
    add_viewer = client.post(
        f"/api/organizations/{org['id']}/members",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers=_auth(owner_token),
    )
    assert add_viewer.status_code == 201

    editor_token = _register(client, "editor@example.com")
    viewer_token = _register(client, "viewer@example.com")

    # Le viewer ne peut pas créer de workspace/projet/production (403)
    assert (
        client.post(
            f"/api/organizations/{org['id']}/workspaces",
            json={"name": "X"},
            headers=_auth(viewer_token),
        ).status_code
        == 403
    )

    # L'éditeur peut créer un workspace et un projet
    ws = _workspace(client, editor_token, org["id"])
    project = _project(client, editor_token, ws["id"])

    # Le viewer ne peut pas créer de production (403), l'éditeur oui
    assert (
        client.post(
            f"/api/projects/{project['id']}/productions",
            json={"name": "P", "brief": "brief"},
            headers=_auth(viewer_token),
        ).status_code
        == 403
    )
    production = _production(client, editor_token, project["id"])
    assert production["status"] == "draft"

    # Le viewer peut lire
    assert (
        client.get(f"/api/productions/{production['id']}", headers=_auth(viewer_token)).status_code == 200
    )

    # Seul le owner/admin peut gérer les membres (403 pour l'éditeur)
    assert (
        client.post(
            f"/api/organizations/{org['id']}/members",
            json={"email": "someone@example.com", "role": "viewer"},
            headers=_auth(editor_token),
        ).status_code
        == 403
    )


def test_member_role_update_and_list(client: TestClient) -> None:
    owner_token = _register(client, "mia@example.com")
    org = _org(client, owner_token)
    client.post(
        f"/api/organizations/{org['id']}/members",
        json={"email": "miguel@example.com", "role": "viewer"},
        headers=_auth(owner_token),
    )
    _register(client, "miguel@example.com")
    # Ajout du même membre avec un autre rôle => mise à jour
    resp = client.post(
        f"/api/organizations/{org['id']}/members",
        json={"email": "miguel@example.com", "role": "editor"},
        headers=_auth(owner_token),
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "editor"
    members = client.get(f"/api/organizations/{org['id']}/members", headers=_auth(owner_token)).json()
    roles = {m["email"]: m["role"] for m in members}
    assert roles["miguel@example.com"] == "editor"


def test_delete_project_removes_productions(client: TestClient) -> None:
    token = _register(client, "nina@example.com")
    org = _org(client, token)
    ws = _workspace(client, token, org["id"])
    project = _project(client, token, ws["id"])
    production = _production(client, token, project["id"])

    resp = client.delete(f"/api/projects/{project['id']}", headers=_auth(token))
    assert resp.status_code == 204
    assert client.get(f"/api/productions/{production['id']}", headers=_auth(token)).status_code == 404
    assert client.get(f"/api/projects/{project['id']}", headers=_auth(token)).status_code == 404


# ----- Phase D : exécution du pipeline via l'API -----


class _StubDirector:
    async def plan_scene(self, brief, story_spec=None, storyboard_spec=None):
        from DeepBl4nder.domain.scene import SceneSpec, ShotSpec

        return SceneSpec(brief=brief.text, shots=[ShotSpec(duration=1.0)])


class _StubBlender:
    async def build_script(self, spec):
        from DeepBl4nder.domain.scene import BlenderScript

        return BlenderScript(code="import bpy\n", scene_name="stub_scene")


class _StubQA:
    async def assess(self, spec, artifact_path, code=""):
        from DeepBl4nder.domain.qa import QAReport

        return QAReport(passed=True, score=1.0)


class _StubAudio:
    async def plan_audio(self, spec):
        from DeepBl4nder.domain.media import AudioPlan

        return AudioPlan(mood="neutral", music_theme="stub", tempo=90.0)


class _StubLocalization:
    def default_languages(self):
        return ["fr"]

    async def plan_localization(self, spec, language, languages=None):
        from DeepBl4nder.domain.media import LanguagePackage

        return LanguagePackage(language=language, languages=list(languages or ["fr"]))


class _StubCompositing:
    async def plan_compositing(self, spec):
        from DeepBl4nder.domain.media import CompositeSpec

        return CompositeSpec(passes=["diffuse", "mist"], grade="balanced")


class _StubStory:
    async def plan_story(self, brief):
        from DeepBl4nder.domain.narrative import StorySpec

        return StorySpec(logline=brief.text[:100], synopsis=brief.text)


class _StubStoryboard:
    async def plan_storyboard(self, story_spec):
        from DeepBl4nder.domain.narrative import StoryboardSpec

        return StoryboardSpec(shots=[])


class _StubCharacterDesigner:
    async def design_characters(self, scene):
        from DeepBl4nder.domain.media import CharacterDesignResult, CharacterModel
        return CharacterDesignResult(characters=[
            CharacterModel(name="Hero", description="Main character", geometry_type="primitive"),
        ])

class _StubAnimator:
    async def generate_animations(self, scene):
        from DeepBl4nder.domain.media import AnimationResult, AnimationClip
        return AnimationResult(clips=[
            AnimationClip(character_name="Hero", shot_index=0, duration=1.0),
        ])

class _StubEnvironmentArtist:
    async def design_environment(self, scene):
        from dataclasses import dataclass, field
        from typing import Any

        @dataclass
        class EnvResult:
            mood: str = "neutral"
            assets: list = field(default_factory=list)
            def to_mapping(self):
                return {"mood": self.mood, "assets": self.assets}
        return EnvResult()

class _StubMusicComposer:
    async def compose_music(self, scene):
        from DeepBl4nder.domain.media import MusicPlan
        return MusicPlan(main_theme="stub_theme", total_duration=5.0)

class _StubSoundDesigner:
    async def design_sound(self, scene):
        from DeepBl4nder.domain.media import SoundDesignPlan
        return SoundDesignPlan()

class _StubReview:
    async def review_production(self, scene, render_output=None, audio_plan=None, composite_spec=None):
        from dataclasses import dataclass

        @dataclass
        class ReviewReport:
            approved: bool = True
            notes: str = "stub review passed"
            score: float = 1.0
            def to_mapping(self):
                return {"approved": self.approved, "notes": self.notes, "score": self.score}
        return ReviewReport()

def _stub_agents():
    return (
        _StubStory(),
        _StubStoryboard(),
        _StubDirector(),
        _StubBlender(),
        _StubQA(),
        _StubAudio(),
        _StubLocalization(),
        _StubCompositing(),
        _StubCharacterDesigner(),
        _StubAnimator(),
        _StubEnvironmentArtist(),
        _StubMusicComposer(),
        _StubSoundDesigner(),
        _StubReview(),
    )


def _project_chain(client: TestClient, token: str) -> dict[str, str]:
    org = _org(client, token)
    ws = _workspace(client, token, org["id"])
    project = _project(client, token, ws["id"])
    return _production(client, token, project["id"])


def _wait_status(client: TestClient, token: str, production_id: str, timeout: float = 30.0) -> dict[str, object]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = client.get(f"/api/productions/{production_id}", headers=_auth(token)).json()
        status = payload.get("status", "")
        if status in ("completed", "failed", "blocked", "cancelled"):
            return payload
        time.sleep(0.05)
    raise AssertionError(f"production stuck in {status!r}")


def test_run_pipeline_e2e(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("DeepBl4nder.api.pipeline.build_agents", _stub_agents)
    token = _register(client, "run@example.com", "Run")
    production = _project_chain(client, token)

    resp = client.post(f"/api/productions/{production['id']}/run", headers=_auth(token))
    assert resp.status_code == 202
    assert resp.json()["status"] == "queued"

    detail = _wait_status(client, token, production["id"])
    assert detail["status"] == "completed"
    assert detail["progress"] == 1.0
    assert detail["version"] == 2
    assert detail["finished_at"] is not None

    artifacts = client.get(f"/api/productions/{production['id']}/artifacts", headers=_auth(token)).json()
    names = {a["name"] for a in artifacts}
    assert "scene_spec.json" in names
    assert "script.py" in names
    # Post-production (étapes 14-16)
    assert "audio_plan.json" in names
    assert "composite_spec.json" in names
    assert "language_package_fr.json" in names

    # Un second run est possible une fois terminé
    resp2 = client.post(f"/api/productions/{production['id']}/run", headers=_auth(token))
    assert resp2.status_code == 202
    detail2 = _wait_status(client, token, production["id"])
    assert detail2["status"] == "completed"
    assert detail2["version"] == 3


def test_run_pipeline_conflict_when_running(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("DeepBl4nder.api.pipeline.build_agents", _stub_agents)
    token = _register(client, "busy@example.com")
    production = _project_chain(client, token)

    resp = client.post(f"/api/productions/{production['id']}/run", headers=_auth(token))
    assert resp.status_code == 202
    # Deuxième lancement immédiat : conflit (queued ou running)
    resp2 = client.post(f"/api/productions/{production['id']}/run", headers=_auth(token))
    assert resp2.status_code in (202, 409)
    _wait_status(client, token, production["id"])


def test_cancel_production(client: TestClient) -> None:
    token = _register(client, "cancel@example.com")
    production = _project_chain(client, token)

    resp = client.post(f"/api/productions/{production['id']}/cancel", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # Annuler une production déjà terminée => conflit
    resp2 = client.post(f"/api/productions/{production['id']}/cancel", headers=_auth(token))
    assert resp2.status_code == 409


def test_tenant_cannot_manage_other_production(client: TestClient) -> None:
    token_a = _register(client, "owner@example.com")
    production_a = _project_chain(client, token_a)
    token_b = _register(client, "intruder@example.com")

    assert client.post(f"/api/productions/{production_a['id']}/run", headers=_auth(token_b)).status_code == 404
    assert client.post(f"/api/productions/{production_a['id']}/cancel", headers=_auth(token_b)).status_code == 404
    assert client.get(f"/api/productions/{production_a['id']}/artifacts", headers=_auth(token_b)).status_code == 404
    assert client.get(f"/api/productions/{production_a['id']}/events", headers=_auth(token_b)).status_code == 404





def _collect_sse(bus, production_id, after=None, limit=2):
    """Lit 'limit' evenements via le generateur SSE reel (hors HTTP)."""

    async def _run():
        queue = await bus.subscribe(production_id, after)
        chunks: list[dict[str, object]] = []
        async for chunk in sse_event_stream(queue, bus.unsubscribe):
            if chunk.startswith("data: "):
                chunks.append(json.loads(chunk[6:]))
            if len(chunks) >= limit:
                break
        return chunks

    return asyncio.run(_run())


def test_production_events_sse_replays_history(client: TestClient) -> None:
    token = _register(client, "sse@example.com")
    production = _project_chain(client, token)
    pid = production["id"]

    bus = client.app.state.bus
    bus.publish_nowait({"type": "run_started", "production_id": pid})
    bus.publish_nowait({"type": "step_completed", "production_id": pid, "step": "director"})
    bus.publish_nowait({"type": "run_started", "production_id": "other", "step": "x"})

    received = _collect_sse(bus, pid)

    assert [e["type"] for e in received] == ["run_started", "step_completed"]
    assert all(e["production_id"] == pid for e in received)
    assert received[1]["seq"] > received[0]["seq"]


def test_production_events_sse_respects_after(client: TestClient) -> None:
    token = _register(client, "sse3@example.com")
    production = _project_chain(client, token)
    pid = production["id"]

    bus = client.app.state.bus
    bus.publish_nowait({"type": "run_started", "production_id": pid})
    bus.publish_nowait({"type": "step_completed", "production_id": pid, "step": "qa"})

    received = _collect_sse(bus, pid, after=1, limit=1)

    assert len(received) == 1
    assert received[0]["type"] == "step_completed"
    assert received[0]["seq"] > 1


def test_cors_allows_frontend_origin(client: TestClient) -> None:
    headers = {"Origin": "http://localhost:3000"}
    resp = client.get("/api/me", headers=headers)
    assert resp.status_code == 401
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_allows_authorization_header(client: TestClient) -> None:
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    }
    resp = client.options("/api/productions/x/events", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "authorization" in resp.headers.get("access-control-allow-headers", "").lower()


def _run_workdir(client: TestClient, production_id: str) -> Path:
    return Path(client.app.state.data_dir) / "runs" / production_id


def test_revision_relaunches_pipeline(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("DeepBl4nder.api.pipeline.build_agents", _stub_agents)
    token = _register(client, "rev@example.com")
    production = _project_chain(client, token)

    resp = client.post(f"/api/productions/{production['id']}/run", headers=_auth(token))
    assert resp.status_code == 202
    detail = _wait_status(client, token, production["id"])
    assert detail["status"] == "completed"
    assert detail["version"] == 2

    resp = client.post(
        f"/api/productions/{production['id']}/revision",
        json={"target_step": "qa", "comment": "Plus de pluie sur les réverbères."},
        headers=_auth(token),
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["status"] == "revising"

    detail2 = _wait_status(client, token, production["id"])
    assert detail2["status"] == "completed"
    assert detail2["version"] == 3

    artifacts = client.get(f"/api/productions/{production['id']}/artifacts", headers=_auth(token)).json()
    assert any(a["name"].startswith("revision_request_") for a in artifacts)


def test_revision_conflict_when_running(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("DeepBl4nder.api.pipeline.build_agents", _stub_agents)
    token = _register(client, "revbusy@example.com")
    production = _project_chain(client, token)

    resp = client.post(f"/api/productions/{production['id']}/run", headers=_auth(token))
    assert resp.status_code == 202
    resp2 = client.post(
        f"/api/productions/{production['id']}/revision",
        json={"target_step": "qa", "comment": "Trop tard"},
        headers=_auth(token),
    )
    assert resp2.status_code in (202, 409)
    _wait_status(client, token, production["id"])


def test_artifact_download_and_path_traversal(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("DeepBl4nder.api.pipeline.build_agents", _stub_agents)
    token = _register(client, "dl@example.com")
    production = _project_chain(client, token)
    pid = production["id"]

    resp = client.post(f"/api/productions/{pid}/run", headers=_auth(token))
    assert resp.status_code == 202
    _wait_status(client, token, pid)

    dl = client.get(f"/api/productions/{pid}/artifacts/scene_spec.json", headers=_auth(token))
    assert dl.status_code == 200
    assert "brief" in dl.json()
    assert dl.headers["content-type"] == "application/json"

    # Traversal refusé
    for evil in ("../saas.db", "%2e%2e/saas.db", "..\\saas.db"):
        resp = client.get(f"/api/productions/{pid}/artifacts/{evil}", headers=_auth(token))
        assert resp.status_code == 404

    # Inexistant
    assert client.get(f"/api/productions/{pid}/artifacts/nope.json", headers=_auth(token)).status_code == 404
    # Hors périmètre (pas de download sans auth)
    assert client.get(f"/api/productions/{pid}/artifacts/scene_spec.json").status_code == 401


def test_preview_prefers_image_then_404(client: TestClient) -> None:
    token = _register(client, "prev@example.com")
    production = _project_chain(client, token)
    pid = production["id"]

    assert client.get(f"/api/productions/{pid}/preview", headers=_auth(token)).status_code == 404

    workdir = _run_workdir(client, pid)
    (workdir / "frames").mkdir(parents=True)
    (workdir / "frames" / "frame_0001.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (workdir / "frames" / "out.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    resp = client.get(f"/api/productions/{pid}/preview", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content.startswith(b"\x89PNG")


def test_worker_status_reports_runs(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    token = _register(client, "worker@example.com")
    resp = client.get("/api/worker", headers=_auth(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] in ("idle", "online")
    assert payload["processed"] >= 0
    assert payload["failed"] >= 0
    assert payload["rotation"] in ("random", "adaptive", "vote", "fallback")
    assert isinstance(payload["routing"], list)
    for provider in payload["routing"]:
        assert provider["id"]
        assert provider["model"]
        assert provider["base_url"]
        assert "successes" in provider
        assert "failures" in provider
        assert "last_error" in provider

    monkeypatch.setattr("DeepBl4nder.api.pipeline.build_agents", _stub_agents)
    production = _project_chain(client, token)
    resp = client.post(f"/api/productions/{production['id']}/run", headers=_auth(token))
    assert resp.status_code == 202
    _wait_status(client, token, production["id"])

    payload = client.get("/api/worker", headers=_auth(token)).json()
    assert payload["processed"] >= 1


def test_usage_reports_consumption_and_quotas(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DeepBl4nder_QUOTA_PRODUCTIONS", "5")
    monkeypatch.setenv("DeepBl4nder_QUOTA_COST", "4.5")
    token = _register(client, "usage@example.com")
    _project_chain(client, token)

    resp = client.get("/api/usage", headers=_auth(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["productions"] == 1
    assert payload["runs"] == 0
    assert payload["total_cost"] == 0.0
    assert payload["quotas"] == {"productions": 5, "cost": 4.5}


