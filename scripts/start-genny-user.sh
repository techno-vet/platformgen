#!/bin/bash
# Start Genny FastAPI on :8889, noVNC desktop on :6080, then exec jupyterhub-singleuser
# JupyterHub requires jupyterhub-singleuser as the main process (port 8888)
# Genny UI:  /user/{name}/proxy/8889/
# Desktop:   /user/{name}/proxy/6080/vnc.html  (runs Genny platform tkinter app only)

export GENNY_PLATFORM_DIR=${GENNY_PLATFORM_DIR:-/opt/genny-platform}
export DISPLAY=${DISPLAY:-:1}

# ── Virtual framebuffer (headless X display) ─────────────────────────────────
# 1920x1080 ensures the 1400x920 genny window fits without clipping (clipped
# windows cause click-coordinate misalignment in noVNC)
Xvfb $DISPLAY -screen 0 1920x1080x24 -ac &
sleep 1

# ── Window manager: openbox with focus-follows-mouse ──────────────────────────
# openbox properly passes all clicks to applications (matchbox uses click-to-
# focus which "swallows" the first click instead of forwarding it to the app)
openbox --sm-disable &
sleep 0.5

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

# ── VNC server — auto-restart loop; no -bg so it stays in the process tree ────
(
  while true; do
    x11vnc -display $DISPLAY -forever -nopw -shared -rfbport 5901 -o /tmp/x11vnc.log 2>&1
    echo "x11vnc exited, restarting in 2s..."
    sleep 2
  done
) &
echo "x11vnc started on :5901"

# ── noVNC web client (proxies :5901 -> HTTP :6080) ───────────────────────────
NOVNC_DIR=/usr/share/novnc
# --heartbeat 30: send WebSocket ping every 30s to prevent proxy idle timeout
websockify --web $NOVNC_DIR --heartbeat 30 6080 localhost:5901 &
echo "noVNC started on :6080"

# ── Genny FastAPI + Next.js UI ───────────────────────────────────────────────
python -m uvicorn genny.web.app:app --host 0.0.0.0 --port 8889 &
echo "Genny UI started on :8889"

# ── Hand off to jupyterhub-singleuser as main process ────────────────────────
exec jupyterhub-singleuser "$@"
