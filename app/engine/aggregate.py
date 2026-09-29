"""Aggregazione: dalle economie unitarie ai totali per anno e per modello."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import param, righe
from .formulas import Calcolatore
from .model import (
    aliquota_ecobonus,
    listino_modello,
    mix_canale,
    unit_economics,
)

CAMPI_SOMMA = [
    "ricavi", "landed", "margine_lordo", "ecobonus", "rimborso_dealer",
    "costo_cessione", "costo_factoring", "costo_agenti", "costo_promo",
    "margine_fully_loaded", "unita",
]


# ------------------------------------------------------------------ volumi
def volumi_anno(cfg: dict[str, Any], anno: int) -> dict[str, float]:
    """Unità per modello nell'anno, risolvendo la ripartizione 150S."""
    raw = {r["modello"]: float(r["unita"]) for r in righe(cfg, "volumi") if int(r["anno"]) == int(anno)}
    modo = param(cfg, "split_150s_mode")
    if modo == "percentuale":
        tot = raw.pop("s150_totale", 0.0)
        pct_lr = float(param(cfg, "pct_150s_lr"))
        raw["s150"] = tot * (1 - pct_lr)
        raw["s150_lr"] = tot * pct_lr
    else:
        raw.pop("s150_totale", None)
    return {k: v for k, v in raw.items() if v > 0}


def unita_promo(cfg: dict[str, Any], anno: int, volumi: dict[str, float]) -> dict[str, list[tuple[dict, float]]]:
    """Per ogni modello: lista di (promo, unità in promo). Il tetto si
    ripartisce tra i modelli della promo in proporzione ai volumi."""
    out: dict[str, list[tuple[dict, float]]] = defaultdict(list)
    for p in righe(cfg, "promo"):
        if not p.get("attiva") or int(p["anno"]) != int(anno):
            continue
        modelli = [m for m in p["modelli"] if volumi.get(m, 0) > 0]
        tot = sum(volumi[m] for m in modelli)
        if tot <= 0:
            continue
        cap = min(float(p["unita_max"]), tot)
        for m in modelli:
            out[m].append((p, cap * volumi[m] / tot))
    return out


def sconto_promo_eur(p: dict[str, Any], listino: float) -> float:
    return float(p["valore"]) if p["tipo"] == "euro" else listino * float(p["valore"])


# ------------------------------------------------------------------ core
def _acc(target: dict[str, float], ue: dict[str, float], n: float, promo_eur: float) -> None:
    target["unita"] += n
    target["ricavi"] += ue["prezzo_vendita"] * n
    target["landed"] += ue["landed"] * n
    target["margine_lordo"] += ue["margine_lordo"] * n
    target["ecobonus"] += ue["ecobonus"] * n
    target["rimborso_dealer"] += ue["rimborso_dealer"] * n
    target["costo_cessione"] += ue["costo_cessione"] * n
    target["costo_factoring"] += ue["costo_factoring"] * n
    target["costo_agenti"] += ue["costo_agenti"] * n
    target["costo_promo"] += promo_eur / (1 + 0.0) * n  # informativo, IVA inclusa
    target["margine_fully_loaded"] += ue["margine_fully_loaded"] * n


def _nuovo() -> dict[str, float]:
    return {k: 0.0 for k in CAMPI_SOMMA}


def simula(cfg: dict[str, Any]) -> dict[str, Any]:
    """Esegue la simulazione completa. Restituisce un dizionario serializzabile."""
    calc = Calcolatore(cfg["formule"])
    modelli = {m["id"]: m for m in righe(cfg, "modelli")}
    tiers = righe(cfg, "tier_dealer")
    anni = cfg["meta"]["anni"]

    per_anno: dict[int, dict[str, Any]] = {}
    per_modello: dict[str, dict[str, Any]] = {}
    combinazioni: list[dict[str, Any]] = []

    for anno in anni:
        vol = volumi_anno(cfg, anno)
        mix = mix_canale(cfg, anno)
        promo_map = unita_promo(cfg, anno, vol)
        tot_anno = _nuovo()
        tot_canale: dict[str, dict[str, float]] = {c: _nuovo() for c in ("diretta", "dealer", "distributore")}
        tot_tier: dict[str, dict[str, float]] = {t["id"]: _nuovo() for t in tiers}

        for mid, n_tot in vol.items():
            m = modelli[mid]
            listino = listino_modello(cfg, m)
            # blocchi (promo, unità): prima le unità promo, poi quelle a listino pieno
            blocchi: list[tuple[float, float, str]] = []  # (sconto_eur, unità, nome_promo)
            n_promo = 0.0
            for p, n_p in promo_map.get(mid, []):
                blocchi.append((sconto_promo_eur(p, listino), n_p, p["nome"]))
                n_promo += n_p
            blocchi.append((0.0, max(n_tot - n_promo, 0.0), ""))

            tot_mod = per_modello.setdefault(mid, {"nome": m["nome"], "anni": {}})
            tot_mod_anno = _nuovo()

            for sconto_eur, n_blocco, nome_promo in blocchi:
                if n_blocco <= 0:
                    continue
                for canale, quota in mix.items():
                    n_can = n_blocco * quota
                    if n_can <= 0:
                        continue
                    if canale == "dealer":
                        combo_tiers = [(t["id"], float(t["sconto"]), float(t[f"mix_{anno}"])) for t in tiers]
                    else:
                        combo_tiers = [(None, 0.0, 1.0)]
                    for tid, sconto_t, quota_t in combo_tiers:
                        n = n_can * quota_t
                        if n <= 0:
                            continue
                        ue = unit_economics(cfg, calc, m, anno, canale, sconto_t, sconto_eur)
                        _acc(tot_anno, ue, n, sconto_eur)
                        _acc(tot_canale[canale], ue, n, sconto_eur)
                        _acc(tot_mod_anno, ue, n, sconto_eur)
                        if tid:
                            _acc(tot_tier[tid], ue, n, sconto_eur)
                        combinazioni.append({
                            "anno": anno, "modello": mid, "nome_modello": m["nome"],
                            "canale": canale, "tier": tid, "promo": nome_promo,
                            "unita": n, **ue,
                        })
            tot_mod["anni"][anno] = tot_mod_anno

        costi_fin = tot_anno["costo_cessione"] + tot_anno["costo_factoring"]
        per_anno[anno] = {
            **tot_anno,
            "costi_finanziari": costi_fin,
            "margine_lordo_pct": tot_anno["margine_lordo"] / tot_anno["ricavi"] if tot_anno["ricavi"] else 0.0,
            "margine_fl_pct": tot_anno["margine_fully_loaded"] / tot_anno["ricavi"] if tot_anno["ricavi"] else 0.0,
            "aliquota_eb": aliquota_ecobonus(cfg, anno),
            "per_canale": tot_canale,
            "per_tier": tot_tier,
        }

    return {
        "per_anno": per_anno,
        "per_modello": per_modello,
        "combinazioni": combinazioni,
        "benchmark": ladder_benchmark(cfg),
        "errori_formule": calc.errori,
    }


# ------------------------------------------------------------------ benchmark
def ladder_benchmark(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Ladder prezzi: HURBA e concorrenti, con e senza ecobonus (stessa aliquota per tutti)."""
    anno = int(param(cfg, "benchmark_eb_anno"))
    eb = aliquota_ecobonus(cfg, anno)
    iva = float(param(cfg, "iva"))
    rows: list[dict[str, Any]] = []
    for m in righe(cfg, "modelli"):
        l = listino_modello(cfg, m)
        rows.append({"nome": m["nome"], "hurba": True, "listino": l, "street": l - eb * l / (1 + iva)})
    for b in righe(cfg, "benchmark"):
        l = float(b["listino"])
        rows.append({"nome": b["nome"], "hurba": False, "listino": l, "street": l - eb * l / (1 + iva), "note": b.get("note", "")})
    rows.sort(key=lambda r: r["listino"])
    return rows
