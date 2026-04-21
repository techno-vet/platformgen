# PlatformGen — AI Platform Builder

> *Build anything with Genny.* 🧩

## What Is PlatformGen?

**PlatformGen** (hosted at [PlatformGen.ai](https://platformgen.ai) / [AskGenny.ai](https://askgenny.ai)) is an open-source AI platform builder. Drop in a widget, wire a dependency, and Genny — your AI agent — configures, explains, and operates it for you.

PlatformGen is not just an SRE tool. It is a **general-purpose AI platform builder**: give it a widget manifest and Genny can build a dev tool, a business dashboard, a data pipeline, or anything else you can describe.

---

## How It Evolved from Auger SRE Platform

PlatformGen grew out of the **Auger AI SRE Platform**, built at GSA ASSIST to help SREs manage Kubernetes pods, GitHub PRs, ServiceNow tickets, Jira stories, Confluence docs, and more — all from a single Tkinter desktop app.

The key insight from Auger: the *widget dependency system* is the real invention. Auger described every widget's purpose, its dependencies, and its rules in a static YAML manifest (`widget_manifests.yaml`). The AI agent loaded this manifest at session start and could reason about every widget without needing to read the source code.

**PlatformGen takes that idea and makes it universal.** Strip out the GSA-specific integrations, wire in a proper agentic AI backend (smolagents), and you have a platform that can build anything.

---

## The Lego Widget Dependency System

Every widget is a Lego brick. Each brick declares:

```yaml
widgets:
  my_widget:
    title: "My Widget"
    purpose: "What this widget does and why"
    depends_on: [api_config]          # bricks this one needs
    used_by: [story_to_prod, tasks]   # bricks that need this one
    key_data_files:
      - "~/.genny/.env  (credentials)"
    genny_rules:
      - "Always load credentials from ~/.genny/.env"
    session_resume_hint: "Check X before doing Y"
```

At startup, Genny reads `genny/data/widget_manifests.yaml` and knows the entire dependency graph. When you ask "set up GitHub integration", Genny knows:
1. `github` depends on `api_config`
2. `api_config` reads from `~/.genny/.env`
3. Load the token, verify it, then proceed

**Dependency resolution is automatic.** You never have to tell Genny the order — the manifest encodes it.

---

## How to Contribute Widgets

1. **Create your widget** in `genny/ui/widgets/your_widget.py`
   - Subclass or follow the pattern in any existing widget
   - Use `~/.genny/.env` for credentials (never hardcode)

2. **Register it** in `genny/data/widget_manifests.yaml`:
   ```yaml
   your_widget:
     title: "Your Widget"
     purpose: "..."
     depends_on: [api_config]
     used_by: []
     genny_rules: []
   ```

3. **Wire it into the app** in `genny/app.py` (follow the existing widget-loading pattern)

4. **Add a README** in `docs/README_YOUR_WIDGET.md`

5. Open a PR — Genny will review it in Phase 2 🤖

---

## Roadmap

### Phase 1 — Rebrand (complete ✅)
- Rename package: `auger/` → `genny/`
- Rebrand all UI strings: Auger → Genny
- Strip GSA-specific credentials
- Publish to [github.com/techno-vet/platformgen](https://github.com/techno-vet/platformgen)

### Phase 2 — Wire GennyRunner / smolagents
- Replace the `gh copilot` CLI stub in `genny/ui/ask_genny.py` with a real agentic AI runner
- Use [smolagents](https://github.com/huggingface/smolagents) as the agent framework
- `GennyRunner` class: loads widget manifests, resolves dependencies, executes tools
- Support local LLM (Ollama) + OpenAI / Anthropic backends
- Add `genny chat` CLI for headless use

### Phase 3 — Web UI + Per-User Pods
- Replace Tkinter with a web UI (FastAPI + htmx or React)
- Per-user Docker pods: each user gets their own `~/.genny/` volume
- Widget marketplace: publish and install widget packs as pip packages
- `genny add widget my-widget-pack` installs and registers automatically

---

## Origin Story

See [`docs/origin/BOOTSTRAP_PROMPT.md`](docs/origin/BOOTSTRAP_PROMPT.md) for how Auger (and therefore PlatformGen) was born.

---

*PlatformGen is MIT licensed. Build freely.*
