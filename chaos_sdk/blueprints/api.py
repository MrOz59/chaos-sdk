from fastapi import APIRouter, HTTPException, Body, Query
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from pathlib import Path
import json, re
from typing import Any, Dict, List, Optional
import time

router = APIRouter(prefix="/api/blueprints", tags=["blueprints"])

BASE_DIR = Path(__file__).parent
ROOT = BASE_DIR.parent.parent  # chaos_sdk root
META_FILE = BASE_DIR / "actions_meta.json"
USER_DIR = BASE_DIR / "user"
USER_DIR.mkdir(parents=True, exist_ok=True)
EDITOR_HTML = ROOT / "web" / "blueprints_visual.html"

# Cache for actions metadata
_actions_cache = None
_actions_cache_time = 0

@router.get('/actions')
async def actions():
    """Get available actions metadata with caching."""
    global _actions_cache, _actions_cache_time
    
    try:
        # Check cache (5 minute TTL)
        if _actions_cache and time.time() - _actions_cache_time < 300:
            return _actions_cache
        
        if META_FILE.exists():
            with open(META_FILE, 'r', encoding='utf-8') as f:
                _actions_cache = json.load(f)
                _actions_cache_time = time.time()
                return _actions_cache
        
        # Fallback to allowed actions list
        from chaos_sdk.blueprints.compiler_v2 import ALLOWED_ACTIONS
        return {"actions": sorted(list(ALLOWED_ACTIONS))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/actions/categories')
async def actions_by_category():
    """Get actions grouped by category."""
    try:
        data = await actions()
        categories = {}
        for action in data.get('actions', []):
            cat = action.get('category', 'Other')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(action)
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/validate')
async def validate(bp: Dict[str, Any] = Body(...)):
    """Validate blueprint structure."""
    try:
        from chaos_sdk.blueprints.compiler import validate_blueprint
        validate_blueprint(bp)
        return {"ok": True, "message": "Blueprint is valid"}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

@router.post('/validate/visual')
async def validate_visual(bp: Dict[str, Any] = Body(...)):
    """Validate visual blueprint with detailed feedback."""
    try:
        errors = []
        warnings = []
        
        # Check required fields
        for field in ['name', 'version', 'author', 'description', 'commands']:
            if field not in bp:
                errors.append(f"Missing required field: {field}")
        
        commands = bp.get('commands', {})
        if not isinstance(commands, dict) or not commands:
            errors.append("'commands' must be a non-empty object")
        
        # Validate each command
        for cmd_name, cmd_data in commands.items():
            if isinstance(cmd_data, dict):
                # Visual format
                nodes = cmd_data.get('nodes', [])
                connections = cmd_data.get('connections', [])
                
                # Check for start event
                has_start = any(n.get('type') == 'event_start' for n in nodes)
                if not has_start:
                    warnings.append(f"Command '{cmd_name}' has no start event node")
                
                # Check for orphan nodes (no connections)
                connected_nodes = set()
                for conn in connections:
                    connected_nodes.add(conn.get('fromNode'))
                    connected_nodes.add(conn.get('toNode'))
                
                for node in nodes:
                    if node['id'] not in connected_nodes and node.get('type') != 'event_start':
                        if not node.get('isPure', False):  # Pure nodes can be unconnected
                            warnings.append(f"Command '{cmd_name}': Node '{node.get('label', node['id'])}' is not connected")
        
        return {
            "ok": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "valid": len(errors) == 0
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

@router.post('/compile')
async def compile_bp(
    bp: Dict[str, Any] = Body(...), 
    cls: Optional[str] = Query(None), 
    standalone: bool = Query(False),
    use_v2: bool = Query(True)  # Use v2 compiler by default
):
    """Compile blueprint to Python plugin."""
    try:
        if use_v2:
            from chaos_sdk.blueprints.compiler_v2 import compile_blueprint_v2
            result = compile_blueprint_v2(bp, class_name=cls, standalone=standalone)
        else:
            from chaos_sdk.blueprints.compiler import compile_blueprint
            result = compile_blueprint(bp, class_name=cls, standalone=standalone)
        
        # Format messages for JSON response
        messages = [
            {
                "severity": msg.severity.value,
                "message": msg.message,
                "location": getattr(msg, 'location', ''),
                "suggestion": getattr(msg, 'suggestion', '')
            }
            for msg in result.messages
        ]
        
        return {
            "ok": result.success,
            "code": result.code,
            "standalone": standalone,
            "messages": messages,
            "warnings": len([m for m in result.messages if m.severity.value == "warning"]),
            "errors": len([m for m in result.messages if m.severity.value == "error"]),
            "stats": getattr(result, 'stats', {})
        }
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={
            "ok": False, 
            "error": str(e), 
            "messages": [],
            "traceback": traceback.format_exc()
        })

@router.post('/save')
async def save(bp: Dict[str, Any] = Body(...), name: str = Query(...)):
    """Save blueprint to user directory."""
    try:
        safe = re.sub(r'[^a-zA-Z0-9_-]+', '-', name).strip('-') or 'blueprint'
        out = USER_DIR / f"{safe}.json"
        
        # Add save metadata
        bp['_saved_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        bp['_saved_name'] = safe
        
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(bp, f, ensure_ascii=False, indent=2)
        
        return {"ok": True, "path": str(out), "name": safe}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

@router.get('/load')
async def load(name: str = Query(...)):
    """Load blueprint from user directory."""
    safe = re.sub(r'[^a-zA-Z0-9_-]+', '-', name).strip('-') or 'blueprint'
    src = USER_DIR / f"{safe}.json"
    if not src.exists():
        raise HTTPException(status_code=404, detail='Blueprint não encontrado')
    with open(src, 'r', encoding='utf-8') as f:
        return json.load(f)

@router.get('/list')
async def list_blueprints():
    """List all saved blueprints."""
    try:
        blueprints = []
        for f in USER_DIR.glob('*.json'):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                    blueprints.append({
                        "filename": f.stem,
                        "name": data.get('name', f.stem),
                        "version": data.get('version', '1.0.0'),
                        "author": data.get('author', 'Unknown'),
                        "description": data.get('description', ''),
                        "commands": list(data.get('commands', {}).keys()),
                        "saved_at": data.get('_saved_at', ''),
                    })
            except:
                pass
        
        return {"blueprints": blueprints}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete('/delete')
async def delete_blueprint(name: str = Query(...)):
    """Delete a saved blueprint."""
    safe = re.sub(r'[^a-zA-Z0-9_-]+', '-', name).strip('-') or 'blueprint'
    src = USER_DIR / f"{safe}.json"
    if not src.exists():
        raise HTTPException(status_code=404, detail='Blueprint não encontrado')
    try:
        src.unlink()
        return {"ok": True, "deleted": safe}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

@router.post('/duplicate')
async def duplicate_blueprint(name: str = Query(...), new_name: str = Query(...)):
    """Duplicate a blueprint with new name."""
    safe = re.sub(r'[^a-zA-Z0-9_-]+', '-', name).strip('-') or 'blueprint'
    new_safe = re.sub(r'[^a-zA-Z0-9_-]+', '-', new_name).strip('-') or 'blueprint-copy'
    
    src = USER_DIR / f"{safe}.json"
    if not src.exists():
        raise HTTPException(status_code=404, detail='Blueprint não encontrado')
    
    dst = USER_DIR / f"{new_safe}.json"
    if dst.exists():
        raise HTTPException(status_code=400, detail='Nome já existe')
    
    try:
        with open(src, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data['name'] = new_name
        data['_saved_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        data['_saved_name'] = new_safe
        
        with open(dst, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return {"ok": True, "new_name": new_safe}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

@router.post('/export/plugin')
async def export_plugin(bp: Dict[str, Any] = Body(...), cls: Optional[str] = Query(None)):
    """Compile and download as Python plugin file."""
    try:
        from chaos_sdk.blueprints.compiler_v2 import compile_blueprint_v2
        result = compile_blueprint_v2(bp, class_name=cls, standalone=True)
        
        if not result.success:
            return JSONResponse(status_code=400, content={
                "ok": False,
                "error": "Compilation failed",
                "messages": [{"severity": m.severity.value, "message": m.message} for m in result.messages]
            })
        
        # Return code as downloadable file
        from fastapi.responses import Response
        filename = (bp.get('name', 'blueprint').replace(' ', '_') or 'blueprint') + '.py'
        return Response(
            content=result.code,
            media_type="text/x-python",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

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
