# Homepage Organizations Display - Fix Summary

## Problem
The homepage was showing "Internal Server Error" and the organization section was not appearing.

## Root Cause
The template override at `extensions/ckanext-assistant/ckanext/assistant/templates/home/index.html` was using `h.get_action()` which is not a valid CKAN template helper. The correct helper is `h.call_action()`, but using Jinja2 helpers in templates can cause server-side rendering issues.

## Solution
Switched to a **client-side JavaScript approach** that:

1. **Removed the problematic template override** (`home/index.html`)
2. **Added JavaScript to the existing footer.html** that already works
3. **Uses CKAN API** to fetch organization data dynamically on page load
4. **Injects the HTML** after the main hero section

## Implementation Details

### File Modified
`extensions/ckanext-assistant/ckanext/assistant/templates/footer.html`

### Key Changes
- Added conditional script that only runs on homepage (`request.path == '/'`)
- JavaScript finds `.main.hero` element (the welcome banner)
- Fetches organizations via `/api/3/action/organization_list?all_fields=true`
- Filters to organizations with `package_count > 0`
- Takes first 2 organizations
- Creates styled div with:
  - Organization title (linked to org page)
  - Package count
  - "View all organizations" button
- Inserts the div after the hero section

### Why This Works
1. ✅ Uses proven working template (footer.html loads correctly)
2. ✅ Client-side rendering avoids template helper issues
3. ✅ API call ensures fresh data
4. ✅ No server restart needed to update displayed orgs
5. ✅ Proper DOM insertion after page loads

## Verification
```bash
# Check the page loads without errors
curl -s "https://opendata.uixai.org/" | grep -i "internal server error"
# Should return empty (no error)

# Verify script is present
curl -s "https://opendata.uixai.org/" | grep -c "insertOrganizations"
# Should return 3 (function definition and calls)
```

## How to Test in Browser
1. Open https://opendata.uixai.org/
2. Scroll down below the "Welcome to CKAN" banner
3. You should see a gray box titled "数据组织" (Data Organizations)
4. It will show 2 organizations with the most datasets
5. Click "查看所有组织" to see all organizations

## Organizations Currently Displayed
Based on API data, the top 2 organizations with data are:
1. **G空間情報センター** (g-space) - 5 datasets
2. **U.S. Geological Survey** (u-s-geological-survey) - 1 dataset

## Note
The organizations are displayed **dynamically** based on current package counts. If new data is harvested to different organizations, the display will automatically update on next page load.
