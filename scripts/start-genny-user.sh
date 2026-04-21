#!/bin/bash
# Start Genny FastAPI server in background on port 8889, then run jupyterhub-singleuser
# JupyterHub requires jupyterhub-singleuser as the main process (port 8888)
# Genny UI runs alongside on port 8889, accessible via /user/{name}/proxy/8889/

export GENNY_PLATFORM_DIR=${GENNY_PLATFORM_DIR:-/opt/genny-platform}

# Start Genny FastAPI + Next.js UI in background
cd $GENNY_PLATFORM_DIR
python -m uvicorn genny.web.app:app --host 0.0.0.0 --port 8889 &
GENNY_PID=$!
echo "Genny UI started (PID $GENNY_PID) on port 8889"

# Hand off to jupyterhub-singleuser as main process
exec jupyterhub-singleuser "$@"
