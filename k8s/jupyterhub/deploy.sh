#!/bin/bash
# Deploy or upgrade JupyterHub for PlatformGen
# Usage: ./deploy.sh
# Prereq: set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in env or .env

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load secrets from .env if present
if [ -f "$SCRIPT_DIR/.env" ]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

if [ -z "$GITHUB_CLIENT_ID" ] || [ -z "$GITHUB_CLIENT_SECRET" ]; then
  echo "❌  Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET before deploying"
  echo "    Create a GitHub OAuth App at: https://github.com/organizations/techno-vet/settings/applications"
  echo "    Callback URL: https://platformgen.ai/hub/oauth_callback"
  exit 1
fi

# Patch values with real secrets (don't commit secrets to git)
VALUES=$(mktemp /tmp/jhub-values-XXXXXX.yaml)
sed \
  -e "s/REPLACE_GITHUB_CLIENT_ID/$GITHUB_CLIENT_ID/" \
  -e "s/REPLACE_GITHUB_CLIENT_SECRET/$GITHUB_CLIENT_SECRET/" \
  "$SCRIPT_DIR/values.yaml" > "$VALUES"

echo "🚀 Deploying JupyterHub to genny-hub namespace..."
helm upgrade --install genny-hub jupyterhub/jupyterhub \
  --namespace genny-hub \
  --values "$VALUES" \
  --timeout 10m \
  --wait

rm "$VALUES"
echo "✅ JupyterHub deployed!"
echo "   Hub URL: https://platformgen.ai/hub"
kubectl get pods -n genny-hub
