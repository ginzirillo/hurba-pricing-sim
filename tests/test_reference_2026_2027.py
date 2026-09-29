"""Il motore, con il preset di validazione, deve replicare i risultati
dell'analisi di settembre 2026 entro ±1%."""
import pytest

from app.engine.aggregate import simula
from app.engine.config import apply_preset, load_defaults
from app.engine.covenants import verifica

TOL = 0.01
ATTESI = {
    2026: {"ricavi": 2_660_000, "margine_fully_loaded": 1_280_000, "ecobonus": 727_000, "unita": 455},
    2027: {"ricavi": 4_600_000, "margine_fully_loaded": 2_020_000, "ecobonus": 1_283_000, "rimborso_dealer": 770_000, "unita": 1000},
}


@pytest.fixture(scope="module")
def ris():
    cfg = apply_preset(load_defaults(), "validazione_set2026")
    return simula(cfg), cfg


@pytest.mark.parametrize("anno", [2026, 2027])
def test_aggregati(ris, anno):
    r, _ = ris
    a = r["per_anno"][anno]
    for k, v in ATTESI[anno].items():
        assert a[k] == pytest.approx(v, rel=TOL), f"{anno} {k}: {a[k]:,.0f} vs atteso {v:,.0f}"


def test_margine_pct(ris):
    r, _ = ris
    assert r["per_anno"][2026]["margine_fl_pct"] == pytest.approx(0.486, abs=0.005)
    assert r["per_anno"][2027]["margine_fl_pct"] == pytest.approx(0.440, abs=0.005)


def test_nessun_errore_formule(ris):
    r, _ = ris
    assert r["errori_formule"] == []


def test_covenant_struttura(ris):
    r, cfg = ris
    alerts = verifica(cfg, r)
    assert {a["covenant"] for a in alerts} == {"tier20", "costi_finanziari", "contribuzione"}


def test_formula_invalida_fallback():
    cfg = load_defaults()
    cfg["formule"]["landed"]["expr"] = "fob_usd / (1 +"  # sintassi rotta
    r = simula(cfg)
    assert r["errori_formule"] and "landed" in r["errori_formule"][0]
    assert r["per_anno"][2026]["unita"] == 455
