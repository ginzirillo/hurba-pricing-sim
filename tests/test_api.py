"""Test degli endpoint FastAPI."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_config_ha_metadati():
    cfg = client.get("/api/config").json()
    assert cfg["parametri"]["iva"]["help"]
    assert "combo3" in cfg["parametri"]["listino_150s_preset"]["options"]


def test_simulate_default_e_override():
    r = client.post("/api/simulate", json={}).json()
    assert r["per_anno"]["2026"]["unita"] == 455
    assert {a["covenant"] for a in r["alert"]} == {"tier20", "costi_finanziari", "contribuzione"}
    r2 = client.post("/api/simulate", json={"override": {"tabelle.volumi.righe[3].unita": 300}}).json()
    assert r2["per_anno"]["2026"]["unita"] == 555


def test_scenari_ciclo_completo(tmp_path, monkeypatch):
    from app.api import scenarios as sc
    monkeypatch.setattr(sc, "SCENARI_DIR", tmp_path)
    cfg = client.get("/api/config").json()
    d = client.post("/api/scenarios", json={"nome": "Test Combo 3", "config": cfg, "note": "prova"}).json()
    assert d["id"].startswith("test-combo-3-")
    assert client.get("/api/scenarios").json()[0]["nome"] == "Test Combo 3"
    assert client.get(f"/api/scenarios/{d['id']}").json()["config"]["parametri"]["iva"]["value"] == 0.22
    assert client.delete(f"/api/scenarios/{d['id']}").json() == {"ok": True}
    assert client.get(f"/api/scenarios/{d['id']}").status_code == 404
