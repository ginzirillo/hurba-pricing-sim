"""Valutazione sicura delle formule del motore (simpleeval, mai eval/exec).

Ogni formula è una stringa in cfg["formule"][nome]["expr"]. Se una formula
utente non è valida, si usa quella di default e l'errore viene raccolto
in `errori` per essere mostrato nel frontend.
"""
from __future__ import annotations

from typing import Any

from simpleeval import SimpleEval, InvalidExpression

from .config import load_defaults

_DEFAULT_EXPRS: dict[str, str] | None = None

# Ordine di calcolo: ogni formula può usare i risultati delle precedenti.
ORDINE = [
    "netto",
    "netto_pieno",
    "landed",
    "prezzo_vendita",
    "ecobonus",
    "street_price",
    "costo_cessione",
    "costo_factoring",
    "margine_lordo",
    "margine_fully_loaded",
]


def _default_exprs() -> dict[str, str]:
    global _DEFAULT_EXPRS
    if _DEFAULT_EXPRS is None:
        _DEFAULT_EXPRS = {k: v["expr"] for k, v in load_defaults()["formule"].items()}
    return _DEFAULT_EXPRS


class Calcolatore:
    """Valuta la catena di formule su un dizionario di variabili."""

    def __init__(self, formule: dict[str, dict[str, Any]]):
        self.exprs = {k: v["expr"] for k, v in formule.items()}
        self.errori: list[str] = []
        self._ev = SimpleEval(functions={"max": max, "min": min, "abs": abs, "round": round})

    def valuta(self, nome: str, variabili: dict[str, Any]) -> float:
        self._ev.names = variabili
        expr = self.exprs.get(nome, _default_exprs()[nome])
        try:
            return float(self._ev.eval(expr))
        except (InvalidExpression, NameError, TypeError, ZeroDivisionError, SyntaxError, KeyError) as exc:
            msg = f"Formula '{nome}' non valida ({exc}); usata la formula di default."
            if msg not in self.errori:
                self.errori.append(msg)
            return float(self._ev.eval(_default_exprs()[nome]))

    def calcola(self, variabili: dict[str, Any]) -> dict[str, float]:
        """Applica tutte le formule nell'ordine; restituisce i risultati.

        `variabili` deve contenere: listino_effettivo, listino_pieno, iva, fob_usd,
        fx, freight_eur, dazio, sconto_canale, aliquota_eb, quota_ceduta,
        pct_incasso_cessione, pct_factoring, quota_factoring, is_dealer,
        costo_agenti (calcolato a parte in model.py) e base_ecobonus (impostata
        dopo il calcolo di netto/netto_pieno).
        """
        v = dict(variabili)
        out: dict[str, float] = {}
        for nome in ORDINE:
            if nome == "ecobonus":
                v["base_ecobonus"] = v["netto"] if v.get("promo_riduce_base_ecobonus", True) else v["netto_pieno"]
            val = self.valuta(nome, v)
            out[nome] = val
            v[nome] = val
        return out
