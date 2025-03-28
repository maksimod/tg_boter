from typing import List, Any, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account

class GoogleSheets:
    """A class to handle Google Sheets operations."""
    
    def __init__(self, credentials_path: str):
        """
        Initialize Google Sheets client.
        
        Args:
            credentials_path: Path to the service account credentials JSON file
        """
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        self.service = build('sheets', 'v4', credentials=self.credentials)
        self.sheets = self.service.spreadsheets()
    
    def read_range(
        self,
        spreadsheet_id: str,
        range_name: str
    ) -> List[List[Any]]:
        """
        Read data from a specific range in the spreadsheet.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The range to read (e.g., 'Sheet1!A1:B10')
            
        Returns:
            List of lists containing the data
        """
        result = self.sheets.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        return result.get('values', [])
    
    def write_range(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]]
    ) -> None:
        """
        Write data to a specific range in the spreadsheet.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The range to write to (e.g., 'Sheet1!A1:B10')
            values: List of lists containing the data to write
        """
        body = {
            'values': values
        }
        
        self.sheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
    
    def append_row(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[Any]
    ) -> None:
        """
        Append a row to the spreadsheet.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The range to append to (e.g., 'Sheet1')
            values: List containing the values for the new row
        """
        body = {
            'values': [values]
        }
        
        self.sheets.values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

# Example usage:
"""
sheets = GoogleSheets('credentials/google/credentials.json')

# Read data
data = sheets.read_range(
    'your-spreadsheet-id',
    'Sheet1!A1:B10'
)

# Write data
sheets.write_range(
    'your-spreadsheet-id',
    'Sheet1!A1:B2',
    [['Name', 'Age'], ['John', '25']]
)

# Append a row
sheets.append_row(
    'your-spreadsheet-id',
    'Sheet1',
    ['Jane', '30']
)
""" 