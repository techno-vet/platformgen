# Production Release Widget - Confluence Integration

## Overview
Enhanced the Production Release widget with automatic deployment document loading from Confluence. The Configure tab now features a two-column layout with document preview and auto-population of all deployment fields.

## New Features

### 1. Two-Column Layout
**Left Column (60%)** - Deployment Form
- Confluence URL input field
- "Load & Parse Document" button
- All deployment metadata fields
- Save/Clear buttons

**Right Column (40%)** - Document Viewer
- Live preview of Confluence document
- Markdown-style rendering
- Scrollable text display
- Styled headers, code blocks, links

### 2. Confluence Document Loading
**URL Input Field:**
- Accepts full Confluence page URLs
- Example: `https://cm.usa.gov/confluence/spaces/ACP/pages/633647209/`
- Automatically extracts page ID from URL

**Load & Parse Button:**
- Fetches document from Confluence using Bearer token auth
- Parses HTML content with BeautifulSoup
- Extracts structured data from tables
- Auto-populates all form fields
- Displays document in viewer

### 3. Auto-Population Features

#### Metadata Extraction:
- **Change Number** - Extracted from title (e.g., CHG0159376)
- **Jira Story** - Extracted from Jira links (e.g., ASSIST3-37047)
- **Release Name** - Parsed from title (e.g., "Data 1.5.4.0")
- **Release Branch** - Generated from release name (e.g., "release/DATA_1.5.4.0_DME")
- **Engineer** - Pre-filled with current user
- **Deployment Date** - Pre-filled with today's date
- **Status** - Default to "in_progress"

#### Services Table Parsing:
Automatically extracts from Confluence application tables:
- Service name
- Repository and branch
- Current image tag (if known)
- New image tag
- Special handling (undeploy/redeploy)
- File path (auto-detected from service name)

Populates **Services tab** with all extracted data!

### 4. Document Viewer

**Styled Text Display:**
- Headers (H1, H2, H3) in teal accent colors
- Bold text highlighting
- Code blocks with monospace font
- Links in blue with underline
- Success/Error color tags
- Dark theme matching platform

**Features:**
- Scrollable content
- Read-only display
- Markdown-like rendering
- Shows document title and version

## Usage

### Step-by-Step:
1. Open **Production Release** widget
2. Go to **Configure** tab
3. Enter Confluence URL in the top field:
   ```
   https://cm.usa.gov/confluence/spaces/ACP/pages/633647209/ASSIST+Data+Release+1.5.4.0+Deployment+Instructions
   ```
4. Click **"Load & Parse Document"**
5. Watch as:
   - Document loads in right panel
   - Form fields auto-populate
   - Services appear in Services tab
6. Review and adjust fields as needed
7. Click **"Save Deployment"**

### Prerequisites:
- Confluence token configured in API Config widget
- Token must be saved to `.env` file
- User must have read access to the document

### What Gets Auto-Populated:

**Configure Tab:**
- Change Number
- Jira Story
- Release Name
- Release Branch

**Services Tab:**
- Service Name
- File Path (flux config)
- New Image Tag
- Special Handling flags

## Technical Details

### URL Parsing:
```python
# Extracts page ID from various URL formats:
https://cm.usa.gov/confluence/spaces/ACP/pages/633647209/...
https://cm.usa.gov/confluence/display/ACP/...pages=633647209

# Regex: r'/pages/(\d+)'
```

### Confluence API Call:
```python
# Endpoint
GET /rest/api/content/{page_id}?expand=body.storage,version

# Headers
Authorization: Bearer {token}
Accept: application/json

# Returns
{
  "title": "ASSIST Data Release 1.5.4.0...",
  "body": {"storage": {"value": "<html>..."}},
  "version": {"number": 15}
}
```

### HTML Parsing:
```python
from bs4 import BeautifulSoup
import html2text

# Convert HTML to Markdown for display
h = html2text.HTML2Text()
h.body_width = 0
markdown = h.handle(html_content)

# Parse HTML for data extraction
soup = BeautifulSoup(html_content, 'html.parser')
tables = soup.find_all('table')
jira_links = soup.find_all('a', href=re.compile(r'cm-jira\.usa\.gov'))
```

### Service Path Detection:
```python
# Intelligently maps service names to flux config paths
service_paths = {
    'Data Pipeline': 'core/production/data-pipeline/utils/data-pipeline.yaml',
    'Data API Service': 'core/production/data-api/utils/data-api-service.yaml',
    'Data-Utils': 'core/production/data-utils/utils/data-utils.yaml',
    'Data-Catalogs': 'core/production/data-catalog/utils/data-catalog.yaml',
    'Airflow': 'core/production/data-pipeline/utils/airflow.yaml',
}
```

## Error Handling

### Clear User Feedback:
- **No URL**: Warning dialog
- **Invalid URL**: Error with expected format
- **No Token**: Prompt to open API Config
- **401 (Auth Failed)**: Check token message
- **403 (Access Denied)**: Permission error
- **404 (Not Found)**: Invalid page ID
- **Timeout**: Connection timeout message
- **Connection Error**: Cannot reach server

### Status Bar Updates:
```
Loading page 633647209 from Confluence...
Loaded: ASSIST Data Release 1.5.4.0 Deployment Instructions (v15)
```

## Example Parsed Data

### From This URL:
`https://cm.usa.gov/confluence/spaces/ACP/pages/633647209/`

### Extracted:
**Metadata:**
- Title: "ASSIST Data Release 1.5.4.0 Deployment Instructions"
- Jira Story: "ASSIST3-37047"
- Release: "Data 1.5.4.0"
- Branch: "release/DATA_1.5.4.0_DME"

**Services (5):**
1. Data Pipeline - `release-DATA_1.5.4.0_DME-BUILD2-e00bb44-1771615873573`
2. Data API Service - `release-DATA_1.5.4.0_DME-BUILD3-82f4c45-1771948597950`
3. Data-Utils - `release-DATA_1.5.4.0_DME-BUILD3-e093993-1771856890543`
4. Data-Catalogs - `release-DATA_1.5.4.0_DME-BUILD7-9d74e51-1771867538289`
5. Airflow - `release-DATA_1.5.4.0_DME-BUILD1-31ee670-1771953683809`

## Files Modified

**ui/widgets/production_release.py** - Added ~280 lines (now 1,160 total)

**New Methods:**
- `_load_from_confluence()` - Fetches and coordinates parsing
- `_parse_deployment_doc()` - Extracts metadata and displays
- `_parse_services_table()` - Parses HTML tables for services
- `_guess_file_path()` - Maps service names to flux paths
- `_update_doc_viewer()` - Updates document preview

**Modified Methods:**
- `_create_config_tab()` - Restructured to two-column layout

**New Instance Variables:**
- `self.confluence_url_var` - URL input field
- `self.doc_viewer` - Text widget for document display

## Benefits

1. **Saves Time** - No more manual copying from Confluence
2. **Reduces Errors** - Automated data extraction
3. **Better Context** - See source document while working
4. **Consistency** - Standardized data format
5. **Efficiency** - One click to populate entire deployment

## Demo Workflow

```
1. Paste URL: https://cm.usa.gov/confluence/.../pages/633647209/
2. Click "Load & Parse Document"
3. ✓ Document appears in right panel
4. ✓ Change Number: CHG0159376
5. ✓ Jira Story: ASSIST3-37047  
6. ✓ Release: Data 1.5.4.0
7. ✓ Branch: release/DATA_1.5.4.0_DME
8. Switch to Services tab
9. ✓ 5 services pre-loaded with image tags
10. Review and save!
```

## Future Enhancements

- [ ] Auto-detect PR numbers from document
- [ ] Parse DAG deployment steps
- [ ] Extract post-deployment verification checklist
- [ ] Support for multiple document formats
- [ ] Search Confluence from within widget
- [ ] Template-based document creation
- [ ] Export deployment report back to Confluence

## Dependencies

**Already Installed:**
- `requests` - HTTP requests to Confluence API
- `beautifulsoup4` - HTML parsing
- `html2text` - HTML to Markdown conversion
- `python-dotenv` - Environment variable loading

**From .env:**
- `CONFLUENCE_BASE_URL` - Confluence server URL
- `CONFLUENCE_TOKEN` - Bearer token for authentication
- `CONFLUENCE_USERNAME` - (optional) For display purposes

## Integration Points

1. **API Config Widget** - Token management
2. **confluence_docs.py** - Shared Confluence utilities
3. **Services Tab** - Populated with parsed data
4. **PRs Tab** - Ready for future PR extraction
5. **SQLite Database** - All data persists

---

**Status**: ✅ Complete and functional
**Added**: February 27, 2026
**Widget**: Production Release Manager
**Impact**: Major workflow improvement for production deployments
