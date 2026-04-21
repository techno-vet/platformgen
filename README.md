# PlatformGen — Powered by Genny AI
### *Build Anything with Genny* 🧩

> ⚠️ **Alpha Release** - Phase 1 rebrand complete. See [ALPHA_TESTING.md](ALPHA_TESTING.md) for testing guide.

**AI Platform Builder — dynamic widgets, Genny AI agent, and a Lego-style dependency system**

PlatformGen (AskGenny.ai) is a flexible AI platform builder for developers, SREs, BAs, and POs:
- 🤖 **Ask Genny** - AI chat assistant (Phase 2: wired to GennyRunner/smolagents)
- 📊 **Dynamic Widgets** - Pods monitoring, GitHub PRs, ServiceNow tickets, CVE scanning, and more  
- 🔐 **Secure Credential Management** - Encrypted secrets, environment-based configuration
- 🔄 **Hot Reload** - Develop and test widgets without restarting
- 🎨 **Modern UI** - Dark theme, responsive design
- 🔌 **Extensible** - Easy to add custom widgets and integrations

> **Enterprise users:** Zscaler certs are included in `zscaler_certs/` — copy as needed for your SSL setup.

---

## Quick Start

### Prerequisites
- Python 3.10 or higher
- Git
- X11 display (Linux) or XQuartz (macOS)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/techno-vet/platformgen.git ~/repos/platformgen

# 2. Run the install wizard — one entry point for everyone
cd ~/repos/platformgen && ./scripts/install_wizard
```

Optional before onboarding: `cp .env.example ~/.genny/.env` and pre-fill any keys you already have.

The wizard handles token detection and prompts for missing `GH_TOKEN` and other credentials, installs the host `genny` CLI for terminal Ask Genny, pulls Docker images, and sets up the GNOME launcher.

---

## Features

- **Ask Genny Chat** - AI assistant helps configure integrations
- **Pods Monitor** - DataDog Kubernetes pod monitoring
- **GitHub** - PRs, repos, CI/CD status
- **ServiceNow** - Incidents, changes (web scraping, no API key!)
- **Cryptkeeper Lite** - Jasypt encryption, multi-environment
- **Prospector** - CVE scanning and diff
- **Hot Reload** - Widget development without restart

---

## Documentation

- [Quick Start Guide](docs/QUICKSTART.md)
- [PlatformGen Vision](PLATFORMGEN.md)
- [Configuration Guide](docs/README_API_CONFIG.md)

---

## CLI Commands

```bash
# Dual-mode usage:
genny                   # Open ask prompt (GUI)
genny "your question"   # Quick ask (terminal)

# Platform commands:
genny init              # Initialize configuration
genny start             # Launch GUI
genny doctor            # Run diagnostics
genny config            # Show configuration
genny widgets           # List available widgets
```

---

## Support

- **Issues:** https://github.com/techno-vet/platformgen/issues
- **Ask Genny:** Open the chat panel for help!

---

**Made with ❤️ by PlatformGen** | [PlatformGen.ai](https://platformgen.ai) | [AskGenny.ai](https://askgenny.ai)
