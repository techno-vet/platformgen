#!/bin/bash
# Start Genny FastAPI on :8889, noVNC desktop on :6080, then exec jupyterhub-singleuser
# JupyterHub requires jupyterhub-singleuser as the main process (port 8888)
# Genny UI:  /user/{name}/proxy/8889/
# Desktop:   /user/{name}/proxy/6080/vnc.html

export GENNY_PLATFORM_DIR=${GENNY_PLATFORM_DIR:-/opt/genny-platform}
export DISPLAY=${DISPLAY:-:1}

# ── Virtual framebuffer (headless X display) ─────────────────────────────────
Xvfb $DISPLAY -screen 0 1280x900x24 -ac &
sleep 1

# ── Lightweight window manager ───────────────────────────────────────────────
openbox --display $DISPLAY &

# ── VNC server (listens on :5901, no password) ───────────────────────────────
x11vnc -display $DISPLAY -forever -nopw -shared -rfbport 5901 -bg -o /tmp/x11vnc.log
echo "x11vnc started on :5901"

# ── noVNC web client (proxies :5901 → HTTP :6080) ────────────────────────────
# On Debian/Ubuntu: apt novnc installs web files to /usr/share/novnc
NOVNC_DIR=/usr/share/novnc
websockify --web $NOVNC_DIR 6080 localhost:5901 &
echo "noVNC started on :6080 (web: $NOVNC_DIR)"

# ── Genny FastAPI + Next.js UI ───────────────────────────────────────────────
cd $GENNY_PLATFORM_DIR
python -m uvicorn genny.web.app:app --host 0.0.0.0 --port 8889 &
echo "Genny UI started on :8889"

# ── Hand off to jupyterhub-singleuser as main process ────────────────────────
exec jupyterhub-singleuser "$@"
