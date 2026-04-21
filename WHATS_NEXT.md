# What's Next - Genny Platform

**Repository:** https://github.helix.gsa.gov/assist/genny-ai-sre-platform  
**Status:** ✅ Initial structure complete and pushed to GitHub

---

## ✅ What's Done

1. **Repository Setup**
   - Complete Python package structure
   - PyPI-ready with pyproject.toml
   - CLI infrastructure (`genny` command)
   - Configuration management
   - All widgets and tools copied
   - Comprehensive documentation
   - MIT License
   - .gitignore for Python

2. **Committed and Pushed**
   - 49 files added
   - 15,512 lines of code
   - Commit: 5d2bd18
   - Branch: main

---

## 🚧 What Needs Fixing (Before First Test)

### 1. Fix app.py Imports
**Location:** `genny/app.py`

Current imports are absolute paths:
```python
# FIND lines like:
from ui.widgets.pods import PodsWidget

# CHANGE TO:
from genny.ui.widgets.pods import PodsWidget
```

**ALL imports need updating** - search for `from ui.` and `import ui.`

### 2. Update Config Loading in app.py
```python
# FIND:
config = yaml.safe_load(open('config.yaml'))

# CHANGE TO:
from genny.config_manager import AugerConfigManager
config_manager = AugerConfigManager()
config = config_manager.to_dict()
```

### 3. Create Integration Test Functions

Create `genny/integrations/github_integration.py`:
```python
def test_github(config):
    """Test GitHub API connection"""
    import requests
    token = config.get('github.token')
    if not token:
        return False
    
    headers = {'Authorization': f'token {token}'}
    response = requests.get('https://api.github.com/user', headers=headers)
    return response.status_code == 200
```

Create `genny/integrations/datadog_integration.py`:
```python
def test_datadog(config):
    """Test DataDog API connection"""
    import requests
    api_key = config.get('datadog.api_key')
    app_key = config.get('datadog.app_key')
    site = config.get('datadog.site', 'ddog-gov.com')
    
    if not api_key or not app_key:
        return False
    
    url = f"https://api.{site}/api/v1/validate"
    headers = {
        'DD-API-KEY': api_key,
        'DD-APPLICATION-KEY': app_key
    }
    response = requests.get(url, headers=headers)
    return response.status_code == 200
```

### 4. Fix Widget Loading Mechanism

In app.py, find widget loading code and update for package structure.

---

## 🧪 Testing Steps

### 1. Install in Development Mode
```bash
cd /home/bobbygblair/repos/genny-ai-sre-platform
pip install -e .
```

### 2. Run Diagnostics
```bash
genny doctor
```

Expected output:
- ✅ Python version
- ✅ Config file (will fail first time - expected)
- ✅ DISPLAY
- ✅ tkinter
- ✅ Dependencies

### 3. Initialize
```bash
genny init --token YOUR_GITHUB_TOKEN
```

Should create:
- `~/.genny/config.yaml`
- `~/.genny/.env`

### 4. Check Config
```bash
genny config
```

### 5. List Widgets
```bash
genny widgets
```

### 6. Test Integration
```bash
genny test github
```

### 7. Start GUI (After Fixes)
```bash
genny start
```

---

## 📋 Development Workflow

### Making Changes
```bash
# 1. Make changes in genny/
vim genny/cli.py

# 2. Changes are immediately available (editable install)
genny --help

# 3. Commit when ready
git add .
git commit -m "Description"
git push origin main
```

### Adding New Widget
```bash
# 1. Create widget file
touch genny/ui/widgets/my_new_widget.py

# 2. Implement widget class
# 3. Add to config.yaml
# 4. Test
genny widgets
genny start
```

### Running Tests (When Added)
```bash
pytest
pytest --cov=genny
```

---

## 🎯 Quick Wins (Easy Tasks)

1. **Fix imports in app.py** (~30 min)
   - Search and replace pattern
   - Test with `python -m genny.app`

2. **Create integration tests** (~20 min)
   - Copy patterns from above
   - Test with `genny test all`

3. **Test installation flow** (~10 min)
   - Fresh venv
   - Install and init
   - Document any issues

4. **Update widget __init__.py** (~15 min)
   - Make widgets easily importable
   - Export widget list

---

## 🚀 Medium Tasks (Next Week)

1. **Widget base class**
   - Standardize interface
   - Common functionality
   - Easier to develop

2. **GitHub Actions CI**
   - Run tests on push
   - Build package
   - Check code quality

3. **Docker image**
   - Test X11 forwarding
   - Document usage
   - Push to registry

4. **Enhanced documentation**
   - Widget dev guide
   - Integration guides
   - Troubleshooting

---

## 🎨 Future Enhancements (Later)

1. **Web UI** - Browser-based version
2. **Plugin system** - 3rd party widgets
3. **Auto-update** - Self-updating mechanism
4. **Multi-user** - Team dashboards
5. **Cloud deploy** - Kubernetes/ECS

---

## 💡 Tips for Development

### Use Development Install
```bash
pip install -e .
```
Changes take effect immediately (no reinstall needed)

### Test Without Installing
```bash
python -m genny.cli --help
python -m genny.app
```

### Check Package Structure
```bash
python -c "import genny; print(genny.__file__)"
python -c "from genny.ui.widgets import pods; print(pods.__file__)"
```

### Debug Import Issues
```bash
python -c "import sys; sys.path.insert(0, '.'); from genny import cli"
```

---

## 📞 Getting Help

### Run Diagnostics
```bash
genny doctor
```

### Check Logs
```bash
tail -f ~/.genny/logs/genny.log  # If we add logging
```

### Compare with Original
Original location: `/home/bobbygblair/repos/devtools-scripts/au-silver/astutl_python/au_sre/`

### Ask Genny!
Once GUI is working, Ask Genny can help debug!

---

## 🎉 Celebrate!

You've just:
- ✅ Created a proper Python package
- ✅ Set up for PyPI distribution
- ✅ Built CLI infrastructure
- ✅ Made it ready for `pip install`
- ✅ Positioned for wide adoption

**Next step:** Fix imports, test installation, and you're ready for alpha testing!
