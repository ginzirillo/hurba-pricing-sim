"""Salvataggio scenari su file JSON (nessun database).

Uno scenario = { "id", "nome", "note", "creato", "aggiornato", "config" }.
La cartella è data/scenarios/ (volume Docker persistente).
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCENARI_DIR = Path(__file__).resolve().parents[2] / "data" / "scenarios"
_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(nome: str) -> str:
    s = _SLUG.sub("-", nome.lower()).strip("-")
    return s or "scenario"


def _path(sid: str) -> Path:
    return SCENARI_DIR / f"{sid}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def elenco() -> list[dict[str, Any]]:
    out = []
    for p in sorted(SCENARI_DIR.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append({k: d.get(k) for k in ("id", "nome", "note", "creato", "aggiornato")})
        except json.JSONDecodeError:
            continue
    return sorted(out, key=lambda d: d.get("aggiornato") or "", reverse=True)


def leggi(sid: str) -> dict[str, Any] | None:
    p = _path(sid)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def salva(nome: str, config: dict[str, Any], note: str = "", sid: str | None = None) -> dict[str, Any]:
    SCENARI_DIR.mkdir(parents=True, exist_ok=True)
    if sid is None:
        sid = f"{_slug(nome)}-{int(time.time())}"
        creato = _now()
    else:
        prev = leggi(sid)
        creato = prev["creato"] if prev else _now()
    d = {"id": sid, "nome": nome, "note": note, "creato": creato, "aggiornato": _now(), "config": config}
    _path(sid).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def elimina(sid: str) -> bool:
    p = _path(sid)
    if p.exists():
        p.unlink()
        return True
    return False
