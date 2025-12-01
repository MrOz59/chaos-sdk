from fastapi import APIRouter, HTTPException, Body, Query
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from pathlib import Path
import json, re
from typing import Any, Dict, Optional

router = APIRouter(prefix="/api/blueprints", tags=["blueprints"])

BASE_DIR = Path(__file__).parent
ROOT = BASE_DIR.parent.parent  # project root
META_FILE = BASE_DIR / "actions_meta.json"
USER_DIR = BASE_DIR / "user"
USER_DIR.mkdir(parents=True, exist_ok=True)
EDITOR_HTML = ROOT / "web" / "blueprints.html"

@router.get('/actions')
async def actions():
    try:
        if META_FILE.exists():
            with open(META_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        from sdk.blueprints.compiler import ALLOWED_ACTIONS
        return {"actions": sorted(list(ALLOWED_ACTIONS))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/validate')
async def validate(bp: Dict[str, Any] = Body(...)):
    try:
        from sdk.blueprints.compiler import validate_blueprint
        validate_blueprint(bp)
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

@router.post('/compile')
async def compile_bp(bp: Dict[str, Any] = Body(...), cls: Optional[str] = Query(None), standalone: bool = Query(False)):
    try:
        from sdk.blueprints.compiler import compile_blueprint
        result = compile_blueprint(bp, class_name=cls, standalone=standalone)
        
        # Format messages for JSON response
        messages = [
            {
                "severity": msg.severity.value,
                "message": msg.message,
                "location": msg.location,
                "suggestion": msg.suggestion
            }
            for msg in result.messages
        ]
        
        return {
            "ok": result.success,
            "code": result.code,
            "standalone": standalone,
            "messages": messages,
            "warnings": len([m for m in result.messages if m.severity.value == "warning"]),
            "errors": len([m for m in result.messages if m.severity.value == "error"])
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e), "messages": []})

@router.post('/save')
async def save(bp: Dict[str, Any] = Body(...), name: str = Query(...)):
    try:
        safe = re.sub(r'[^a-zA-Z0-9_-]+', '-', name).strip('-') or 'blueprint'
        out = USER_DIR / f"{safe}.json"
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(bp, f, ensure_ascii=False, indent=2)
        return {"ok": True, "path": str(out)}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

@router.get('/load')
async def load(name: str = Query(...)):
    safe = re.sub(r'[^a-zA-Z0-9_-]+', '-', name).strip('-') or 'blueprint'
    src = USER_DIR / f"{safe}.json"
    if not src.exists():
        raise HTTPException(status_code=404, detail='Blueprint não encontrado')
    with open(src, 'r', encoding='utf-8') as f:
        return json.load(f)

# Non-API routes for editor pages
@router.get('/editor', response_class=HTMLResponse)
async def editor():
    if not EDITOR_HTML.exists():
        raise HTTPException(status_code=404, detail='Editor não encontrado')
    return FileResponse(str(EDITOR_HTML))

@router.get('/visual', response_class=HTMLResponse)
async def visual_editor():
    visual_html = ROOT / "web" / "blueprints_visual.html"
    if not visual_html.exists():
        raise HTTPException(status_code=404, detail='Visual editor não encontrado')
    return FileResponse(str(visual_html))
