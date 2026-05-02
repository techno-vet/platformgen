#!/bin/bash
# Deploy or upgrade JupyterHub for PlatformGen
# Usage: GITHUB_CLIENT_ID=xxx GITHUB_CLIENT_SECRET=yyy ./deploy.sh
# JupyterHub lives at https://platformgen.ai/hub
# Ingress: prod-platformgen ingress routes /hub -> jupyterhub-proxy ExternalName service

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NAMESPACE="genny-hub"
SECRET_NAME="platformgen-github-oauth"
if [ -f "$SCRIPT_DIR/.env" ]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

GITHUB_CLIENT_ID="${GITHUB_CLIENT_ID:-${GITHUB_OAUTH_CLIENT_ID:-}}"
GITHUB_CLIENT_SECRET="${GITHUB_CLIENT_SECRET:-${GITHUB_OAUTH_CLIENT_SECRET:-}}"
GITHUB_CALLBACK_URL="${GITHUB_CALLBACK_URL:-https://platformgen.ai/hub/oauth_callback}"

if [ -z "$GITHUB_CLIENT_ID" ] || [ -z "$GITHUB_CLIENT_SECRET" ]; then
  echo "❌  Set GITHUB_CLIENT_ID/GITHUB_CLIENT_SECRET (or GITHUB_OAUTH_CLIENT_ID/GITHUB_OAUTH_CLIENT_SECRET)"
  echo "    OAuth App: https://github.com/organizations/techno-vet/settings/applications"
  echo "    Callback:  $GITHUB_CALLBACK_URL"
  exit 1
fi

echo "🔐 Syncing GitHub OAuth secret in ${NAMESPACE}..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic "$SECRET_NAME" \
  --namespace "$NAMESPACE" \
  --from-literal=client_id="$GITHUB_CLIENT_ID" \
  --from-literal=client_secret="$GITHUB_CLIENT_SECRET" \
  --from-literal=callback_url="$GITHUB_CALLBACK_URL" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "🚀 Deploying JupyterHub (genny-hub namespace)..."
helm upgrade --install genny-hub jupyterhub/jupyterhub \
  --namespace "$NAMESPACE" \
  --values "$SCRIPT_DIR/values.yaml" \
  --timeout 10m \
  --wait

echo ""
echo "✅ JupyterHub deployed — https://platformgen.ai/hub"
kubectl get pods -n "$NAMESPACE"
