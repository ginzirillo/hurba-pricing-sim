"""Caricamento di defaults.yaml e applicazione di preset/sovrascritture.

Le sovrascritture usano percorsi puntati, es.
  parametri.iva.value            -> chiave annidata
  tabelle.ecobonus.righe[0].flat -> elemento di lista
"""
from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import yaml

DEFAULTS_PATH = Path(__file__).parent / "defaults.yaml"
_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def load_defaults() -> dict[str, Any]:
    """Legge defaults.yaml e restituisce un dizionario nuovo (mai condiviso)."""
    with DEFAULTS_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _tokens(path: str) -> list[str | int]:
    out: list[str | int] = []
    for key, idx in _TOKEN.findall(path):
        out.append(int(idx) if idx != "" else key)
    return out


def set_path(cfg: dict[str, Any], path: str, value: Any) -> None:
    """Imposta `value` al percorso puntato `path` dentro `cfg` (in place)."""
    node: Any = cfg
    toks = _tokens(path)
    for tok in toks[:-1]:
        node = node[tok]
    node[toks[-1]] = value


def get_path(cfg: dict[str, Any], path: str) -> Any:
    node: Any = cfg
    for tok in _tokens(path):
        node = node[tok]
    return node


def apply_overrides(cfg: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Restituisce una copia di cfg con le sovrascritture applicate."""
    out = copy.deepcopy(cfg)
    for path, value in (overrides or {}).items():
        set_path(out, path, value)
    return out


def apply_preset(cfg: dict[str, Any], preset_id: str) -> dict[str, Any]:
    preset = cfg["preset"][preset_id]
    return apply_overrides(cfg, preset.get("override", {}))


def param(cfg: dict[str, Any], key: str) -> Any:
    """Valore di un parametro scalare."""
    return cfg["parametri"][key]["value"]


def righe(cfg: dict[str, Any], tabella: str) -> list[dict[str, Any]]:
    return cfg["tabelle"][tabella]["righe"]
