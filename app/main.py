"""HURBA Pricing Simulator — API FastAPI + frontend statico.

Endpoint:
  GET  /api/config              -> defaults.yaml completo (valori + metadati per il pannello)
  GET  /api/presets             -> elenco preset con override
  POST /api/simulate            -> body: {"config": {...}}  -> risultati + alert covenant
  GET  /api/scenarios           -> elenco scenari salvati
  GET  /api/scenarios/{id}      -> scenario completo
  POST /api/scenarios           -> body: {"nome", "note", "config", "id"?} -> salva/aggiorna
  DELETE /api/scenarios/{id}
  GET  /api/health
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.api import scenarios as sc
from app.engine.aggregate import simula
from app.engine.config import apply_overrides, load_defaults
from app.engine.covenants import verifica

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="HURBA Pricing Simulator", version="0.1")


class SimulateBody(BaseModel):
    config: dict[str, Any] | None = None
    override: dict[str, Any] | None = None  # alternativa: percorsi puntati sopra i default


class ScenarioBody(BaseModel):
    nome: str
    config: dict[str, Any]
    note: str = ""
    id: str | None = None


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    return load_defaults()


@app.get("/api/presets")
def get_presets() -> dict[str, Any]:
    return load_defaults()["preset"]


@app.post("/api/simulate")
def post_simulate(body: SimulateBody) -> dict[str, Any]:
    cfg = body.config if body.config else load_defaults()
    if body.override:
        cfg = apply_overrides(cfg, body.override)
    try:
        ris = simula(cfg)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Configurazione non valida: {exc}") from exc
    ris["alert"] = verifica(cfg, ris)
    return ris


@app.get("/api/scenarios")
def list_scenarios() -> list[dict[str, Any]]:
    return sc.elenco()


@app.get("/api/scenarios/{sid}")
def get_scenario(sid: str) -> dict[str, Any]:
    d = sc.leggi(sid)
    if d is None:
        raise HTTPException(status_code=404, detail="Scenario non trovato")
    return d


@app.post("/api/scenarios")
def save_scenario(body: ScenarioBody) -> dict[str, Any]:
    return sc.salva(body.nome, body.config, body.note, body.id)


@app.delete("/api/scenarios/{sid}")
def delete_scenario(sid: str) -> dict[str, bool]:
    if not sc.elimina(sid):
        raise HTTPException(status_code=404, detail="Scenario non trovato")
    return {"ok": True}


# Frontend statico (step 4). Montato per ultimo così /api ha la precedenza.
@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
