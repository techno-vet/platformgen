# Genny Platform — Contributor Testing Guide

You're not just testing Genny — you're building it. Real SRE infrastructure, real AI assistant, and a live codebase you can edit. Widget changes hot-reload instantly. If something breaks, Ask Genny can fix it. Push your ideas.

---

## Install (one command, first time only)

```bash
# 1. Clone the repo (if you haven't already)
git clone https://github.helix.gsa.gov/assist/genny-ai-sre-platform.git ~/repos/genny-ai-sre-platform

# 2. Run the install wizard — one entry point for everyone
cd ~/repos/genny-ai-sre-platform && ./scripts/install_wizard
```

The wizard will:
- Auto-detect your GitHub Copilot token (from `gh` CLI or env — only prompts if not found)
- Auto-detect Artifactory credentials (AU Gold users: fully silent, no prompts)
- Pull the Docker image (~500 MB, once only) and launch Genny on your desktop
- Install a GNOME launcher so Genny appears in your app grid going forward

**After first install:** click the Genny icon in your app grid — it uses `docker-run.sh` directly (same as the dev team). No re-running the wizard.

**AU Gold users:** setup is zero-prompt — your Artifactory keys in `~/.astutl/astutl_secure_config.env` are detected automatically.

**After it launches:** Ask Genny is your first stop. Ask it anything about setup, credentials, widgets, or the codebase.

---

## What Needs Credentials (and What Doesn't)

| Widget | Works without creds? | Needs |
|--------|---------------------|-------|
| Ask Genny | ❌ | `GH_TOKEN` (github.com) — set automatically by setup |
| Tasks | ✅ | Nothing |
| Bash $ (terminal) | ✅ | Nothing |
| Explorer | ✅ | Nothing |
| Help | ✅ | Nothing |
| GitHub | ❌ | `GHE_TOKEN` (github.helix.gsa.gov) |
| Jira | ❌ | MFA session via Jira widget login |
| Pods / K8s | ❌ | `RANCHER_BEARER_TOKEN` |
| Artifactory | ❌ | `ARTIFACTORY_IDENTITY_TOKEN` |
| DataDog | ❌ | `DATADOG_API_KEY` + `DATADOG_APP_KEY` |
| ServiceNow | ❌ | `SN_COOKIES` (auto-captured via Host Tools login) |
| Story → Prod | ❌ | Jira + GitHub + Artifactory + Flux |
| Flux Config | ❌ | `GHE_TOKEN` |
| Database | ❌ | `DB_HOST`, `DB_USER`, `DB_PASSWORD` |

To set any credential: open **API Keys+** widget (🔑 tab) or ask:
> *"Help me set up the GitHub widget"*

---

## Contributor Tasks

### Task 1 — Install and launch (required)

Run the wizard, confirm platform opens.

- [ ] `cd ~/repos/genny-ai-sre-platform && ./scripts/install_wizard` completes without errors
- [ ] Genny window opens on desktop
- [ ] System tray icon appears
- [ ] Ask Genny responds to: *"What widgets are available?"*

**Report:** Any errors during setup? Token detection work automatically?

---

### Task 2 — Ask Genny onboarding (required)

Test that Ask Genny can guide credential setup.

- [ ] Ask: *"What credentials do I need for the Jira widget?"*
- [ ] Ask: *"Help me get the GitHub widget working"*
- [ ] Ask: *"What's the difference between GH_TOKEN and GHE_TOKEN?"*

**Report:** Did Ask Genny give accurate, useful answers?

---

### Task 3 — Configure your most-used widgets (pick 2-3)

Using Ask Genny or the API Keys+ widget, get credentials in place for the widgets most relevant to your work.

**Report:** Which widgets did you configure? Any friction in the credential setup process?

---

### Task 4 — Story → Prod pipeline (if you have full creds)

If you have Jira + GHE + Artifactory configured:

- [ ] Open Story → Prod widget
- [ ] Load a real Jira story you're working on
- [ ] Walk through the pipeline stages

**Report:** Does the pipeline correctly reflect your story's current state?

---

### Task 5 — Workspace restart persistence

- [ ] Restart your WorkSpace (or log out and back in)
- [ ] Confirm Genny auto-starts without manual intervention

**Report:** Did it come back automatically?

---

## Known Alpha Limitations

- **Jira widget MFA:** after the recent Jira upgrade, re-auth may be needed — click Login in the Jira widget if it shows expired session
- **Story → Prod Loop A** (local Docker deploy panel) is not yet implemented
- **Self-healing** (auto-fix on widget crash) is planned for beta

---

## Reporting Issues

Open Genny → Ask Genny: *"I found a bug: [describe it]"*

Or file an issue: https://github.helix.gsa.gov/assist/genny-ai-sre-platform/issues

Include: what you did, what you expected, what happened, and `docker logs genny-platform` output if relevant.

---

## Useful Commands

```bash
# Restart Genny (keeps daemon + tray running)
curl -s http://localhost:7437/restart_platform

# Full restart (daemon + container)
docker rm -f genny-platform && bash ~/repos/genny-ai-sre-platform/scripts/genny-launch.sh

# Check daemon health
curl http://localhost:7437/health

# View logs
docker logs genny-platform
tail -f ~/.genny/daemon.log
```
