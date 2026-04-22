#!/bin/bash
# genny — Copilot CLI wrapper for the Genny Platform
#
# Usage:
#   genny <question>         Ask Genny via GitHub Copilot
#   genny                    Open interactive Copilot session
#
# Auth priority:
#   1. GITHUB_COPILOT_TOKEN from ~/.genny/.env  (dedicated Copilot PAT)
#   2. GITHUB_TOKEN from ~/.genny/.env           (repo PAT — works if it has 'copilot' scope)
#   3. GH_TOKEN from environment                 (JupyterHub OAuth — may lack copilot scope)

if [ -f "$HOME/.genny/.env" ]; then
    COPILOT_PAT=$(grep '^GITHUB_COPILOT_TOKEN=' "$HOME/.genny/.env" 2>/dev/null \
        | head -1 | sed 's/^GITHUB_COPILOT_TOKEN=//;s/^"//;s/"$//')
    REPO_PAT=$(grep '^GITHUB_TOKEN=' "$HOME/.genny/.env" 2>/dev/null \
        | head -1 | sed 's/^GITHUB_TOKEN=//;s/^"//;s/"$//')
    TOKEN="${COPILOT_PAT:-$REPO_PAT}"
    if [ -n "$TOKEN" ]; then
        export GH_TOKEN="$TOKEN"
    fi
fi

COPILOT=/usr/local/bin/copilot

if [ ! -x "$COPILOT" ]; then
    echo "Error: Copilot CLI not found at $COPILOT" >&2
    exit 1
fi

if [ -z "$*" ]; then
    exec "$COPILOT"
else
    exec "$COPILOT" -p "$*" --allow-all --silent --continue
fi
