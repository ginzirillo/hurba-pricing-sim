"""Verifica dei tre covenant e produzione degli alert."""
from __future__ import annotations

from typing import Any


def verifica(cfg: dict[str, Any], risultati: dict[str, Any]) -> list[dict[str, Any]]:
    cov = cfg["covenant"]
    max_t20 = float(cov["tier20_max_share"]["value"])
    min_contr = float(cov["contribuzione_min"]["value"])
    max_fin = float(cov["costi_finanziari_max"]["value"])
    alerts: list[dict[str, Any]] = []

    for anno, r in risultati["per_anno"].items():
        # 1) tier 20% sul fatturato dealer
        ric_dealer = r["per_canale"]["dealer"]["ricavi"]
        ric_t20 = r["per_tier"].get("t20", {}).get("ricavi", 0.0)
        share = ric_t20 / ric_dealer if ric_dealer else 0.0
        alerts.append({
            "anno": anno, "covenant": "tier20",
            "label": "Tier 20% ≤ quota massima del fatturato dealer",
            "valore": share, "soglia": max_t20, "ok": share <= max_t20 + 1e-9,
        })
        # 3) costi finanziari sul margine lordo
        ratio = r["costi_finanziari"] / r["margine_lordo"] if r["margine_lordo"] else 0.0
        alerts.append({
            "anno": anno, "covenant": "costi_finanziari",
            "label": "Costi finanziari (cessione + factoring) ≤ quota del margine lordo",
            "valore": ratio, "soglia": max_fin, "ok": ratio <= max_fin + 1e-9,
        })

    # 2) contribuzione minima su ogni combinazione
    violazioni = [
        c for c in risultati["combinazioni"] if c["contribuzione_pct"] < min_contr - 1e-9
    ]
    peggiore = min(risultati["combinazioni"], key=lambda c: c["contribuzione_pct"], default=None)
    alerts.append({
        "anno": "tutti", "covenant": "contribuzione",
        "label": "Contribuzione ≥ soglia su ogni combinazione modello × canale × tier",
        "valore": peggiore["contribuzione_pct"] if peggiore else 0.0,
        "soglia": min_contr, "ok": not violazioni,
        "dettaglio": [
            {"anno": c["anno"], "modello": c["nome_modello"], "canale": c["canale"],
             "tier": c["tier"], "promo": c["promo"], "contribuzione_pct": c["contribuzione_pct"]}
            for c in violazioni
        ],
    })
    return alerts
