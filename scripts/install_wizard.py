#!/usr/bin/env python3
"""
Genny SRE Platform — Install Wizard

Standalone Tk GUI for first-time setup. Runs on the host (no Docker required).

Usage:
    python3 scripts/install_wizard.py

Requirements (host): Python 3.8+, tkinter, docker
No pip installs needed — stdlib only.
"""
# ── GTK font env cleanup (prevents blank labels on some Ubuntu desktops) ──────
import os
for _var in ("GTK_PATH", "GTK_DATA_PREFIX", "GTK_EXE_PREFIX", "GTK_MODULES"):
    os.environ.pop(_var, None)

import sys
import subprocess
import threading
import urllib.request
import urllib.error
import shutil
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
REPO_DIR     = SCRIPT_DIR.parent
AUGER_DIR    = Path.home() / ".genny"
ENV_FILE     = AUGER_DIR / ".env"
ENV_TEMPLATE = REPO_DIR / ".env.example"
LAUNCH_SH    = SCRIPT_DIR / "genny-launch.sh"
ART_REGISTRY = "artifactory.helix.gsa.gov"
AUGER_IMAGE = f"{ART_REGISTRY}/gs-assist-docker-repo/genny-platform:20260311"
GHE_HOST = "github.helix.gsa.gov"
GHE_URL = f"https://{GHE_HOST}"
GHE_API_USER = f"{GHE_URL}/api/v3/user"

# Candidate locations for astutl config (checked in priority order)
ASTUTL_CANDIDATES = [
    Path.home() / ".astutl" / "astutl_secure_config.env",                              # installed AU Gold
    Path.home() / "repos" / "devtools-scripts" / "au-silver" / "config" / ".astutl" / "astutl_secure_config.env",
    Path.home() / "repos" / "devtools-scripts" / "astutl"   / "config" / ".astutl" / "astutl_secure_config.env",
    Path.home() / "repos" / "devtool-scripts-orig" / "au-silver" / "config" / ".astutl" / "astutl_secure_config.env",
    Path.home() / "repos" / "devtools-scripts-6.1" / "au-silver" / "config" / ".astutl" / "astutl_secure_config.env",
]

# Maps astutl key name → Genny .env key name (+ optional display label for logging)
# "~" means "copy only if destination is not already set"
ASTUTL_KEY_MAP = {
    # Artifactory
    "ARTIFACTORY_IDENTITY_TOKEN": "ARTIFACTORY_IDENTITY_TOKEN",
    "ARTIFACTORY_API_KEY":        "ARTIFACTORY_API_KEY",
    "ARTIFACTORY_USER":           "ARTIFACTORY_USERNAME",       # astutl uses _USER, Genny uses _USERNAME
    "ARTIFACTORY_PASSWORD":       "ARTIFACTORY_PASSWORD",
    # GitHub / Copilot (github.com)
    "GH_TOKEN":                   "GH_TOKEN",
    "GH_CLI_PAT":                 "GH_TOKEN",                   # fallback source; won't overwrite GH_TOKEN
    # GitHub Enterprise (github.helix.gsa.gov)
    "GH_ENTERPRISE_TOKEN":        "GHE_TOKEN",
    "GSA_EMAIL":                  "GHE_USERNAME",
    # Jira
    "JIRA_PAT":                   "JIRA_API_TOKEN",
    # Jenkins
    "JENKINS_API_KEY":            "JENKINS_API_TOKEN",
    # DataDog  (astutl uses DD_*, Genny uses DATADOG_*)
    "DD_API_KEY":                 "DATADOG_API_KEY",
    "DD_APP_KEY":                 "DATADOG_APP_KEY",
    # Rancher
    "RANCHER_BEARER_TOKEN":       "RANCHER_BEARER_TOKEN",
    # AWS per-env buckets → Genny stores as AWS_1/2/3/4 slots
    # DEV / TEST / STAGING / PROD → slots 1-4
    "DEV_S3_AWS_ACCESS_KEY_ID":       "AWS_1_ACCESS_KEY_ID",
    "DEV_S3_AWS_SECRET_ACCESS_KEY":   "AWS_1_SECRET_ACCESS_KEY",
    "TEST_S3_AWS_ACCESS_KEY_ID":      "AWS_2_ACCESS_KEY_ID",
    "TEST_S3_AWS_SECRET_ACCESS_KEY":  "AWS_2_SECRET_ACCESS_KEY",
    "STAGING_S3_AWS_ACCESS_KEY_ID":   "AWS_3_ACCESS_KEY_ID",
    "STAGING_S3_AWS_SECRET_ACCESS_KEY": "AWS_3_SECRET_ACCESS_KEY",
    "PROD_S3_AWS_ACCESS_KEY_ID":      "AWS_4_ACCESS_KEY_ID",
    "PROD_S3_AWS_SECRET_ACCESS_KEY":  "AWS_4_SECRET_ACCESS_KEY",
    # Cryptkeeper per-env keys
    "DEV_CRYPTKEEPER_KEY":      "DEV_CRYPTKEEPER_KEY",
    "TEST_CRYPTKEEPER_KEY":     "TEST_CRYPTKEEPER_KEY",
    "STAGING_CRYPTKEEPER_KEY":  "STAGING_CRYPTKEEPER_KEY",
    "PROD_CRYPTKEEPER_KEY":     "PROD_CRYPTKEEPER_KEY",
    "LOCAL_CRYPTKEEPER_KEY":    "LOCAL_CRYPTKEEPER_KEY",
}

# ── Theme (matches Genny dark theme) ──────────────────────────────────────────
BG     = "#1e1e1e"
BG2    = "#2d2d2d"
FG     = "#d4d4d4"
GREEN  = "#4ec9b0"
YELLOW = "#dcdcaa"
RED    = "#f44747"
BLUE   = "#569cd6"
ORANGE = "#ce9178"
DIM    = "#6a6a6a"
ACCENT = "#007acc"
FONT   = ("Segoe UI", 10)
MFONT  = ("Consolas", 10)


# ── Wizard Window ─────────────────────────────────────────────────────────────

class WizardWindow:
    def __init__(self):
        import tkinter as tk
        from tkinter import scrolledtext
        self._tk = tk

        self.root = tk.Tk()
        self.root.title("Genny SRE Platform — Setup")
        self.root.geometry("720x560")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # Force window to front so it's not hidden behind other windows
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(500, lambda: self.root.attributes('-topmost', False))
        self._setup_running = True
        self._build_ui()

    def _build_ui(self):
        tk = self._tk
        from tkinter import scrolledtext

        # ── Header ─────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=ACCENT, pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr, text="🔩  Genny SRE Platform — First-Time Setup",
            bg=ACCENT, fg="white", font=("Segoe UI", 13, "bold"),
        ).pack(side=tk.LEFT, padx=16)

        # ── Log / chat area ────────────────────────────────────────────────
        self.log = scrolledtext.ScrolledText(
            self.root, bg=BG, fg=FG, font=MFONT,
            relief=tk.FLAT, wrap=tk.WORD, state=tk.DISABLED,
            padx=14, pady=10, insertbackground=FG,
        )
        self.log.pack(fill=tk.BOTH, expand=True)

        for name, fg_col, extra in [
            ("ok",     GREEN,  {}),
            ("err",    RED,    {}),
            ("warn",   YELLOW, {}),
            ("info",   BLUE,   {}),
            ("dim",    DIM,    {}),
            ("orange", ORANGE, {}),
            ("h2",     BLUE,   {"font": ("Segoe UI", 11, "bold")}),
            ("bold",   FG,     {"font": ("Consolas", 10, "bold")}),
        ]:
            self.log.tag_configure(name, foreground=fg_col, **extra)

        # ── Bottom bar ─────────────────────────────────────────────────────
        bottom = tk.Frame(self.root, bg=BG2, pady=6)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_var = tk.StringVar(value="Initializing…")
        tk.Label(
            bottom, textvariable=self.status_var,
            bg=BG2, fg=DIM, font=("Segoe UI", 9), anchor="w",
        ).pack(side=tk.LEFT, padx=12, fill=tk.X, expand=True)

        self.close_btn = tk.Button(
            bottom, text="Close", command=self.root.destroy,
            bg=ACCENT, fg="white", font=("Segoe UI", 10),
            relief=tk.FLAT, padx=18, pady=4,
            state=tk.DISABLED, cursor="hand2",
        )
        self.close_btn.pack(side=tk.RIGHT, padx=12)

    def _on_close(self):
        self.root.destroy()

    # ── Thread-safe UI helpers ────────────────────────────────────────────────

    def log_line(self, text, tag=None):
        """Append one line to the log. Thread-safe."""
        def _do():
            self.log.configure(state="normal")
            if tag:
                self.log.insert("end", text + "\n", tag)
            else:
                self.log.insert("end", text + "\n")
            self.log.configure(state="disabled")
            self.log.see("end")
        self.root.after(0, _do)

    def log_inline(self, text, tag=None):
        """Append text without a trailing newline. Thread-safe."""
        def _do():
            self.log.configure(state="normal")
            if tag:
                self.log.insert("end", text, tag)
            else:
                self.log.insert("end", text)
            self.log.configure(state="disabled")
            self.log.see("end")
        self.root.after(0, _do)

    def set_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))

    def open_link(self, label: str, url: str):
        """Append a clickable hyperlink button to the log area."""
        def _add():
            import webbrowser
            btn = tk.Label(
                self.log_text,
                text=f"  -> {label}: {url}",
                fg="#4ec9b0", bg="#1e1e1e",
                cursor="hand2",
                font=("Consolas", 9, "underline"),
            )
            btn.bind("<Button-1>", lambda _e: webbrowser.open(url))
            self.log_text.window_create(tk.END, window=btn)
            self.log_text.insert(tk.END, "\n")
            self.log_text.see(tk.END)
        self.root.after(0, _add)

    def ask_secret(self, prompt, title="Genny Setup"):
        from tkinter import simpledialog
        result  = [None]
        ev      = threading.Event()
        def _ask():
            result[0] = simpledialog.askstring(title, prompt, show="*", parent=self.root)
            ev.set()
        self.root.after(0, _ask)
        ev.wait()
        return result[0] or ""

    def ask_text(self, prompt, title="Genny Setup"):
        """Modal plain-text dialog — blocks the background thread."""
        from tkinter import simpledialog
        result  = [None]
        ev      = threading.Event()
        def _ask():
            result[0] = simpledialog.askstring(title, prompt, parent=self.root)
            ev.set()
        self.root.after(0, _ask)
        ev.wait()
        return result[0] or ""

    def mark_done(self, success=True):
        self._setup_running = False
        def _finish():
            self.close_btn.configure(state="normal")
            if success:
                self.status_var.set("✅  Setup complete — Genny is running")
            else:
                self.status_var.set("⚠️  Setup incomplete — see messages above")
        self.root.after(0, _finish)

    def run(self):
        t = threading.Thread(target=_run_setup, args=(self,), daemon=True)
        t.start()
        self.root.mainloop()


# ── Credential helpers ────────────────────────────────────────────────────────

def _read_env_key(path, key):
    if not path or not path.exists():
        return ""
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith(f"{key}="):
            return line[len(key) + 1:].strip().strip("'\"")
    return ""


def _set_env_key(key, val):
    AUGER_DIR.mkdir(parents=True, exist_ok=True)
    if not ENV_FILE.exists():
        ENV_FILE.touch(mode=0o600)
    lines   = ENV_FILE.read_text(errors="replace").splitlines()
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={val}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"{key}={val}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n")
    ENV_FILE.chmod(0o600)


def _seed_env_template():
    AUGER_DIR.mkdir(parents=True, exist_ok=True)
    if ENV_FILE.exists() and ENV_FILE.read_text(errors="replace").strip():
        ENV_FILE.chmod(0o600)
        return False
    if ENV_TEMPLATE.exists():
        ENV_FILE.write_text(ENV_TEMPLATE.read_text(errors="replace"))
    else:
        ENV_FILE.touch(mode=0o600)
    ENV_FILE.chmod(0o600)
    return True


def _gh_token_valid(token):
    try:
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "genny-install-wizard/1.0",
            },
        )
        # Bypass corporate proxy for external calls
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=8) as resp:
            return resp.status == 200
    except Exception:
        return False


def _ghe_token_valid(token):
    try:
        req = urllib.request.Request(
            GHE_API_USER,
            headers={
                "Authorization": f"token {token}",
                "User-Agent": "genny-install-wizard/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status == 200
    except Exception:
        return False


def _art_login_valid(user, key):
    try:
        login = subprocess.run(
            ["docker", "login", ART_REGISTRY, "-u", user, "--password-stdin"],
            input=key.encode(),
            capture_output=True,
            timeout=25,
        )
        if login.returncode != 0:
            return False
        inspect = subprocess.run(
            ["docker", "manifest", "inspect", AUGER_IMAGE],
            capture_output=True,
            timeout=30,
        )
        return inspect.returncode == 0
    except Exception:
        return False


def _find_host_genny_bin():
    candidates = [
        shutil.which("genny"),
        str(Path.home() / ".local" / "bin" / "genny"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return ""


def _find_host_copilot_bin():
    candidates = [
        shutil.which("copilot"),
        str(Path.home() / ".local" / "bin" / "copilot"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return ""


def _install_host_genny():
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    user_bin = str(Path.home() / ".local" / "bin")
    env["PATH"] = f"{user_bin}:{env.get('PATH', '')}" if env.get("PATH") else user_bin
    cmd = [sys.executable, "-m", "pip", "install", "--user", "--upgrade", str(REPO_DIR)]
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
    except Exception as exc:
        return exc


def _install_host_copilot():
    env = os.environ.copy()
    user_bin = str(Path.home() / ".local" / "bin")
    env["PATH"] = f"{user_bin}:{env.get('PATH', '')}" if env.get("PATH") else user_bin
    cmd = [
        "bash",
        "-lc",
        "curl -fsSL https://gh.io/copilot-install | bash",
    ]
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
    except Exception as exc:
        return exc


def _choose_valid_art_secret(user, identity_token="", api_key=""):
    """Return (secret, label) for the first Artifactory secret that can read the image."""
    candidates = []
    if identity_token:
        candidates.append((identity_token, "Identity Token"))
    if api_key and api_key != identity_token:
        candidates.append((api_key, "API Key"))
    for secret, label in candidates:
        if _art_login_valid(user, secret):
            return secret, label
    return "", ""


def _read_gh_hosts_token(hostname):
    gh_cfg = Path.home() / ".config" / "gh" / "hosts.yml"
    if not gh_cfg.exists():
        return ""
    current_host = ""
    for raw in gh_cfg.read_text(errors="replace").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not raw.startswith((" ", "\t")) and line.endswith(":"):
            current_host = line[:-1].strip()
            continue
        if current_host == hostname:
            stripped = line.strip()
            if stripped.startswith(("oauth_token:", "token:")):
                return stripped.split(":", 1)[1].strip().strip("'\"")
    return ""


def _read_git_credential_token(hostname):
    try:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        r = subprocess.run(
            ["git", "credential", "fill"],
            input=f"protocol=https\nhost={hostname}\n".encode(),
            capture_output=True,
            timeout=5,
            env=env,
        )
        for line in r.stdout.decode(errors="replace").splitlines():
            if line.startswith("password="):
                return line[9:].strip()
    except Exception:
        pass
    return ""


def _detect_gh_token():
    """Returns (token, source) — empty strings if nothing found."""
    # 1. Already saved
    tok = _read_env_key(ENV_FILE, "GH_TOKEN")
    if tok:
        return tok, "~/.genny/.env"

    # 2. gh CLI
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip(), "gh CLI"
    except Exception:
        pass

    # 3. Environment variables
    for var in ("GH_TOKEN", "GITHUB_TOKEN", "COPILOT_GITHUB_TOKEN"):
        val = os.environ.get(var, "")
        if val:
            return val, f"${var}"

    # 4. gh config file
    tok = _read_gh_hosts_token("github.com")
    if tok:
        return tok, "~/.config/gh/hosts.yml"

    # 5. git credential store (only classic/fine-grained PATs)
    tok = _read_git_credential_token("github.com")
    if tok and tok.startswith(("ghp_", "github_pat_", "github_pat_")):
        return tok, "git credential store"

    # 6. astutl devtools config (GH_TOKEN or GH_CLI_PAT)
    astutl = _find_astutl_file()
    if astutl:
        for key in ("GH_TOKEN", "GH_CLI_PAT"):
            val = _read_env_key(astutl, key)
            if val:
                short = str(astutl).replace(str(Path.home()), "~")
                return val, f"astutl ({key})"

    return "", ""


def _detect_ghe_token():
    """Returns (token, source) — empty strings if nothing found."""
    tok = _read_env_key(ENV_FILE, "GHE_TOKEN")
    if tok:
        return tok, "~/.genny/.env"

    for var in ("GHE_TOKEN", "GH_ENTERPRISE_TOKEN"):
        val = os.environ.get(var, "")
        if val:
            return val, f"${var}"

    try:
        r = subprocess.run(
            ["gh", "auth", "token", "--hostname", GHE_HOST],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip(), f"gh CLI ({GHE_HOST})"
    except Exception:
        pass

    tok = _read_gh_hosts_token(GHE_HOST)
    if tok:
        return tok, "~/.config/gh/hosts.yml"

    tok = _read_git_credential_token(GHE_HOST)
    if tok:
        return tok, "git credential store"

    astutl = _find_astutl_file()
    if astutl:
        tok = _read_env_key(astutl, "GH_ENTERPRISE_TOKEN")
        if tok:
            return tok, "astutl (GH_ENTERPRISE_TOKEN)"

    return "", ""


def _find_astutl_file():
    """Return the first existing astutl_secure_config.env path, or None."""
    for p in ASTUTL_CANDIDATES:
        if p.exists():
            return p
    return None


def _import_from_astutl(astutl_path):
    """
    Read astutl_secure_config.env and copy known keys to ~/.genny/.env.
    Only writes a key if the destination is not already set.
    Returns list of (genny_key, astutl_key) pairs that were imported.
    """
    imported = []
    for astutl_key, genny_key in ASTUTL_KEY_MAP.items():
        val = _read_env_key(astutl_path, astutl_key)
        if not val:
            continue
        existing = _read_env_key(ENV_FILE, genny_key)
        if existing:
            continue  # already set — don't overwrite
        _set_env_key(genny_key, val)
        imported.append((genny_key, astutl_key))
    return imported


def _detect_art_creds():
    """Returns (username, identity_token, api_key, source) — empty strings if nothing found."""
    user = (
        _read_env_key(ENV_FILE, "ARTIFACTORY_USERNAME")
        or _read_env_key(ENV_FILE, "ARTIFACTORY_USER")
        or os.environ.get("ARTIFACTORY_USERNAME", "")
        or os.environ.get("ARTIFACTORY_USER", "")
    )
    it = _read_env_key(ENV_FILE, "ARTIFACTORY_IDENTITY_TOKEN") or os.environ.get("ARTIFACTORY_IDENTITY_TOKEN", "")
    ak = _read_env_key(ENV_FILE, "ARTIFACTORY_API_KEY") or os.environ.get("ARTIFACTORY_API_KEY", "")
    if user and (it or ak):
        return user, it, ak, "~/.genny/.env / environment"

    astutl = _find_astutl_file()
    if astutl:
        # astutl uses ARTIFACTORY_USER (not _USERNAME)
        u  = _read_env_key(astutl, "ARTIFACTORY_USER") or _read_env_key(astutl, "ARTIFACTORY_USERNAME")
        it = _read_env_key(astutl, "ARTIFACTORY_IDENTITY_TOKEN")
        ak = _read_env_key(astutl, "ARTIFACTORY_API_KEY")
        if u and (it or ak):
            return u, it, ak, f"astutl ({astutl.parent.parent.name})"

    return "", "", "", ""


# ── Main setup flow ───────────────────────────────────────────────────────────

def _run_setup(wiz):
    w = wiz

    w.log_line("")
    w.log_line("  Genny SRE Platform — Setting up your environment", "bold")
    w.log_line("")

    seeded_template = _seed_env_template()
    if seeded_template:
        w.log_line("  Seeded ~/.genny/.env from .env.example so it can be pre-filled before onboarding.", "dim")
        w.log_line("")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 0 — Bulk import from astutl (AU Gold devtools)
    # ═══════════════════════════════════════════════════════════════════════
    astutl_path = _find_astutl_file()
    if astutl_path:
        w.log_line("  ── Step 0: AU Gold Credential Import ──────────────────", "h2")
        short = str(astutl_path).replace(str(Path.home()), "~")
        w.log_inline(f"  Found {short} — importing credentials… ")
        imported = _import_from_astutl(astutl_path)
        if imported:
            w.log_line(f"✅  {len(imported)} key(s) imported", "ok")
            # Group by service for readable output
            service_groups = {}
            for genny_key, astutl_key in imported:
                svc = genny_key.split("_")[0]
                service_groups.setdefault(svc, []).append(genny_key)
            for svc, keys in sorted(service_groups.items()):
                w.log_line(f"    {svc}: {', '.join(keys)}", "dim")
        else:
            w.log_line("(all keys already set — nothing new to import)", "dim")
        w.log_line("")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1 — GitHub Copilot token
    # ═══════════════════════════════════════════════════════════════════════
    w.log_line("  ── Step 1: GitHub Copilot Token ──────────────────────", "h2")
    w.set_status("Checking GitHub Copilot token…")

    gh_tok, gh_src = _detect_gh_token()
    gh_ok = False

    if gh_tok:
        w.log_inline(f"  Found token via {gh_src} — verifying… ")
        if _gh_token_valid(gh_tok):
            w.log_line("✅  valid", "ok")
            _set_env_key("GH_TOKEN", gh_tok)
            gh_ok = True
        else:
            w.log_line("❌  rejected by github.com", "err")
            gh_tok = ""
    else:
        w.log_line("  No GitHub token found automatically.", "warn")

    while not gh_ok:
        w.log_line("")
        w.log_line("  A github.com Personal Access Token is required for Ask Genny.", "dim")
        w.log_line("  1. Go to: https://github.com/settings/personal-access-tokens", "dim")
        w.log_line("  2. Click 'Generate new token (fine-grained)'", "dim")
        w.log_line("  3. Permission required: ✅ Copilot > Copilot requests (read-only)", "dim")
        w.log_line("     (No other scopes needed for Ask Genny)", "dim")
        w.open_link("Open GitHub token page", "https://github.com/settings/personal-access-tokens")
        w.log_line("")
        tok = w.ask_secret(
            "Paste your github.com Fine-Grained Personal Access Token\n\n"
            "Create one at:\n"
            "https://github.com/settings/personal-access-tokens\n\n"
            "Required permission: Copilot > Copilot requests (read-only)\n\n"
            "Leave blank to skip — Ask Genny won't work until GH_TOKEN is set.",
            title="GitHub Copilot Token",
        )
        if not tok:
            w.log_line("  ⚠️  Skipped — Ask Genny will not function until GH_TOKEN is added.", "warn")
            w.log_line("      Edit ~/.genny/.env to add it later.", "dim")
            break
        w.log_inline("  Verifying… ")
        if _gh_token_valid(tok):
            w.log_line("✅  valid", "ok")
            _set_env_key("GH_TOKEN", tok)
            gh_ok = True
        else:
            w.log_line("❌  github.com rejected that token — check scopes and try again", "err")

    w.log_line("")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1b — Enterprise GitHub token
    # ═══════════════════════════════════════════════════════════════════════
    w.log_line("  ── Step 1b: Enterprise GitHub Token ──────────────────", "h2")
    w.set_status("Checking Enterprise GitHub token…")

    ghe_tok, ghe_src = _detect_ghe_token()
    ghe_ok = False

    if ghe_tok:
        w.log_inline(f"  Found token via {ghe_src} — verifying against {GHE_HOST}… ")
        if _ghe_token_valid(ghe_tok):
            w.log_line("✅  valid", "ok")
            _set_env_key("GHE_URL", GHE_URL)
            _set_env_key("GHE_TOKEN", ghe_tok)
            ghe_ok = True
        else:
            w.log_line("❌  rejected by github.helix.gsa.gov", "err")
            ghe_tok = ""
    else:
        w.log_line("  No Enterprise GitHub token found automatically.", "warn")

    while not ghe_ok:
        w.log_line("")
        w.log_line("  A github.helix.gsa.gov token powers the GitHub widget, Prospector, and HTTPS git flows inside Genny.", "dim")
        w.log_line("  If you cloned with VS Code or browser auth, Genny still needs a separate GHE token in ~/.genny/.env.", "dim")
        w.log_line(f"  Get it at: {GHE_URL}/settings/tokens", "dim")
        w.log_line("  Recommended scopes: repo  read:user", "dim")
        w.open_link("Open Enterprise GitHub token page", f"{GHE_URL}/settings/tokens")
        w.log_line("")
        tok = w.ask_secret(
            "Paste your github.helix.gsa.gov Personal Access Token\n\n"
            "Create one at:\n"
            f"{GHE_URL}/settings/tokens\n\n"
            "Recommended scopes: repo, read:user\n\n"
            "Leave blank to skip — GitHub/Prospector features will stay limited until GHE_TOKEN is set.",
            title="Enterprise GitHub Token",
        )
        if not tok:
            w.log_line("  ⚠️  Skipped — GitHub Enterprise features will remain limited until GHE_TOKEN is added.", "warn")
            w.log_line("      Edit ~/.genny/.env to add it later.", "dim")
            break
        w.log_inline(f"  Verifying against {GHE_HOST}… ")
        if _ghe_token_valid(tok):
            w.log_line("✅  valid", "ok")
            _set_env_key("GHE_URL", GHE_URL)
            _set_env_key("GHE_TOKEN", tok)
            ghe_ok = True
        else:
            w.log_line("❌  github.helix.gsa.gov rejected that token — check scopes and try again", "err")

    w.log_line("")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1c — Host genny CLI
    # ═══════════════════════════════════════════════════════════════════════
    w.log_line("  ── Step 1c: Host Genny CLI ───────────────────────────", "h2")
    w.set_status("Checking host genny CLI…")

    host_genny = _find_host_genny_bin()
    host_copilot = _find_host_copilot_bin()
    if host_genny:
        w.log_line(f"  ✅  Host genny CLI already available at {host_genny}", "ok")
    elif gh_ok:
        w.log_line("  📦  Installing host genny CLI so Ask Genny works from any terminal…", "dim")
        install_result = _install_host_genny()
        if isinstance(install_result, Exception):
            w.log_line(f"  ⚠️  Host genny install error: {install_result}", "warn")
            w.log_line("      You can retry later with: python3 -m pip install --user --upgrade .", "dim")
        elif install_result.returncode == 0:
            host_genny = _find_host_genny_bin()
            if host_genny:
                w.log_line(f"  ✅  Host genny CLI installed at {host_genny}", "ok")
            else:
                w.log_line("  ⚠️  pip reported success but ~/.local/bin/genny was not found", "warn")
                w.log_line("      Retry later with: python3 -m pip install --user --upgrade .", "dim")
        else:
            err = (install_result.stderr or install_result.stdout or "").strip()
            w.log_line("  ⚠️  Host genny install failed — continuing with platform setup", "warn")
            if err:
                w.log_line(f"      {err.splitlines()[-1]}", "dim")
            w.log_line("      Retry later with: python3 -m pip install --user --upgrade .", "dim")
    else:
        w.log_line("  ⚠️  Skipping host genny install because no valid GitHub token is configured yet.", "warn")

    host_genny = _find_host_genny_bin()
    if host_copilot:
        w.log_line(f"  ✅  Host copilot CLI already available at {host_copilot}", "ok")
    elif host_genny:
        w.log_line("  📦  Installing standalone Copilot CLI required by terminal genny…", "dim")
        copilot_result = _install_host_copilot()
        if isinstance(copilot_result, Exception):
            w.log_line(f"  ⚠️  Host copilot install error: {copilot_result}", "warn")
            w.log_line("      Retry later with: curl -fsSL https://gh.io/copilot-install | bash", "dim")
        elif copilot_result.returncode == 0:
            host_copilot = _find_host_copilot_bin()
            if host_copilot:
                w.log_line(f"  ✅  Host copilot CLI installed at {host_copilot}", "ok")
            else:
                w.log_line("  ⚠️  Copilot installer reported success but ~/.local/bin/copilot was not found", "warn")
                w.log_line("      Retry later with: curl -fsSL https://gh.io/copilot-install | bash", "dim")
        else:
            err = (copilot_result.stderr or copilot_result.stdout or "").strip()
            w.log_line("  ⚠️  Host copilot CLI install failed — terminal Ask Genny may not work yet", "warn")
            if err:
                w.log_line(f"      {err.splitlines()[-1]}", "dim")
            w.log_line("      Retry later with: curl -fsSL https://gh.io/copilot-install | bash", "dim")
    else:
        w.log_line("  ⚠️  Skipping host copilot install until host genny CLI is available.", "warn")

    w.log_line("")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 2 — Artifactory credentials
    # ═══════════════════════════════════════════════════════════════════════
    w.log_line("  ── Step 2: Artifactory Credentials ───────────────────", "h2")
    w.set_status("Checking Artifactory credentials…")

    art_user, art_it, art_ak, art_src = _detect_art_creds()
    art_key = ""
    art_ok  = False

    if art_user and (art_it or art_ak):
        available = []
        if art_it:
            available.append("Identity Token")
        if art_ak:
            available.append("API Key")
        w.log_inline(
            f"  Found credentials via {art_src} ({' + '.join(available)}) — testing Docker image access… "
        )
        art_key, art_key_label = _choose_valid_art_secret(art_user, art_it, art_ak)
        if art_key:
            w.log_line("✅  success", "ok")
            # Persist from astutl if not already in .env
            if "astutl" in art_src:
                _set_env_key("ARTIFACTORY_USERNAME", art_user)
                if art_it:
                    _set_env_key("ARTIFACTORY_IDENTITY_TOKEN", art_it)
                if art_ak:
                    _set_env_key("ARTIFACTORY_API_KEY", art_ak)
                w.log_line("  Credentials saved to ~/.genny/.env", "dim")
            w.log_line(f"  Using saved {art_key_label} for Docker authentication", "dim")
            art_ok = True
        else:
            w.log_line("❌  Docker image access failed", "err")
            art_user = art_key = ""
    else:
        w.log_line("  No Artifactory credentials found automatically.", "warn")

    while not art_ok:
        w.log_line("")
        w.log_line(f"  Credentials needed to pull the Genny image from {ART_REGISTRY}.", "dim")
        w.log_line("  Preferred: Identity Token  •  Legacy fallback: API Key", "dim")
        w.log_line(f"  Find them at: https://{ART_REGISTRY} → Profile / Authentication Settings", "dim")
        w.log_line("")

        if not art_user:
            art_user = w.ask_text(
                "Artifactory username\n(your FCS username, e.g. jsmith)",
                title="Artifactory Username",
            )
        if not art_user:
            w.log_line("  ⚠️  Cannot pull image without Artifactory credentials.", "warn")
            w.log_line("      Run 'bash scripts/genny-setup.sh' to retry.", "dim")
            break

        identity_key = w.ask_secret(
            f"Artifactory Identity Token (recommended)\n(for user: {art_user})\n\n"
            f"Find it at: https://{ART_REGISTRY} → Profile → Identity Token\n\n"
            "Leave blank only if you need to try a legacy API key instead.",
            title="Artifactory Identity Token",
        )
        if identity_key:
            w.log_inline("  Testing Docker image access with Identity Token… ")
            if _art_login_valid(art_user, identity_key):
                w.log_line("✅  success", "ok")
                _set_env_key("ARTIFACTORY_USERNAME", art_user)
                _set_env_key("ARTIFACTORY_IDENTITY_TOKEN", identity_key)
                w.log_line("  Credentials saved to ~/.genny/.env", "dim")
                art_ok = True
                art_key = identity_key
                break
            w.log_line("❌  Identity Token could not read the Genny image", "err")

        api_key = w.ask_secret(
            f"Legacy Artifactory API Key (optional)\n(for user: {art_user})\n\n"
            f"If your account still has one, find it at: https://{ART_REGISTRY} → Profile → API Key",
            title="Artifactory API Key",
        )
        if api_key:
            w.log_inline("  Testing Docker image access with API Key… ")
            if _art_login_valid(art_user, api_key):
                w.log_line("✅  success", "ok")
                _set_env_key("ARTIFACTORY_USERNAME", art_user)
                _set_env_key("ARTIFACTORY_API_KEY", api_key)
                w.log_line("  Credentials saved to ~/.genny/.env", "dim")
                art_ok = True
                art_key = api_key
                break
            w.log_line("❌  API key could not read the Genny image", "err")

        w.log_line("  ⚠️  Cannot pull image without working Artifactory credentials.", "warn")
        w.log_line("      Run './scripts/install_wizard' again after updating ~/.genny/.env.", "dim")
        art_user = art_key = ""

    w.log_line("")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 2b — Host pip dependencies (no sudo needed)
    # ═══════════════════════════════════════════════════════════════════════
    w.log_line("  ── Step 2b: Host voice dependencies ──────────────────", "h2")
    w.set_status("Checking host pip dependencies…")

    _HOST_PIP_DEPS = [
        ("faster_whisper", "faster-whisper", "voice transcription (Ask Genny mic input)"),
    ]
    for _import_name, _pip_name, _desc in _HOST_PIP_DEPS:
        try:
            __import__(_import_name)
            w.log_line(f"  ✅  {_pip_name} already installed ({_desc})", "ok")
        except ImportError:
            w.log_line(f"  📦  Installing {_pip_name} — {_desc}…", "dim")
            try:
                _r = subprocess.run(
                    ["pip3", "install", "--user", "--quiet", _pip_name],
                    capture_output=True, text=True, timeout=120,
                )
                if _r.returncode == 0:
                    w.log_line(f"  ✅  {_pip_name} installed", "ok")
                else:
                    w.log_line(f"  ⚠️  {_pip_name} install failed — {_desc} disabled", "warn")
                    w.log_line(f"      pip3 install --user {_pip_name}", "dim")
            except Exception as _pip_exc:
                w.log_line(f"  ⚠️  {_pip_name} install error: {_pip_exc}", "warn")

    w.log_line("")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 3 — Launch the platform
    # ═══════════════════════════════════════════════════════════════════════
    w.log_line("  ── Step 3: Launching Genny Platform ──────────────────", "h2")
    w.set_status("Launching Genny…")

    if not LAUNCH_SH.exists():
        w.log_line(f"  ❌  Launch script not found: {LAUNCH_SH}", "err")
        w.log_line("  Make sure you're running from the genny-ai-sre-platform repo.", "dim")
        w.mark_done(success=False)
        return

    if not art_ok:
        w.log_line("  ⚠️  Skipping image pull — Artifactory credentials not configured.", "warn")
        w.log_line("  Add ARTIFACTORY_USERNAME plus ARTIFACTORY_IDENTITY_TOKEN", "dim")
        w.log_line("  (or a legacy ARTIFACTORY_API_KEY if your account still has one) to ~/.genny/.env,", "dim")
        w.log_line("  then run: bash scripts/genny-launch.sh", "dim")
        w.mark_done(success=False)
        return

    w.log_line("  Running genny-launch.sh…", "dim")
    w.log_line("  (First run pulls ~500 MB — this may take a few minutes)", "dim")
    w.log_line("")

    try:
        proc = subprocess.Popen(
            ["bash", str(LAUNCH_SH)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={
                **os.environ,
                "AUGER_WIZARD": "1",
                "AUGER_FORCE_REBUILD_PERSONALIZED": "1",
            },
        )
        for raw in proc.stdout:
            line = raw.rstrip()
            if not line:
                continue
            lo = line.lower()
            if any(x in lo for x in ("✅", "success", "started", "running", "complete")):
                w.log_line("  " + line, "ok")
            elif any(x in lo for x in ("❌", "error", "failed", "denied")):
                w.log_line("  " + line, "err")
            elif any(x in lo for x in ("⚠️", "warn", "skip")):
                w.log_line("  " + line, "warn")
            elif any(x in lo for x in ("pulling", "pulled", "already", "digest", "status:")):
                w.log_line("  " + line, "info")
            else:
                w.log_line("  " + line, "dim")
        proc.wait()

        # Exit 143 = SIGTERM (128+15): bash received SIGTERM during cleanup
        # (e.g. tray applet launch, sleep). Genny itself may still be running.
        # Verify by checking docker ps rather than trusting the exit code.
        container_up = False
        try:
            r = subprocess.run(
                ["docker", "ps", "--filter", "name=genny-platform",
                 "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=5)
            container_up = "genny-platform" in r.stdout
        except Exception:
            pass

        if proc.returncode == 0 or (proc.returncode == 143 and container_up):
            w.log_line("")
            w.log_line("  ✅  Genny is running!", "ok")
            w.log_line("  The platform window should now appear on your desktop.", "dim")

            # Verify daemon health
            try:
                import urllib.request, urllib.error
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                resp = opener.open("http://localhost:7437/health", timeout=3)
                w.log_line("  ✅  Host Tools daemon is healthy (port 7437)", "ok")
            except Exception:
                w.log_line("  ⚠️  Host Tools daemon not responding — it may still be starting", "warn")

            # Verify tray applet
            try:
                r2 = subprocess.run(["pgrep", "-f", "genny_tray.py"],
                                    capture_output=True, text=True, timeout=3)
                if r2.stdout.strip():
                    w.log_line("  ✅  System tray icon is running", "ok")
                else:
                    w.log_line("  ⚠️  Tray icon not detected — check ~/.genny/tray.log", "warn")
            except Exception:
                pass

            w.log_line("")
            w.log_line("  💡 Ask Genny is ready — type any question into the Ask Genny panel.", "info")
            w.log_line("  💡 Open the API Keys+ tab (🔑) to configure additional integrations.", "info")
            w.log_line("  💡 Need help? Type: what can you do?", "info")
            w.mark_done(success=True)
        else:
            w.log_line(f"  ❌  Launch script exited with code {proc.returncode}", "err")
            w.log_line("  Run:  docker logs genny-platform  for details.", "dim")
            w.mark_done(success=False)

    except FileNotFoundError:
        w.log_line("  ❌  'bash' not found — cannot run launch script", "err")
        w.mark_done(success=False)
    except Exception as exc:
        w.log_line(f"  ❌  Unexpected error: {exc}", "err")
        w.mark_done(success=False)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("ERROR: tkinter is not installed.")
        print("")
        print("Install it with:  sudo apt-get install -y python3-tk")
        print("")
        print("Falling back to the bash installer…")
        bash_setup = SCRIPT_DIR / "genny-setup.sh"
        if bash_setup.exists():
            os.execv("/bin/bash", ["/bin/bash", str(bash_setup)])
        sys.exit(1)

    wiz = WizardWindow()
    wiz.run()


if __name__ == "__main__":
    main()
