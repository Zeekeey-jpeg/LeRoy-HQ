---
name: google-apps-script
description: |
  Stack B: Google Apps Script + Drive for internal/lightweight tools.

  Use when building:
  - Internal tools (intranet, TaskHub)
  - your organization Security internal systems
  - Clients deep in Google Workspace
  - Quick prototypes / MVPs
  - Budget-conscious deployments
  - No external user auth required

  Includes: HTML Service, Sheets as DB, Drive storage, Triggers.
---

# Stack B: Google Apps Script + Drive

## When to Use
- Internal tools (intranet, TaskHub)
- your organization Security internal systems
- Clients deep in Google Workspace
- Quick prototypes / MVPs
- Budget-conscious deployments
- No external user auth required

## Architecture

```
           GOOGLE APPS SCRIPT + DRIVE
  Frontend    | Apps Script Web App (HTML)
  Auth        | Google Workspace (automatic)
  Database    | Google Sheets (as data store)
  Storage     | Google Drive
  Automation  | Apps Script triggers
  Integration | Native Google APIs
```

## Key Patterns

### Web App Structure
```javascript
// Code.gs - Server-side
function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('My App')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function getData() {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName('Data');
  const data = sheet.getDataRange().getValues();
  return data;
}
```

### HTML Service
```html
<!-- index.html -->
<!DOCTYPE html>
<html>
  <head>
    <base target="_top">
    <?!= include('styles'); ?>
  </head>
  <body>
    <div id="app"></div>
    <?!= include('script'); ?>
  </body>
</html>
```

### Sheets as Database
```javascript
// Read all data
function getAllRecords() {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName('Products');
  const data = sheet.getDataRange().getValues();
  const headers = data.shift();

  return data.map(row => {
    const obj = {};
    headers.forEach((header, i) => obj[header] = row[i]);
    return obj;
  });
}

// Add record
function addRecord(record) {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName('Products');
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const row = headers.map(header => record[header] || '');
  sheet.appendRow(row);
}

// Update record
function updateRecord(id, updates) {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName('Products');
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  const idCol = headers.indexOf('id');

  for (let i = 1; i < data.length; i++) {
    if (data[i][idCol] === id) {
      Object.keys(updates).forEach(key => {
        const col = headers.indexOf(key);
        if (col > -1) sheet.getRange(i + 1, col + 1).setValue(updates[key]);
      });
      break;
    }
  }
}
```

### External API Calls
```javascript
function fetchExternalData(url) {
  const options = {
    method: 'GET',
    headers: {
      'Authorization': 'Bearer ' + PropertiesService.getScriptProperties().getProperty('API_KEY')
    },
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  return JSON.parse(response.getContentText());
}
```

### Triggers
```javascript
// Time-based trigger (runs daily)
function createDailyTrigger() {
  ScriptApp.newTrigger('dailySync')
    .timeBased()
    .everyDays(1)
    .atHour(6)
    .create();
}

// Form submit trigger
function onFormSubmit(e) {
  const responses = e.values;
  // Process form submission
}
```

### Properties Service (Config/Secrets)
```javascript
// Store secret
PropertiesService.getScriptProperties().setProperty('API_KEY', 'xxx');

// Retrieve secret
const apiKey = PropertiesService.getScriptProperties().getProperty('API_KEY');
```

### Drive Integration
```javascript
// Create file
function createFile(name, content, folderId) {
  const folder = DriveApp.getFolderById(folderId);
  return folder.createFile(name, content, MimeType.PLAIN_TEXT);
}

// Read file
function readFile(fileId) {
  return DriveApp.getFileById(fileId).getBlob().getDataAsString();
}
```

## Deployment

1. Open Script Editor (script.google.com)
2. Deploy > New deployment
3. Select "Web app"
4. Execute as: Me
5. Who has access: Anyone with Google account
6. Deploy

## Quotas & Limits

| Resource | Limit |
|----------|-------|
| URL Fetch calls | 20,000/day |
| Script runtime | 6 min (consumer) / 30 min (Workspace) |
| Triggers | 20 per user per script |
| Properties | 500KB total |

## Example Projects
- your organization TaskHub (intranet)
- Internal dashboards
- Google Workspace automation
- Client tools within their domain
