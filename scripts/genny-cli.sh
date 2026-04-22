#!/bin/bash
# genny — Copilot CLI wrapper for the Genny Platform
#
# Usage:
#   genny <question>         Ask Genny via GitHub Copilot
#   genny                    Open interactive Copilot session
#
# Auth priority:
#   1. GITHUB_TOKEN from ~/.genny/.env  (user's saved PAT with copilot scope)
#   2. GH_TOKEN from environment        (JupyterHub OAuth token — may lack copilot scope)

# Load saved PAT if available (preferred — has copilot scope)
if [ -f "$HOME/.genny/.env" ]; then
    SAVED_PAT=$(grep '^GITHUB_TOKEN=' "$HOME/.genny/.env" 2>/dev/null \
        | head -1 | sed 's/^GITHUB_TOKEN=//;s/^"//;s/"$//')
    if [ -n "$SAVED_PAT" ]; then
        export GH_TOKEN="$SAVED_PAT"
    fi
fi

COPILOT=/usr/local/bin/copilot

if [ ! -x "$COPILOT" ]; then
    echo "Error: Copilot CLI not found at $COPILOT" >&2
    echo "Please contact your platform administrator." >&2
    exit 1
fi

if [ -z "$*" ]; then
    exec "$COPILOT"
else
    exec "$COPILOT" -p "$*" --allow-all --silent --continue
fi
