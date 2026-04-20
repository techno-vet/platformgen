# Confluence API Access

## Overview
Your Confluence personal access token **works** and can programmatically access deployment documentation.

## Authentication Details
- **Confluence URL**: https://cm.usa.gov/confluence
- **Username**: bobbygblair
- **Token**: REDACTED_TOKEN/HSf+q5
- **Auth Method**: Bearer token (not Basic Auth)
- **Page ID**: 633647209 (ASSIST Data Release 1.5.4.0)

## Test Results
✓ **Status Code**: 200 (Success)
✓ **Page Title**: ASSIST Data Release 1.5.4.0 Deployment Instructions
✓ **Version**: 15
✓ **Content Length**: 19,143 characters
✓ **Access Level**: Full read access (page requires authentication)

## Usage

### Python Script: `confluence_docs.py`
A utility to fetch and convert Confluence pages to Markdown.

**Basic Usage:**
```bash
# Display page in terminal
python confluence_docs.py 633647209

# Save to file as Markdown
python confluence_docs.py 633647209 --output deployment.md

# Save as HTML
python confluence_docs.py 633647209 --output deployment.html --format html

# Use different token
python confluence_docs.py 633647209 --token YOUR_TOKEN
```

### Python Code Example:
```python
import requests

base_url = "https://cm.usa.gov/confluence"
token = "REDACTED_TOKEN/HSf+q5"
page_id = "633647209"

url = f"{base_url}/rest/api/content/{page_id}?expand=body.storage,version"
headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {token}"
}

response = requests.get(url, headers=headers, verify=True)

if response.status_code == 200:
    data = response.json()
    title = data['title']
    content = data['body']['storage']['value']
    print(f"Title: {title}")
    print(f"Content length: {len(content)} chars")
```

### curl Example:
```bash
curl -X GET \
  "https://cm.usa.gov/confluence/rest/api/content/633647209?expand=body.storage" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer REDACTED_TOKEN/HSf+q5"
```

## API Endpoints

### REST API v1 (Works ✓)
- Base: `https://cm.usa.gov/confluence/rest/api`
- Get page: `/content/{pageId}?expand=body.storage,version`
- Get children: `/content/{pageId}/child/page`
- Search: `/content/search?cql={query}`

### REST API v2 (Works ✓)
- Base: `https://cm.usa.gov/confluence/api/v2`
- Get page: `/pages/{pageId}?body-format=storage`

## Integration Ideas

### 1. Deployment Documentation Widget
Fetch deployment docs directly in the Auger SRE Platform:
- Auto-load latest deployment instructions
- Parse steps and PRs from Confluence
- Track completion status

### 2. Automated Pre-Deployment Checks
- Fetch deployment checklist from Confluence
- Verify all prerequisites before starting
- Generate deployment plan from docs

### 3. Release Notes Generator
- Extract version history from Confluence
- Auto-generate release summaries
- Cross-reference with GitHub PRs

### 4. Documentation Sync
- Keep local deployment guides in sync
- Pull updates automatically
- Offline access to critical docs

## ConfluenceDocs Class

The `confluence_docs.py` script includes a reusable class:

```python
from confluence_docs import ConfluenceDocs

docs = ConfluenceDocs(
    base_url="https://cm.usa.gov/confluence",
    token="YOUR_TOKEN"
)

# Fetch page
page = docs.get_page("633647209")

# Get children
children = docs.get_page_children("633647209")

# Save as Markdown
docs.save_page("633647209", "output.md", format='markdown')

# Display in terminal
docs.display_page("633647209")
```

## Dependencies
```bash
pip install requests beautifulsoup4 html2text
```

## Security Notes
- Token is stored in code (consider using environment variables)
- Token has read-only access to pages user can access
- Uses HTTPS with certificate verification
- Consider rotating tokens periodically

## Example Output
Successfully downloaded:
- **File**: `data/REDACTED_TOKEN.5.4.0_Deployment.md`
- **Size**: ~500+ lines of Markdown
- **Includes**: Full deployment steps, PRs, commands, notes

## Next Steps
1. ✓ Token verified and working
2. ✓ Created `confluence_docs.py` utility
3. ✓ Downloaded deployment documentation
4. Consider: Add Confluence widget to Auger SRE Platform
5. Consider: Auto-sync deployment docs before each release
