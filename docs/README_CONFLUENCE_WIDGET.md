# Confluence API Configuration Widget

## Overview
Added Confluence API Key manager to the API Config widget in Auger SRE Platform.

## What Was Added

### Confluence Section Fields:
1. **Base URL** - Default: `https://cm.usa.gov/confluence`
2. **Username** - Your GSA username (e.g., `bobbygblair`)
3. **Personal Token** - Masked field for Bearer token
4. **Test Page ID** - Default: `633647209` (Data Release 1.5.4.0 deployment docs)

### Features:
- ✓ Masked token field with show/hide toggle
- ✓ Test Connection button with live verification
- ✓ Auto-saves to `.env` file
- ✓ Clickable header linking to token creation page
- ✓ Help text with token creation instructions
- ✓ Full status logging (success/error details)

### Test Connection Output:
```
Confluence: Testing connection to https://cm.usa.gov/confluence...
Confluence: ✓ Connection successful!
Confluence:   Page: ASSIST Data Release 1.5.4.0 Deployment Instructions
Confluence:   Version: 15
Confluence:   Username: bobbygblair
```

## Usage

### In the UI:
1. Open **API Config** widget from the Widgets menu
2. Scroll to **Confluence** section
3. Fill in your credentials:
   - Base URL: `https://cm.usa.gov/confluence`
   - Username: `bobbygblair`
   - Token: `REDACTED_TOKEN`
   - Test Page: `633647209` (or any page ID)
4. Click **Test Connection** to verify
5. Click **Save to .env** to persist

### Stored in .env:
```bash
CONFLUENCE_BASE_URL=https://cm.usa.gov/confluence
CONFLUENCE_USERNAME=bobbygblair
CONFLUENCE_TOKEN=REDACTED_TOKEN/HSf+q5
REDACTED_TOKEN=633647209
```

### In Python Code:
```python
import os
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv('CONFLUENCE_BASE_URL')
token = os.getenv('CONFLUENCE_TOKEN')
username = os.getenv('CONFLUENCE_USERNAME')

# Use with confluence_docs.py or directly with requests
```

## Integration with confluence_docs.py

The credentials configured in the widget can be used by `confluence_docs.py`:

```bash
# Uses CONFLUENCE_BASE_URL and CONFLUENCE_TOKEN from .env
python confluence_docs.py 633647209 --output deployment.md
```

Or programmatically:
```python
from confluence_docs import ConfluenceDocs
import os

docs = ConfluenceDocs(
    base_url=os.getenv('CONFLUENCE_BASE_URL'),
    token=os.getenv('CONFLUENCE_TOKEN')
)

page = docs.get_page('633647209')
```

## Token Creation

1. Go to: https://cm.usa.gov/confluence/admin/users/editmyprofile.action
2. Click on **Settings** or **Personal Access Tokens**
3. Create a new token with read permissions
4. Copy the token immediately (shown only once)
5. Paste into the API Config widget

## Test Page IDs

- **633647209** - ASSIST Data Release 1.5.4.0 Deployment Instructions (default)
- Or use any page ID from your Confluence instance

## Error Handling

The test connection provides detailed feedback:

| Status Code | Message |
|-------------|---------|
| 200 | ✓ Connection successful with page details |
| 401 | ✗ Authentication failed - Token invalid/expired |
| 403 | ✗ Access denied - Missing permissions |
| 404 | ✗ Page not found - Incorrect page ID |
| Timeout | ✗ Connection timeout |
| Connection Error | ✗ Could not connect to server |

## Security Notes

- Token is masked by default (show as `●●●●●`)
- Click eye icon to toggle visibility
- Stored in `.env` (excluded from git via `.gitignore`)
- Uses Bearer authentication (more secure than Basic Auth)
- HTTPS with certificate verification enabled

## Location in Code

**File**: `ui/widgets/api_config.py`

**Methods Added**:
- `REDACTED_TOKEN()` - Builds the UI section
- `_test_confluence()` - Tests connection with detailed logging

**Line Count**: Added ~85 lines to existing widget

## Visual Integration

The Confluence section matches the existing API Config widget style:
- Dark theme (#1e1e1e background)
- Teal header (#9cdcfe) with external link icon
- Green "Test Connection" button (#4ec9b0)
- Consistent spacing and layout
- Scrollable with other API sections

## Next Steps

1. ✓ Confluence section added to API Config
2. ✓ Test connection working
3. ✓ Integration with confluence_docs.py
4. Consider: Add Confluence browser widget to view pages in-app
5. Consider: Auto-fetch deployment docs in Production Release widget
6. Consider: Confluence search widget
