#!/bin/bash
# Start the Auger host tools daemon (if needed) and the host task tray.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUGER_DIR="${AUGER_DIR:-$HOME/.auger}"
TRAY_SCRIPT="$SCRIPT_DIR/auger_tray.py"
DAEMON_SCRIPT="$SCRIPT_DIR/host_tools_daemon.py"

mkdir -p "$AUGER_DIR"

DISPLAY_VAL="${DISPLAY:-}"
if [ -z "$DISPLAY_VAL" ]; then
    if [ -S /tmp/.X11-unix/X1 ]; then
        DISPLAY_VAL=":1"
    elif [ -S /tmp/.X11-unix/X0 ]; then
        DISPLAY_VAL=":0"
    else
        DISPLAY_VAL=":0"
    fi
fi

if [ -f "$DAEMON_SCRIPT" ] && ! curl -sf --noproxy localhost http://localhost:7437/health >/dev/null 2>&1; then
    OLD_DAEMON=$(lsof -ti tcp:7437 2>/dev/null | head -1 || true)
    if [ -n "$OLD_DAEMON" ]; then
        kill "$OLD_DAEMON" 2>/dev/null || true
        sleep 1
    fi

    echo "🌐  Starting Host Tools daemon on port 7437..."
    nohup python3 "$DAEMON_SCRIPT" >> "$AUGER_DIR/daemon.log" 2>&1 &
    DAEMON_PID=$!
    disown "$DAEMON_PID"

    for _i in $(seq 1 20); do
        if curl -sf --noproxy localhost http://localhost:7437/health >/dev/null 2>&1; then
            echo "$DAEMON_PID" > "$AUGER_DIR/daemon.pid"
            echo "✅  Daemon ready (PID $DAEMON_PID)"
            break
        fi
        sleep 0.5
    done
fi

if [ ! -f "$TRAY_SCRIPT" ]; then
    echo "ℹ️  auger_tray.py not found — skipping system tray icon"
    exit 0
fi

if ! python3 -c "import pystray" 2>/dev/null; then
    echo "📦  Installing pystray for system tray support..."
    pip3 install --user --quiet pystray pillow 2>/dev/null \
        && echo "✅  pystray installed" \
        || echo "⚠️  pystray install failed — tray icon disabled"
fi

if ! python3 -c "import pystray" 2>/dev/null; then
    echo "⚠️  pystray not available — skipping system tray icon"
    exit 0
fi

python3 -c "
import os, signal, subprocess, time
self_pid = os.getpid()
r = subprocess.run(['pgrep', '-f', 'auger_tray.py'], capture_output=True, text=True)
pids = [int(p) for p in r.stdout.split() if p.strip() and int(p) != self_pid]
for pid in pids:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
if pids:
    time.sleep(1)
"

echo "🔔  Starting system tray applet..."
DISPLAY="$DISPLAY_VAL" XAUTHORITY="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}" \
gnome-extensions enable ubuntu-appindicators@ubuntu.com 2>/dev/null || true

DISPLAY="$DISPLAY_VAL" XAUTHORITY="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}" \
setsid env -u GTK_EXE_PREFIX -u GTK_PATH -u GTK_DATA_PREFIX -u GTK_IM_MODULE_FILE \
    -u GIO_MODULE_DIR -u GIO_EXTRA_MODULES -u GI_TYPELIB_PATH \
    -u GDK_PIXBUF_MODULEDIR -u GDK_PIXBUF_MODULE_FILE -u GTK_MODULES \
    -u LD_LIBRARY_PATH -u PYTHONHOME \
    python3 "$TRAY_SCRIPT" >> "$AUGER_DIR/tray.log" 2>&1 &
TRAY_PID=$!
disown "$TRAY_PID"

sleep 2
if python3 -c "import subprocess; r=subprocess.run(['pgrep','-f','auger_tray.py'],capture_output=True); exit(0 if r.stdout.strip() else 1)" 2>/dev/null; then
    echo "✅  Tray applet running (PID $TRAY_PID)"
else
    echo "⚠️  Tray applet failed to start — check $AUGER_DIR/tray.log"
    tail -5 "$AUGER_DIR/tray.log" 2>/dev/null | sed 's/^/   /'
fi
