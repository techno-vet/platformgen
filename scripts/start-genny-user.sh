#!/bin/bash
# Start Genny FastAPI on :8889, noVNC desktop on :6080, then exec jupyterhub-singleuser
# JupyterHub requires jupyterhub-singleuser as the main process (port 8888)
# Genny UI:  /user/{name}/proxy/8889/
# Desktop:   /user/{name}/proxy/6080/vnc.html  (runs Genny platform tkinter app only)

export GENNY_PLATFORM_DIR=${GENNY_PLATFORM_DIR:-/opt/genny-platform}
export DISPLAY=${DISPLAY:-:1}

# ── Virtual framebuffer (headless X display) ─────────────────────────────────
Xvfb $DISPLAY -screen 0 1280x900x24 -ac &
sleep 1

# ── Kiosk window manager (handles focus/clicks, no menus or terminal access) ─
matchbox-window-manager -use_titlebar no &

# ── Launch Genny tkinter platform (stdout->null suppresses unicode noise) ─────
# Auto-restart loop: if genny crashes, it relaunches automatically
(
  while true; do
    cd $GENNY_PLATFORM_DIR
    python -m genny.app >/dev/null 2>&1
    echo "Genny platform exited, restarting in 2s..."
    sleep 2
  done
) &
echo "Genny platform (tkinter) started on display $DISPLAY"

# ── VNC server (-reconnect keeps running after client disconnect) ────────────
x11vnc -display $DISPLAY -forever -nopw -shared -rfbport 5901 -reconnect -bg -o /tmp/x11vnc.log
echo "x11vnc started on :5901"

# ── noVNC web client (proxies :5901 -> HTTP :6080) ───────────────────────────
NOVNC_DIR=/usr/share/novnc
websockify --web $NOVNC_DIR 6080 localhost:5901 &
echo "noVNC started on :6080"

# ── Genny FastAPI + Next.js UI ───────────────────────────────────────────────
python -m uvicorn genny.web.app:app --host 0.0.0.0 --port 8889 &
echo "Genny UI started on :8889"

# ── Hand off to jupyterhub-singleuser as main process ────────────────────────
exec jupyterhub-singleuser "$@"
