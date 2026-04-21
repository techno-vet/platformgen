"""
PlatformGen Genny Web Server
FastAPI app: serves Next.js static build + WebSocket chat + REST API
Runs on port 8888 inside each user pod.
"""
import os
import json
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from genny.agents.genny_runner import GennyRunner
from genny.web.widgets_api import router as widgets_router

app = FastAPI(title="Genny", docs_url=None, redoc_url=None)

# ── REST API ─────────────────────────────────────────────────────────────────
app.include_router(widgets_router, prefix="/api")

@app.get("/api/health")
async def health():
    return {"status": "ok", "tier": os.environ.get("GENNY_TIER", "free")}

# ── WebSocket Chat ────────────────────────────────────────────────────────────
_runner: GennyRunner | None = None

def get_runner() -> GennyRunner:
    global _runner
    if _runner is None:
        model = os.environ.get("GENNY_MODEL", "qwen2.5-coder:14b")
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        _runner = GennyRunner(model_name=model, ollama_base=ollama_url)
    return _runner

@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    await ws.accept()
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                prompt = msg.get("prompt", "").strip()
            except Exception:
                prompt = data.strip()

            if not prompt:
                continue

            done_event = asyncio.Event()
            error_holder = []

            def on_step(text: str):
                asyncio.run_coroutine_threadsafe(
                    ws.send_text(json.dumps({"type": "step", "text": text})),
                    loop,
                )

            def on_done(text: str):
                asyncio.run_coroutine_threadsafe(
                    ws.send_text(json.dumps({"type": "done", "text": text})),
                    loop,
                )
                done_event.set()

            def on_error(text: str):
                error_holder.append(text)
                asyncio.run_coroutine_threadsafe(
                    ws.send_text(json.dumps({"type": "error", "text": text})),
                    loop,
                )
                done_event.set()

            get_runner().run(prompt, on_step=on_step, on_done=on_done, on_error=on_error)
            await done_event.wait()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_text(json.dumps({"type": "error", "text": str(e)}))
        except Exception:
            pass

# ── Static frontend (Next.js build) ─────────────────────────────────────────
_STATIC_DIR = Path(__file__).parent.parent.parent / "web" / "out"

if _STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
else:
    @app.get("/")
    async def index_fallback():
        return JSONResponse({"message": "Genny web UI not built yet. Run: cd web && npm run build"}, status_code=503)

if __name__ == "__main__":
    uvicorn.run("genny.web.app:app", host="0.0.0.0", port=8888, reload=False)
