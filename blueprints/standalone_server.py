#!/usr/bin/env python3
"""
Servidor standalone do Blueprint Editor
Completamente independente do sistema principal
"""
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import apenas o router de blueprints
from sdk.blueprints.api import router as blueprints_router

app = FastAPI(
    title="Blueprint Editor",
    description="Editor visual de plugins - Sistema independente",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir apenas o router de blueprints
app.include_router(blueprints_router)

# Servir arquivos estáticos do web (para blueprints.html e JS)
WEB_DIR = Path(__file__).parent.parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

# Rota raiz redireciona para o editor
from fastapi.responses import RedirectResponse

@app.get("/")
async def root():
    return RedirectResponse(url="/api/blueprints/editor")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "blueprint-editor"}


if __name__ == "__main__":
    print("🧩 Blueprint Editor - Servidor Standalone")
    print("=" * 50)
    print("Editor: http://localhost:3050/api/blueprints/editor")
    print("API: http://localhost:3050/api/blueprints/actions")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=3050, log_level="info")
