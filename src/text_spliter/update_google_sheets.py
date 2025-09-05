import os
import json
import logging
from typing import Dict, List, Tuple

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
]


class GoogleSheetsUpdater:
    """Updates Google Sheets with Google Docs URLs from text_id mapping"""
    
    def __init__(self, credentials_path: str, token_path: str = "token.json"):
        """
        Initialize the Google Sheets updater
        
        Args:
            credentials_path: Path to OAuth client JSON
            token_path: Path to cached OAuth token file
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        
        # Configure as needed.
        # self.GOOGLE_SHEET_ID = "1f4fu_IKT22o5U8cmplwQsAc0CU4CRg_Nj5eprw-CDdY"
        self.GOOGLE_SHEET_ID = "1vtQ_aCDN1Y9jbwmJEE48aIgPauRvheFgYF6X1xKieMo"
        self.SHEET_NAME = "སྡེ་དགེ་བསྟན་འགྱུར་ཡར་འཇུག"
        
        # Create output directory for logs and missing IDs
        self.output_dir = "google_sheets_update_output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.setup_logging()
        self.setup_google_services()
        self.missing_text_ids = []
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_file_path = os.path.join(self.output_dir, 'google_sheets_update.log')
        
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        
        # File handler
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_formatter = logging.Formatter('🔍 %(asctime)s | %(levelname)s\n📝 %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        
        # Configure logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.propagate = False
        
        self.logger.info(f"📁 Log file created at: {log_file_path}")
        
    def setup_google_services(self):
        """Initialize Google Sheets API service via OAuth"""
        creds = None
        
        # Reuse token if present
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        # If no valid creds, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        self.sheets_service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
        self.logger.info("🚀 Google Sheets API service initialized successfully")
        
    def load_url_mapping(self, mapping_file: str = "google_docs_upload_output/text_id_to_url_mapping.json") -> Dict[str, str]:
        """Load text_id to URL mapping from JSON file"""
        if not os.path.exists(mapping_file):
            self.logger.error(f"❌ Mapping file not found: {mapping_file}")
            return {}
            
        try:
            with open(mapping_file, 'r') as f:
                mapping = json.load(f)
            self.logger.info(f"📖 Loaded {len(mapping)} URL mappings from {mapping_file}")
            return mapping
        except Exception as e:
            self.logger.error(f"❌ Failed to load mapping file: {e}")
            return {}
            
    def read_sheet_range(self, start_row: int, end_row: int) -> Tuple[List[str], List[str]]:
        """
        Read text_ids from column J and existing URLs from column L for specified row range
        
        Returns:
            Tuple of (text_ids_list, existing_urls_list)
        """
        try:
            # Read columns J and L for the specified range
            range_name = f"{self.SHEET_NAME}!J{start_row}:L{end_row}"
            
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.GOOGLE_SHEET_ID,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            text_ids = []
            existing_urls = []
            
            for row in values:
                # Column J (text_id)
                text_id = row[0] if len(row) > 0 else ""
                text_ids.append(text_id)
                
                # Column L (existing URL) - skip column K, get column L
                existing_url = row[2] if len(row) > 2 else ""
                existing_urls.append(existing_url)
                
            self.logger.info(f"📊 Read {len(text_ids)} rows from range {range_name}")
            return text_ids, existing_urls
            
        except HttpError as e:
            self.logger.error(f"❌ Failed to read sheet range: {e}")
            return [], []
            
    def update_sheet_urls(self, start_row: int, urls_to_update: List[Tuple[int, str]]):
        """
        Update column L with URLs for specified rows
        
        Args:
            start_row: Starting row number
            urls_to_update: List of (row_offset, url) tuples
        """
        if not urls_to_update:
            self.logger.info("No URLs to update")
            return
            
        try:
            # Prepare batch update data
            data = []
            for row_offset, url in urls_to_update:
                actual_row = start_row + row_offset
                data.append({
                    'range': f"{self.SHEET_NAME}!L{actual_row}",
                    'values': [[url]]
                })
            
            # Batch update
            body = {
                'valueInputOption': 'RAW',
                'data': data
            }
            
            result = self.sheets_service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.GOOGLE_SHEET_ID,
                body=body
            ).execute()
            
            updated_cells = result.get('totalUpdatedCells', 0)
            self.logger.info(f"✅ Successfully updated {updated_cells} cells in column L")
            
        except HttpError as e:
            self.logger.error(f"❌ Failed to update sheet: {e}")
            
    def save_missing_text_ids(self):
        """Save missing text_ids to a JSON file"""
        if not self.missing_text_ids:
            self.logger.info("No missing text_ids to save")
            return
            
        missing_file = os.path.join(self.output_dir, "missing_text_ids.json")
        try:
            with open(missing_file, 'w') as f:
                json.dump(self.missing_text_ids, f, indent=2)
            self.logger.info(f"📄 Missing text_ids saved to {missing_file} ({len(self.missing_text_ids)} entries)")
        except Exception as e:
            self.logger.error(f"❌ Failed to save missing text_ids: {e}")
            
    def update_sheet_range(self, start_row: int, end_row: int, mapping_file: str = "google_docs_upload_output/text_id_to_url_mapping.json"):
        """
        Update Google Sheet with URLs for specified row range
        
        Args:
            start_row: Starting row number (1-based)
            end_row: Ending row number (1-based)
            mapping_file: Path to the text_id to URL mapping JSON file
        """
        self.logger.info(f"🚀 Starting Google Sheets update for rows {start_row} to {end_row}")
        
        # Load URL mapping
        url_mapping = self.load_url_mapping(mapping_file)
        if not url_mapping:
            self.logger.error("❌ No URL mapping available. Cannot proceed.")
            return
            
        # Read current sheet data
        text_ids, existing_urls = self.read_sheet_range(start_row, end_row)
        
        if not text_ids:
            self.logger.error("❌ No data found in specified range")
            return
            
        # Process each row
        urls_to_update = []
        skipped_existing = 0
        missing_count = 0
        
        for i, (text_id, existing_url) in enumerate(zip(text_ids, existing_urls)):
            if not text_id.strip():
                continue  # Skip empty text_ids
                
            # Skip if column L already has a URL
            if existing_url.strip():
                skipped_existing += 1
                self.logger.info(f"⏭️  Row {start_row + i}: Skipping {text_id} - already has URL")
                continue
                
            # Check if text_id exists in our mapping
            if text_id in url_mapping:
                url = url_mapping[text_id]
                urls_to_update.append((i, url))
                self.logger.info(f"✅ Row {start_row + i}: {text_id} → URL found")
            else:
                self.missing_text_ids.append(text_id)
                missing_count += 1
                self.logger.warning(f"⚠️  Row {start_row + i}: {text_id} → URL not found in mapping")
        
        # Update the sheet
        self.update_sheet_urls(start_row, urls_to_update)
        
        # Save missing text_ids
        self.save_missing_text_ids()
        
        self.logger.info("✅ Google Sheets update completed!")
        self.logger.info(f"📈 Summary:")
        self.logger.info(f"   Total rows processed: {len(text_ids)}")
        self.logger.info(f"   URLs updated: {len(urls_to_update)}")
        self.logger.info(f"   Skipped (already had URLs): {skipped_existing}")
        self.logger.info(f"   Missing from mapping: {missing_count}")


def get_update_config():
    """Configuration settings - modify these as needed"""
    config = {
        'credentials_path': '../../credentials.json',
        'start_row': 1005,
        'end_row': 1006,
        'mapping_file': 'google_docs_upload_output/text_id_to_url_mapping.json' # this file is created by upload_to_google_docs.py (Contains Mapping of text_id to URL)
    }
    
    if not os.path.exists(config['credentials_path']):
        print(f"❌ Error: Credentials file not found: {config['credentials_path']}")
        return None
    
    print("=" * 60)
    print("🔥 GOOGLE SHEETS URL UPDATER 🔥")
    print("=" * 60)
    print("\n📋 UPDATE CONFIGURATION:")
    print(f"   Credentials: {config['credentials_path']}")
    print(f"   Row range: {config['start_row']} to {config['end_row']}")
    print(f"   Mapping file: {config['mapping_file']}")
    print("\n🚀 Starting update...")
    
    return config


def main():
    """Main function"""
    try:
        config = get_update_config()
        if not config:
            return
        
        print("\n🔄 Initializing sheets updater...")
        updater = GoogleSheetsUpdater(config['credentials_path'])
        
        updater.update_sheet_range(
            start_row=config['start_row'],
            end_row=config['end_row'],
            mapping_file=config['mapping_file']
        )
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Update interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
