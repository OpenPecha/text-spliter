# Tibetan Text Processing Workflow Guide

This guide explains the complete workflow for uploading Tibetan texts to Google Docs and updating Google Sheets with the generated links.

## Overview

The workflow consists of two main steps:

1. **Upload texts to Google Docs** using `upload_to_google_docs.py`
2. **Update Google Sheets with links** using `update_google_sheets.py`

⚠️ **Important**: You must run `upload_to_google_docs.py` first, as it generates the JSON mapping file that `update_google_sheets.py` requires.

## Prerequisites

### 1. Google API Setup

#### Enable Required APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - **Google Docs API**
   - **Google Drive API**
   - **Google Sheets API**

#### Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Select **Desktop application**
4. Enter name: `tibetan-text-processor`
5. Download the JSON file and save as `credentials.json` in project root

#### Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select **External** user type
3. Fill required fields:
   - App name: `Tibetan Text Processor`
   - User support email: your email
   - Developer contact: your email
4. Add scopes:
   - `https://www.googleapis.com/auth/drive`
   - `https://www.googleapis.com/auth/documents`
   - `https://www.googleapis.com/auth/spreadsheets`
5. Add your email as test user

### 2. File Structure

```
project/
├── credentials.json          # OAuth credentials (you create this)
├── src/text_spliter/
│   ├── upload_to_google_docs.py
│   └── update_google_sheets.py
│   ├── token.json                # OAuth token (created by scripts)
│   └── ...
└── data/
    ├── text/                 # Text files organized by ID
    │   ├── D2097/
    │   ├── D2098/
    │   └── ...
    └── text_list.txt          # List of all text IDs
```

## Step 1: Upload Texts to Google Docs

### Configuration

Edit `upload_to_google_docs.py`:

```python
config = {
    'credentials_path': '../../credentials.json',
    'start_id': 'D2097',     # Starting text ID
    'end_id': 'D2197',       # Ending text ID
    'delay': 1.0,            # Delay between uploads (seconds)
    'progress_file': 'upload_progress_OAuth.json'
}
```

### Key Settings:

- **start_id**: First text ID to process (e.g., 'D2097')
- **end_id**: Last text ID to process (e.g., 'D2197')
- **delay**: Delay between uploads to avoid rate limits
- **credentials_path**: Path to your OAuth credentials file

### Run the Upload

```bash
cd src/text_spliter
python3 upload_to_google_docs.py
```

### What Happens:

1. **First run**: Opens browser for OAuth authentication
2. **Creates Google Docs**: Uploads each text file as a Google Doc
3. **Stores in Drive folder**: All docs go to the specified Tengyur folder
4. **Generates mapping**: Creates `text_id_to_url_mapping.json` with text_id → Google Docs URL pairs
5. **Progress tracking**: Saves progress, can resume if interrupted

### Output Files:

- `google_docs_upload_output/text_id_to_url_mapping.json` - **Required for Step 2**
- `google_docs_upload_output/upload_progress_OAuth.json` - Progress tracking
- `google_docs_upload_output/google_docs_upload.log` - Detailed logs
- `token.json` - OAuth token (reused by Step 2)

## Step 2: Update Google Sheets

### Configuration

Edit `update_google_sheets.py`:

```python
# Google Sheet Configuration (lines 33-36)
self.GOOGLE_SHEET_ID = "YOUR_SHEET_ID_HERE"  # Replace with actual sheet ID
self.SHEET_NAME = "Sheet1"                   # Replace with actual sheet name

# Row Range Configuration
config = {
    'start_row': 2,          # Starting row (usually 2 if row 1 has headers)
    'end_row': 100,          # Ending row
    'mapping_file': 'google_docs_upload_output/text_id_to_url_mapping.json'
}
```

### Key Settings:

- **GOOGLE_SHEET_ID**: Extract from sheet URL: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
- **SHEET_NAME**: Name of the sheet tab (visible at bottom of Google Sheets)
- **start_row/end_row**: Row range to process
- **mapping_file**: Path to JSON file generated in Step 1

### Sheet Structure Expected:

- **Column J**: Contains text_ids (e.g., D2097, D2098, etc.)
- **Column L**: Where Google Docs URLs will be written

### Permissions Required:

The Google Sheet owner must share the sheet with your Google account with **Editor** permissions.

### Run the Update

```bash
cd src/text_spliter
python3 update_google_sheets.py
```

### What Happens:

1. **Reads mapping**: Loads the JSON file from Step 1
2. **Reads sheet**: Gets text_ids from column J and checks existing URLs in column L
3. **Matches and updates**: For each text_id in column J, finds corresponding URL and writes to column L
4. **Skips existing**: Won't overwrite existing URLs in column L
5. **Handles missing**: Text_ids not found in mapping are logged separately

### Output Files:

- `google_sheets_update_output/missing_text_ids.json` - Text_ids not found in mapping
- `google_sheets_update_output/google_sheets_update.log` - Detailed logs

## Complete Workflow Example

### 1. Configure Upload Script

```python
# In upload_to_google_docs.py
config = {
    'start_id': 'D2097',
    'end_id': 'D2197',
    'delay': 1.0,
}
```

### 2. Run Upload

```bash
python3 upload_to_google_docs.py
```

**Result**: 101 Google Docs created, mapping file generated

### 3. Configure Sheets Script

```python
# In update_google_sheets.py
self.GOOGLE_SHEET_ID = <Sheet ID>
self.SHEET_NAME = <Sheet Name>

config = {
    'start_row': 1005,
    'end_row': 1106,  # Covers all 101 texts
}
```

### 4. Run Sheets Update

```bash
python3 update_google_sheets.py
```

**Result**: Column L populated with Google Docs URLs

## Important Notes

### Authentication

- **First run**: `upload_to_google_docs.py` handles OAuth setup
- **Subsequent runs**: Both scripts reuse the same `token.json`
- **Token expires**: Scripts automatically refresh or re-prompt for auth

### Error Handling

- **Missing text files**: Logged and skipped
- **Upload failures**: Tracked in progress file, can resume
- **Missing mappings**: Saved to `missing_text_ids.json`
- **Sheet permission errors**: Check sharing settings

### Rate Limits

- **Upload delay**: Configurable delay between Google Docs creation
- **Batch operations**: Sheets updates use efficient batch API calls

### Resume Capability

- **Upload script**: Can resume from last successful upload
- **Sheets script**: Skips rows that already have URLs

## Troubleshooting

### Common Issues

1. **"Credentials file not found"**

   - Ensure `credentials.json` is in the correct location
   - Check the `credentials_path` in config

2. **"Permission denied" for Google Sheet**

   - Sheet owner must share with Editor permissions
   - Verify the Google Sheet ID is correct

3. **"Mapping file not found"**

   - Run `upload_to_google_docs.py` first
   - Check that `text_id_to_url_mapping.json` was generated

### File Locations

All output files are created in respective directories:

- `google_docs_upload_output/` - Upload script outputs
- `google_sheets_update_output/` - Sheets script outputs

These directories are automatically created and are included in `.gitignore`.
