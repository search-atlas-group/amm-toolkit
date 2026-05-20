# Google Sheets Integration

Export client reports, SEO summaries, and workflow results to a Google Sheet.

## How It Works

This integration uses a Google Apps Script **web app** as a lightweight webhook. Claude pushes JSON rows to the endpoint; the Apps Script appends them to the specified tab.

No OAuth flow is needed for the caller — just a single webhook URL stored in `.env`.

---

## Setup (one-time, ~5 minutes)

### Step 1 — Create the Apps Script

1. Open [script.google.com](https://script.google.com)
2. Click **New project**
3. Replace the default code with this:

```javascript
function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const ss = SpreadsheetApp.openById(body.spreadsheetId);
    const sheet = ss.getSheetByName(body.tab) || ss.insertSheet(body.tab);

    (body.rows || []).forEach(row => sheet.appendRow(row));

    return ContentService
      .createTextOutput(JSON.stringify({ status: "ok", rowsAdded: (body.rows || []).length }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

4. Click **Deploy → New deployment**
5. Type: **Web app**
6. Execute as: **Me**
7. Who has access: **Anyone** (or "Anyone with Google account" if you prefer)
8. Click **Deploy** → copy the web app URL

### Step 2 — Add the webhook to .env

```bash
GOOGLE_SHEETS_WEBHOOK=https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec
```

---

## Usage

```bash
source .env

bash integrations/google/export-to-sheet.sh \
  --sheet-id  "YOUR_SPREADSHEET_ID" \
  --tab       "SEO Report" \
  --data      '[["Client","Domain","Score","Date"],["Apple","apple.com","87","2026-04-23"]]'
```

The `--data` argument is a JSON array of rows. Each row is an array of cell values.

### Get the Spreadsheet ID

The spreadsheet ID is in the URL:
```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
```

---

## Claude Code Integration

When running `/business-report` or any workflow, Claude can export results directly:

```
"Export this report to Google Sheets"
```

Claude will call this script with the appropriate data, using the sheet ID and tab name you specify.

---

## Common Use Cases

| Use Case | Tab Name | Columns |
|----------|----------|---------|
| SEO monthly summary | `SEO Reports` | Client, Domain, Issues Fixed, Content Added, Date |
| GBP performance | `GBP Stats` | Client, Location, Views, Calls, Clicks, Period |
| Content pipeline | `Content` | Client, Title, Status, Published URL, Date |
| Client onboarding tracker | `Onboarding` | Client, Domain, Brand Vault ID, Services, Date |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_SHEETS_WEBHOOK` | Apps Script web app URL |
