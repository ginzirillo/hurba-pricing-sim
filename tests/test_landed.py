"""Verifica dei costi landed per modello (formula default)."""
import pytest

from app.engine.config import load_defaults, righe
from app.engine.formulas import Calcolatore
from app.engine.model import unit_economics

ATTESI = {"brezza_50": 1440, "brezza_125": 1440, "s150": 1531, "s150_lr": 2038, "s200": 2371, "s300": 3246}


@pytest.mark.parametrize("mid,atteso", ATTESI.items())
def test_landed(mid, atteso):
    cfg = load_defaults()
    calc = Calcolatore(cfg["formule"])
    m = next(r for r in righe(cfg, "modelli") if r["id"] == mid)
    ue = unit_economics(cfg, calc, m, 2026, "diretta", 0.0)
    assert ue["landed"] == pytest.approx(atteso, abs=1.0)
    assert calc.errori == []
