# Origin — How Auger Was Built

This folder contains the complete origin story of the Auger SRE Platform: the original prompt that started it all, and the full chat history of the AI-assisted development session that built the platform from scratch.

**The entire Auger SRE Platform was built 100% through AI-assisted development.** No code was written manually — every file, every fix, every feature came from a conversation with GitHub Copilot (`auger`).

---

## Files

| File | Description |
|------|-------------|
| `BOOTSTRAP_PROMPT.md` | The original prompt that created the platform — start here |
| `conversations.jsonl` | Complete chat history (JSONL) from the development session |
| `conversations_clean.jsonl` | Cleaned/deduped version of the chat history |
| `conversations.jsonl.bak` | Backup of an earlier chat history snapshot |

---

## For New AI Agents (GitHub Copilot / auger)

If you are an AI agent reading this to understand your purpose, read `BOOTSTRAP_PROMPT.md` first — it contains the complete architectural spec for the platform. Then read through `conversations.jsonl` to understand how the platform evolved, what problems were solved, and what decisions were made.

Key things to know:
- You are the **Auger AI Agent** embedded inside the Auger SRE Platform
- Your purpose is to help SREs by answering questions AND generating new widgets dynamically
- Generated widgets are `tk.Frame` subclasses saved to `auger/ui/widgets/` and hot-reloaded at runtime
- All credentials live in `~/.auger/.env` — never hardcode secrets
- The platform runs in Docker (`scripts/docker-run.sh`) or pip-installed (`auger start`)
- DISPLAY must be `:1` for the Tkinter UI to appear on DCV/X11

---

## The Development Journey

The platform was developed in a single session starting **2026-02-27**. Here's a high-level summary of what was built:

1. **Bootstrap** — Full Tkinter framework: tabbed content area, hot-reload, markdown widget, Ask Auger panel, API Key Configurator widget
2. **Packaging** — Converted to proper Python package (`pyproject.toml`, `setup.cfg`, `auger` CLI entry point)
3. **Containerization** — Dockerfile, docker-compose.yml, with X11/DCV display passthrough
4. **DNS fix** — Container couldn't resolve `api.github.com`; added explicit DNS `8.8.8.8/8.8.4.4`
5. **`.env` unification** — All three run modes (pip, docker-compose, docker-run) share `~/.auger/.env`
6. **UID passthrough** — Container runs as host UID to allow bind-mounted `~/.auger` to be writable
7. **Widget fixes** — Cryptkeeper Lite subprocess→import fix, widget reopen-after-close fix
8. **Auto-rebuild** — `docker-run.sh` detects git commit mismatch and rebuilds automatically
9. **Distribution** — `scripts/docker-run.sh` one-liner for Artifactory users with zero setup

---

## Reading the Chat History

```bash
# View all user prompts
jq -r 'select(.role=="user") | "\(.timestamp): \(.content[:80])"' docs/origin/conversations.jsonl

# View all assistant responses  
jq -r 'select(.role=="assistant") | "\(.timestamp): \(.content[:80])"' docs/origin/conversations.jsonl

# Count messages
wc -l docs/origin/conversations.jsonl
```
