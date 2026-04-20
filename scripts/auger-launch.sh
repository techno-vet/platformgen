#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Auger SRE Platform — One-Shot Launcher
# Pull the latest image from Artifactory and start Auger.
# The first-run wizard will guide you through Copilot token setup.
#
# Usage:
#   bash auger-launch.sh               # Docker mode (default)
#   bash auger-launch.sh --venv        # Native venv mode (no Docker required)
#   bash auger-launch.sh --venv --install-only   # Install deps only, don't start
# ─────────────────────────────────────────────────────────────────────────────
set -e
set -o pipefail

IMAGE="artifactory.helix.gsa.gov/gs-assist-docker-repo/auger-platform:20260311"
CONTAINER="auger-platform"
AUGER_DIR="$HOME/.auger"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROGRESS_LOG="$AUGER_DIR/startup-progress.log"

start_progress_dialog() {
    mkdir -p "$AUGER_DIR"
    : > "$PROGRESS_LOG"
    if [ "${AUGER_WIZARD:-0}" = "1" ] || [ "${AUGER_SUPPRESS_STARTUP_DIALOG:-0}" = "1" ]; then
        return
    fi
    if [ -n "${DISPLAY:-}" ] && [ -f "$SCRIPT_DIR/startup_progress.py" ]; then
        nohup python3 "$SCRIPT_DIR/startup_progress.py" \
            --log-file "$PROGRESS_LOG" \
            --title "Auger Startup" >/dev/null 2>&1 &
    fi
}

progress_msg() {
    local message="$1"
    echo "$message"
    printf '%s\n' "$message" >> "$PROGRESS_LOG"
}

progress_done() {
    printf 'STATE:done\n' >> "$PROGRESS_LOG"
}

progress_error() {
    local message="$1"
    echo "$message"
    printf '%s\nSTATE:error\n' "$message" >> "$PROGRESS_LOG"
}

trap 'rc=$?; if [ "$rc" -ne 0 ] && [ -f "$PROGRESS_LOG" ]; then progress_error "Auger startup failed."; fi' EXIT

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║          Auger SRE Platform — Launcher               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Mode detection ────────────────────────────────────────────────────────────
VENV_MODE=0
INSTALL_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --venv)          VENV_MODE=1 ;;
        --install-only)  INSTALL_ONLY=1 ;;
    esac
done

# Auto-detect venv mode if Docker is not available
if [ "$VENV_MODE" -eq 0 ] && ! command -v docker &>/dev/null; then
    echo "ℹ️   Docker not found — switching to native venv mode automatically."
    VENV_MODE=1
fi

# ─────────────────────────────────────────────────────────────────────────────
# VENV MODE  (no Docker required — works on Windows, macOS, Linux)
# ─────────────────────────────────────────────────────────────────────────────
if [ "$VENV_MODE" -eq 1 ]; then
    echo "🐍  Auger native venv mode"
    echo ""

    # Require Python 3.8+
    if ! command -v python3 &>/dev/null; then
        echo "❌  python3 not found. Please install Python 3.8 or newer."
        exit 1
    fi

    VENV_DIR="$AUGER_DIR/venv"
    mkdir -p "$AUGER_DIR"

    # Create venv if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        echo "📦  Creating Python virtual environment at $VENV_DIR ..."
        python3 -m venv "$VENV_DIR"
    fi

    # Activate venv
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    # Detect proxy (same logic as Docker mode)
    PROXY_URL=""
    for port in 9000 10800 3128 8080; do
        if ss -tlnp 2>/dev/null | grep -q ":${port} " || \
           netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
            PROXY_URL="http://127.0.0.1:${port}"
            echo "🔒  Proxy detected on port ${port}"
            break
        fi
    done

    PIP_PROXY_ARGS=""
    if [ -n "$PROXY_URL" ]; then
        PIP_PROXY_ARGS="--proxy $PROXY_URL"
        export http_proxy="$PROXY_URL"
        export https_proxy="$PROXY_URL"
        export HTTP_PROXY="$PROXY_URL"
        export HTTPS_PROXY="$PROXY_URL"
    fi

    # Install/update Auger if not already installed or if --install-only
    if [ "$INSTALL_ONLY" -eq 1 ] || ! python3 -c "import auger" 2>/dev/null; then
        echo "📦  Installing Auger and dependencies..."
        pip install --quiet $PIP_PROXY_ARGS --upgrade pip
        pip install --quiet $PIP_PROXY_ARGS -e "$REPO_DIR"
        echo "✅  Auger installed in venv"
    fi

    if [ "$INSTALL_ONLY" -eq 1 ]; then
        echo ""
        echo "✅  Venv install complete: $VENV_DIR"
        echo "   To start Auger:  bash $SCRIPT_DIR/auger-launch.sh --venv"
        exit 0
    fi

    # Load .env tokens into environment
    if [ -f "$AUGER_DIR/.env" ]; then
        set -a
        # shellcheck disable=SC1090
        source "$AUGER_DIR/.env" 2>/dev/null || true
        set +a
    fi

    # Auto-init if config.yaml doesn't exist
    CONFIG_FILE="$AUGER_DIR/config.yaml"
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "🔧  First run — initializing Auger config..."
        # Try to find a GitHub token from environment
        _INIT_TOKEN="${GH_TOKEN:-${GHE_TOKEN:-${GITHUB_TOKEN:-}}}"
        if [ -z "$_INIT_TOKEN" ]; then
            read -rp "   GitHub Copilot token (github.com): " _INIT_TOKEN
        else
            echo "   Using token from ~/.auger/.env"
        fi
        python3 -m auger init --token "$_INIT_TOKEN" || true
    fi

    # Start host tools daemon if not already running
    if ! curl -sf http://localhost:7437/health >/dev/null 2>&1; then
        echo "🔧  Starting host tools daemon..."
        nohup python3 "$SCRIPT_DIR/host_tools_daemon.py" \
            > "$AUGER_DIR/daemon.log" 2>&1 &
        DAEMON_PID=$!
        echo "$DAEMON_PID" > "$AUGER_DIR/daemon.pid"
        sleep 1
        if curl -sf http://localhost:7437/health >/dev/null 2>&1; then
            echo "✅  Host tools daemon running (PID $DAEMON_PID)"
        else
            echo "⚠️   Daemon may still be starting — continuing anyway"
        fi
    else
        echo "✅  Host tools daemon already running"
    fi

    # Export venv mode so widgets can detect it
    export AUGER_MODE=venv

    echo "🚀  Starting Auger (venv mode)..."
    echo ""
    echo "   Auger window will appear on your display."
    echo "   To stop: Ctrl+C or close the window."
    echo ""

    exec python3 -m auger start
fi

# ─────────────────────────────────────────────────────────────────────────────
# DOCKER MODE  (original flow)
# ─────────────────────────────────────────────────────────────────────────────

# ── 1. Docker check ───────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "❌  Docker not found. Please install Docker Desktop or Docker Engine first."
    exit 1
fi

if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    DISPLAY_VAL="${DISPLAY:-:0}"
    echo "✅  Auger container already running — opening the existing platform window..."
    if docker exec -d -e DISPLAY="$DISPLAY_VAL" "$CONTAINER" auger start >/dev/null 2>&1; then
        exit 0
    fi
    echo "⚠️   Could not activate the existing Auger UI — continuing with full startup path."
fi

start_progress_dialog
progress_msg "Starting Auger launcher..."

# ── 2. Artifactory login ──────────────────────────────────────────────────────
# Prefer non-interactive login via saved credentials from environment or
# ~/.auger/.env. Only fall back to an interactive prompt if no saved credential
# works. This keeps install_wizard and shell setup flows silent when .env is
# already correct.
_art_registry="artifactory.helix.gsa.gov"
BASE_IMAGE="$IMAGE"
read_env_key() {
    local file="$1" key="$2"
    [ -f "$file" ] || return 0
    grep -E "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d "'\""
}

art_image_access_ok() {
    local image="$1"
    [ -n "$image" ] || return 1
    docker manifest inspect "$image" >/dev/null 2>&1
}

_art_last_error=""
art_login_with_key() {
    local user="$1" key="$2" image="$3"
    [ -n "$user" ] && [ -n "$key" ] || {
        _art_last_error="missing"
        return 1
    }
    if ! printf '%s' "$key" | docker login "$_art_registry" -u "$user" --password-stdin >/dev/null 2>&1; then
        _art_last_error="login"
        return 1
    fi
    if ! art_image_access_ok "$image"; then
        _art_last_error="access"
        return 1
    fi
    _art_last_error=""
    return 0
}

_art_user="${ARTIFACTORY_USERNAME:-${ARTIFACTORY_USER:-}}"
_art_identity="${ARTIFACTORY_IDENTITY_TOKEN:-}"
_art_api="${ARTIFACTORY_API_KEY:-}"
if [ -z "$_art_user" ]; then
    _art_user=$(read_env_key "$AUGER_DIR/.env" "ARTIFACTORY_USERNAME")
fi
if [ -z "$_art_user" ]; then
    _art_user=$(read_env_key "$AUGER_DIR/.env" "ARTIFACTORY_USER")
fi
[ -z "$_art_identity" ] && _art_identity=$(read_env_key "$AUGER_DIR/.env" "ARTIFACTORY_IDENTITY_TOKEN")
[ -z "$_art_api" ] && _art_api=$(read_env_key "$AUGER_DIR/.env" "ARTIFACTORY_API_KEY")

_art_authenticated=false
if art_login_with_key "$_art_user" "$_art_identity" "$BASE_IMAGE"; then
    echo "🔐  Logged in to Artifactory with saved Identity Token."
    _art_authenticated=true
else
    if [ -n "$_art_identity" ] && [ "$_art_last_error" = "access" ]; then
        echo "⚠️   Saved Identity Token logged in but cannot read ${BASE_IMAGE}."
        echo "    Retrying with saved API Key if available..."
    fi
fi

if [ "$_art_authenticated" = false ] && art_login_with_key "$_art_user" "$_art_api" "$BASE_IMAGE"; then
    echo "🔐  Logged in to Artifactory with saved API Key."
    _art_authenticated=true
fi

if [ "$_art_authenticated" = false ]; then
    progress_msg "Logging in to Artifactory..."
    docker login "$_art_registry"
    if ! art_image_access_ok "$BASE_IMAGE"; then
        progress_error "Artifactory login succeeded, but this account still cannot read ${BASE_IMAGE}."
        echo "    Prefer ARTIFACTORY_API_KEY in ~/.auger/.env."
        echo "    If you only have an Identity Token, verify it has Docker pull access."
        exit 1
    fi
fi

# ── 3. Pull base image + build personalized image ────────────────────────────
# Sanitize username for use as a Docker image tag:
# Domain usernames like bobbygblair@gtd.gsa.gov are invalid in tags.
# Strip domain suffix and replace any remaining non-alphanumeric chars with -.
_SAFE_USER="$(echo "${USER}" | sed 's/@.*//' | tr -cs 'a-zA-Z0-9' '-' | sed 's/-$//' | tr 'A-Z' 'a-z')"
PERSONALIZED_IMAGE="auger-platform-${_SAFE_USER}:latest"
FORCE_REBUILD_PERSONALIZED="${AUGER_FORCE_REBUILD_PERSONALIZED:-0}"

if [ "$FORCE_REBUILD_PERSONALIZED" = "1" ]; then
    progress_msg "Forcing personalized image rebuild to pick up latest local code..."
elif docker image inspect "$PERSONALIZED_IMAGE" >/dev/null 2>&1; then
    progress_msg "Personalized image already present: ${PERSONALIZED_IMAGE}"
fi

if [ "$FORCE_REBUILD_PERSONALIZED" = "1" ] || ! docker image inspect "$PERSONALIZED_IMAGE" >/dev/null 2>&1; then
    progress_msg "Pulling Auger base image..."
    docker pull "$BASE_IMAGE" 2>&1 | tee -a "$PROGRESS_LOG"

    progress_msg "Building personalized image for ${USER} (this can take a few minutes)..."
    # Force legacy builder (DOCKER_BUILDKIT=0) — docker buildx hangs on layer export
    # for large images on this platform. Legacy builder completes reliably.
    # NOTE: no --network=host here — Dockerfile.user only does useradd+mkdir+chown,
    # needs no network. --network=host caused useradd to hang querying domain AD/LDAP
    # with large domain UIDs on domain-joined WorkSpaces.
    if DOCKER_BUILDKIT=0 docker build --no-cache \
        -f "$REPO_DIR/Dockerfile.user" \
        --build-arg "BASE_IMAGE=${BASE_IMAGE}" \
        --build-arg "HOST_USER=${_SAFE_USER}" \
        --build-arg "HOST_UID=$(id -u)" \
        --build-arg "HOST_GID=$(id -g)" \
        -t "$PERSONALIZED_IMAGE" \
        "$REPO_DIR" 2>&1 | tee -a "$PROGRESS_LOG"; then
        progress_msg "Personalized image ready: ${PERSONALIZED_IMAGE}"
    else
        progress_error "Personalized image build failed."
        exit 1
    fi
fi

# ── 4. Stop any existing container ───────────────────────────────────────────
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    progress_msg "Stopping existing Auger container..."
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
fi

# ── 5. Ensure ~/.auger exists ─────────────────────────────────────────────────
mkdir -p "$AUGER_DIR"
touch "$AUGER_DIR/.env"

# ── 6. Detect display ────────────────────────────────────────────────────────
DISPLAY_VAL="${DISPLAY:-:0}"

# ── 7. Detect Zscaler proxy ──────────────────────────────────────────────────
PROXY_ARGS=""
for port in 9000 10800 3128 8080; do
    if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
        PROXY_URL="http://127.0.0.1:${port}"
        PROXY_ARGS="-e http_proxy=$PROXY_URL -e https_proxy=$PROXY_URL -e HTTP_PROXY=$PROXY_URL -e HTTPS_PROXY=$PROXY_URL"
        echo "🔒  Proxy detected on port ${port}"
        break
    fi
done

# ── 8. Load token if already configured ──────────────────────────────────────
GH_TOKEN_ARG=""
if [ -f "$AUGER_DIR/.env" ]; then
    _tok=$(grep -E '^(GHE_TOKEN|GH_TOKEN)=' "$AUGER_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d "'\"")
    [ -n "$_tok" ] && GH_TOKEN_ARG="-e GH_TOKEN=$_tok"
fi

# ── 9. Allow X11 connections ─────────────────────────────────────────────────
xhost +local: >/dev/null 2>&1 || true

# ── Ensure .env readable ──────────────────────────────────────────────────────
# Container runs as the host user (same uid) — .env is already readable.
# chmod is a no-op but kept as a safety net for first-run edge cases.
chmod 644 "$AUGER_DIR/.env" 2>/dev/null || true

# ── 10. Start Host Tools Daemon (BEFORE container) ───────────────────────────
# Must be running before the UI starts so /schedule_restart, browser launch,
# and Jira MFA auth are all available the moment the platform opens.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_SCRIPT="$SCRIPT_DIR/host_tools_daemon.py"
if [ -f "$DAEMON_SCRIPT" ]; then
    OLD_DAEMON=$(lsof -ti tcp:7437 2>/dev/null | head -1)
    [ -n "$OLD_DAEMON" ] && kill "$OLD_DAEMON" 2>/dev/null && sleep 1
    progress_msg "Starting host tools daemon..."
    nohup python3 "$DAEMON_SCRIPT" >> "$AUGER_DIR/daemon.log" 2>&1 &
    DAEMON_PID=$!
    disown $DAEMON_PID
    for i in $(seq 1 20); do
        if curl -sf --noproxy localhost http://localhost:7437/health >/dev/null 2>&1; then
            echo "✅  Daemon ready (PID $DAEMON_PID)"
            echo "$DAEMON_PID" > "$AUGER_DIR/daemon.pid"
            break
        fi
        sleep 0.5
    done
else
    echo "⚠️   Daemon script not found at $DAEMON_SCRIPT — skipping"
fi

# ── 11. Start container ───────────────────────────────────────────────────────
progress_msg "Starting Auger on personalized image..."
CONTAINER_HOME="/home/${_SAFE_USER}"
CONTAINER_USER="$(id -u):$(id -g)"
REPOS_MOUNT=""
[ -d "$HOME/repos" ] && REPOS_MOUNT="-v $HOME/repos:${CONTAINER_HOME}/repos"

KUBE_MOUNT=""
[ -d "$HOME/.kube" ] && KUBE_MOUNT="-v $HOME/.kube:${CONTAINER_HOME}/.kube:ro"

SSH_MOUNT=""
[ -d "$HOME/.ssh" ] && SSH_MOUNT="-v $HOME/.ssh:${CONTAINER_HOME}/.ssh:ro"

GITCONFIG_MOUNT=""
[ -f "$HOME/.gitconfig" ] && GITCONFIG_MOUNT="-v $HOME/.gitconfig:${CONTAINER_HOME}/.gitconfig:ro"

# Ask Auger session state (copilot events.jsonl lives here)
COPILOT_MOUNT=""
[ -d "$HOME/.copilot" ] && COPILOT_MOUNT="-v $HOME/.copilot:${CONTAINER_HOME}/.copilot"

# Docker socket for Cryptkeeper/Prospector widgets
# Also pass --group-add so the auger user inside the container can connect to the daemon.
# On Amazon WorkSpaces the socket is owned by root:video (GID 44) -- not root:docker.
DOCKER_SOCK_MOUNT=""
DOCKER_SOCK_GROUP=""
if [ -S /var/run/docker.sock ]; then
    DOCKER_SOCK_MOUNT="-v /var/run/docker.sock:/var/run/docker.sock"
    _sock_gid=$(stat -c '%g' /var/run/docker.sock 2>/dev/null)
    [ -n "$_sock_gid" ] && DOCKER_SOCK_GROUP="--group-add $_sock_gid"
fi

# Chrome binary for Host Tools browser launch
CHROME_MOUNT=""
[ -d /opt/google/chrome ] && CHROME_MOUNT="-v /opt/google/chrome:/opt/google/chrome:ro"

# DNS fix: 169.254.169.253 (AWS VPC DNS) is unreachable from inside the container
# even with --network host. Build a patched resolv.conf mounting 8.8.8.8 as the
# primary nameserver so RDS/private hostnames (*.rds.amazonaws.com) resolve.
AUGER_RESOLV="/tmp/auger-resolv.conf"
{
    grep -v '^nameserver' /etc/resolv.conf 2>/dev/null || true
    echo "nameserver 8.8.8.8"
    echo "nameserver 1.1.1.1"
    grep '^nameserver' /etc/resolv.conf 2>/dev/null | grep -v '169\.254\.' || true
} > "$AUGER_RESOLV"
RESOLV_MOUNT="-v $AUGER_RESOLV:/etc/resolv.conf:ro"

# ── DNS detection ─────────────────────────────────────────────────────────────
# Amazon WorkSpaces use systemd-resolved with a 127.0.0.53 stub resolver that
# is unreachable from inside Docker containers. Detect the real upstream DNS
# servers and pass them via --dns so internal hostnames (RDS, Artifactory, etc.)
# resolve correctly inside the container.
DNS_ARGS=""
if command -v resolvectl &>/dev/null; then
    while read -r ns; do
        [ -n "$ns" ] && DNS_ARGS="$DNS_ARGS --dns $ns"
    done < <(resolvectl status 2>/dev/null | awk '/DNS Servers:/{for(i=3;i<=NF;i++) print $i}' | sort -u | head -4)
fi
if [ -z "$DNS_ARGS" ] && [ -f /etc/resolv.conf ]; then
    while IFS= read -r line; do
        case "$line" in
            nameserver\ *)
                ns="${line#nameserver }"
                # Skip loopback (127.x.x.x) and link-local (169.254.x.x) — unreachable inside containers
                case "$ns" in 127.*|169.254.*) ;; *) DNS_ARGS="$DNS_ARGS --dns $ns" ;; esac ;;
        esac
    done < /etc/resolv.conf
fi
# Hard fallback: if no non-loopback DNS found, use GSA-reachable public resolvers
[ -z "$DNS_ARGS" ] && DNS_ARGS="--dns 8.8.8.8 --dns 8.8.4.4"
progress_msg "Preparing container DNS and mounts..."

if ! docker run -d \
    --name "$CONTAINER" \
    --network host \
    --security-opt seccomp:unconfined \
    --user "$CONTAINER_USER" \
    -e DISPLAY="$DISPLAY_VAL" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v "$AUGER_DIR:${CONTAINER_HOME}/.auger" \
    -v /:/host:ro \
    ${REPOS_MOUNT} \
    ${KUBE_MOUNT} \
    ${SSH_MOUNT} \
    ${GITCONFIG_MOUNT} \
    ${COPILOT_MOUNT} \
    ${DOCKER_SOCK_MOUNT} \
    ${DOCKER_SOCK_GROUP} \
    ${CHROME_MOUNT} \
    ${RESOLV_MOUNT} \
    ${GH_TOKEN_ARG} \
    ${PROXY_ARGS} \
    ${DNS_ARGS} \
    "$PERSONALIZED_IMAGE" \
    auger start 2>&1 | tee -a "$PROGRESS_LOG"; then
    progress_error "Failed to launch Auger container."
    exit 1
fi

# ── 12. Wait for UI ───────────────────────────────────────────────────────────
progress_msg "Waiting for Auger UI to start..."
sleep 5

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    progress_msg "Auger container exited during startup. Recent container logs:"
    docker logs --tail 120 "$CONTAINER" 2>&1 | tee -a "$PROGRESS_LOG" || true
    progress_error "Auger container failed to start. Check docker logs auger-platform."
    exit 1
fi

# ── 12b. Host pip dependencies (no sudo needed) ──────────────────────────────
if ! python3 -c "import faster_whisper" 2>/dev/null; then
    echo "📦  Installing faster-whisper for voice transcription..."
    pip3 install --user --quiet faster-whisper 2>/dev/null \
        && echo "✅  faster-whisper installed" \
        || echo "⚠️  faster-whisper install failed — voice transcription disabled (run: pip3 install --user faster-whisper)"
fi

# ── 13. GNOME desktop launcher + tray autostart ───────────────────────────────
# Creates ~/.local/share/applications/auger-platform.desktop so Auger appears
# in the GNOME app grid and can be pinned to the dock. Also installs a tray
# autostart entry so, after workspace reboot, users can start Auger from the
# tray or from the launcher without auto-opening the full platform window.
# This runs from auger-launch.sh (the install_wizard path) so alpha testers get
# the GNOME launcher even if they never run docker-run.sh.
ICON_DIR="$HOME/.local/share/icons"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_PATH="$ICON_DIR/auger-platform.png"
DESKTOP_FILE="$DESKTOP_DIR/auger-platform.desktop"
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/auger-task-tray.desktop"
mkdir -p "$ICON_DIR" "$DESKTOP_DIR" "$AUTOSTART_DIR"
rm -f "$AUTOSTART_DIR/auger-platform.desktop"

# Render app icon from Python source (no file dependency)
python3 -c "
import sys
sys.path.insert(0, '${SCRIPT_DIR}/..')
try:
    from auger.ui.icons import install_app_icon
    path = install_app_icon('${ICON_PATH}')
    print('✅  App icon saved:', path)
except Exception as e:
    print('⚠️   Could not render app icon:', e)
" 2>/dev/null

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Auger Platform
GenericName=SRE Platform
Comment=Drill Down With Auger 🔩
Exec=bash ${SCRIPT_DIR}/auger-launch.sh
Icon=${ICON_PATH}
Terminal=false
Categories=Development;System;
StartupWMClass=Auger-platform
Keywords=auger;sre;devops;kubernetes;
DESKTOP

chmod +x "$DESKTOP_FILE"
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
progress_msg "GNOME launcher installed."

cat > "$AUTOSTART_FILE" <<AUTOSTART
[Desktop Entry]
Type=Application
Name=Auger Task Tray
Comment=Start Auger task tray on login
Exec=bash ${SCRIPT_DIR}/start-auger-tray.sh
Icon=${ICON_PATH}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
AUTOSTART
progress_msg "Tray autostart registered."
progress_msg "Auger startup complete."
progress_done

# ── 14. Start System Tray Applet ─────────────────────────────────────────────
DISPLAY="${DISPLAY_VAL}" bash "$SCRIPT_DIR/start-auger-tray.sh"

echo ""
echo "✅  Auger is running!"
echo ""
echo "   The Auger window should appear on your screen."
echo "   The system tray icon (🤖) gives you Open / Ask / Restart / Stop controls."
echo ""
echo "   To stop Auger:  docker rm -f auger-platform"
echo ""
