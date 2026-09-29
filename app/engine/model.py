"""Economia unitaria: per ogni modello × canale × tier calcola prezzi,
costi, ecobonus e margini per unità (tutto in € netto IVA salvo listino
e street price che sono IVA inclusa).
"""
from __future__ import annotations

from typing import Any

from .config import param, righe
from .formulas import Calcolatore


# ------------------------------------------------------------------ helpers
def listino_modello(cfg: dict[str, Any], modello: dict[str, Any]) -> float:
    """Listino IVA inclusa, applicando il preset 150S se non 'custom'."""
    preset = param(cfg, "listino_150s_preset")
    if modello["id"] in ("s150", "s150_lr") and preset != "custom":
        for r in righe(cfg, "listini_150s"):
            if r["id"] == preset:
                return float(r[modello["id"]])
    return float(modello["listino"])


def aliquota_ecobonus(cfg: dict[str, Any], anno: int) -> float:
    for r in righe(cfg, "ecobonus"):
        if int(r["anno"]) == int(anno):
            if r.get("usa_mix"):
                m = float(r["mix_rottamazione"])
                return float(r["senza_rottamazione"]) * (1 - m) + float(r["con_rottamazione"]) * m
            return float(r["flat"])
    return 0.0


def mix_canale(cfg: dict[str, Any], anno: int) -> dict[str, float]:
    for r in righe(cfg, "mix_canale"):
        if int(r["anno"]) == int(anno):
            return {k: float(r[k]) for k in ("diretta", "dealer", "distributore")}
    return {"diretta": 1.0, "dealer": 0.0, "distributore": 0.0}


def sconto_canale(cfg: dict[str, Any], canale_id: str) -> float:
    for r in righe(cfg, "canali"):
        if r["id"] == canale_id:
            return float(r["sconto"] or 0.0)
    return 0.0


def canale_info(cfg: dict[str, Any], canale_id: str) -> dict[str, Any]:
    for r in righe(cfg, "canali"):
        if r["id"] == canale_id:
            return r
    return {"id": canale_id, "factoring": False, "agenti": False, "sconto": 0.0}


def costo_agenti_unit(cfg: dict[str, Any], base_vals: dict[str, float]) -> float:
    """Somma delle provvigioni per unità sulle categorie di agenti attive."""
    if not param(cfg, "agenti_attivi"):
        return 0.0
    basi = {
        "listino": base_vals["listino_effettivo"],
        "netto": base_vals["netto"],
        "prezzo_dealer": base_vals["prezzo_vendita"],
        "margine": base_vals["margine_lordo"],
    }
    tot = 0.0
    for a in righe(cfg, "agenti"):
        if a.get("attivo"):
            tot += basi[a["base"]] * float(a["pct"]) * float(a["quota"])
    return tot


# ------------------------------------------------------------------ core
def unit_economics(
    cfg: dict[str, Any],
    calc: Calcolatore,
    modello: dict[str, Any],
    anno: int,
    canale_id: str,
    sconto_tier: float,
    promo_sconto_eur: float = 0.0,
) -> dict[str, float]:
    """Economia per una singola unità in una combinazione data."""
    canale = canale_info(cfg, canale_id)
    listino_pieno = listino_modello(cfg, modello)
    listino_eff = listino_pieno - promo_sconto_eur
    sconto = sconto_tier if canale_id == "dealer" else sconto_canale(cfg, canale_id)

    v: dict[str, Any] = {
        "listino_pieno": listino_pieno,
        "listino_effettivo": listino_eff,
        "iva": float(param(cfg, "iva")),
        "fob_usd": float(modello["fob_usd"]),
        "freight_eur": float(modello["freight_eur"]),
        "fx": float(param(cfg, "fx_usd_eur")),
        "dazio": float(param(cfg, "dazio")),
        "sconto_canale": sconto,
        "aliquota_eb": aliquota_ecobonus(cfg, anno),
        "promo_riduce_base_ecobonus": bool(param(cfg, "promo_riduce_base_ecobonus")),
        "quota_ceduta": float(param(cfg, "quota_ceduta")),
        "pct_incasso_cessione": float(param(cfg, "pct_incasso_cessione")),
        "pct_factoring": float(param(cfg, "pct_factoring")),
        "quota_factoring": float(param(cfg, "quota_factoring")),
        "is_dealer": 1.0 if canale.get("factoring") else 0.0,
        "costo_agenti": 0.0,
    }
    out = calc.calcola(v)

    # Agenti: dipendono da prezzo/margine, quindi si calcolano dopo il primo passaggio
    if canale.get("agenti"):
        out["costo_agenti"] = costo_agenti_unit(cfg, {**v, **out})
    else:
        out["costo_agenti"] = 0.0
    v2 = {**v, **out}
    out["margine_fully_loaded"] = calc.valuta("margine_fully_loaded", v2)

    out["listino_pieno"] = listino_pieno
    out["listino_effettivo"] = listino_eff
    out["promo_sconto"] = promo_sconto_eur
    out["sconto_canale"] = sconto
    out["aliquota_eb"] = v["aliquota_eb"]
    out["rimborso_dealer"] = out["ecobonus"] if canale_id in ("dealer", "distributore") else 0.0
    out["contribuzione_pct"] = (
        out["margine_fully_loaded"] / out["prezzo_vendita"] if out["prezzo_vendita"] else 0.0
    )
    out["margine_lordo_pct"] = out["margine_lordo"] / out["prezzo_vendita"] if out["prezzo_vendita"] else 0.0
    return out
