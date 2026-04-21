#!/bin/bash
# Deploy or upgrade JupyterHub for PlatformGen
# Usage: GITHUB_CLIENT_ID=xxx GITHUB_CLIENT_SECRET=yyy ./deploy.sh
# JupyterHub lives at https://platformgen.ai/hub
# Ingress: prod-platformgen ingress routes /hub -> jupyterhub-proxy ExternalName service

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

if [ -z "$GITHUB_CLIENT_ID" ] || [ -z "$GITHUB_CLIENT_SECRET" ]; then
  echo "❌  Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET"
  echo "    OAuth App: https://github.com/organizations/techno-vet/settings/applications"
  echo "    Callback:  https://platformgen.ai/hub/oauth_callback"
  exit 1
fi

VALUES=$(mktemp /tmp/jhub-values-XXXXXX.yaml)
trap "rm -f $VALUES" EXIT
sed \
  -e "s/REPLACE_GITHUB_CLIENT_ID/$GITHUB_CLIENT_ID/" \
  -e "s/REPLACE_GITHUB_CLIENT_SECRET/$GITHUB_CLIENT_SECRET/" \
  "$SCRIPT_DIR/values.yaml" > "$VALUES"

echo "🚀 Deploying JupyterHub (genny-hub namespace)..."
helm upgrade --install genny-hub jupyterhub/jupyterhub \
  --namespace genny-hub \
  --values "$VALUES" \
  --timeout 10m \
  --wait

echo ""
echo "✅ JupyterHub deployed — https://platformgen.ai/hub"
kubectl get pods -n genny-hub
