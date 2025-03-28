import os
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import io

class GoogleDrive:
    """A class to handle Google Drive operations."""
    
    def __init__(self, credentials_path: str):
        """
        Initialize Google Drive client.
        
        Args:
            credentials_path: Path to the service account credentials JSON file
        """
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        self.service = build('drive', 'v3', credentials=self.credentials)
    
    def download_file(
        self,
        file_id: str,
        save_path: Optional[str] = None
    ) -> bytes:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: The ID of the file to download
            save_path: Optional path to save the file locally
            
        Returns:
            The file contents as bytes
        """
        request = self.service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        
        while done is False:
            status, done = downloader.next_chunk()
        
        file.seek(0)
        file_contents = file.read()
        
        if save_path:
            with open(save_path, 'wb') as f:
                f.write(file_contents)
        
        return file_contents
    
    def get_file_metadata(self, file_id: str) -> dict:
        """
        Get metadata for a file.
        
        Args:
            file_id: The ID of the file
            
        Returns:
            Dictionary containing file metadata
        """
        return self.service.files().get(
            fileId=file_id,
            fields='id,name,mimeType,size,createdTime,modifiedTime'
        ).execute()
    
    def list_files(
        self,
        folder_id: Optional[str] = None,
        query: Optional[str] = None
    ) -> list:
        """
        List files in a folder or matching a query.
        
        Args:
            folder_id: Optional folder ID to list files from
            query: Optional search query
            
        Returns:
            List of file metadata dictionaries
        """
        if folder_id:
            query = f"'{folder_id}' in parents"
        elif not query:
            query = "trashed = false"
        
        results = self.service.files().list(
            q=query,
            fields='files(id, name, mimeType, size, createdTime, modifiedTime)'
        ).execute()
        
        return results.get('files', [])

# Example usage:
"""
drive = GoogleDrive('credentials/google/credentials.json')

# Download a file
file_contents = drive.download_file(
    'your-file-id',
    save_path='downloaded_file.pdf'
)

# Get file metadata
metadata = drive.get_file_metadata('your-file-id')
print(f"File name: {metadata['name']}")
print(f"File size: {metadata['size']} bytes")

# List files in a folder
files = drive.list_files(folder_id='your-folder-id')
for file in files:
    print(f"File: {file['name']} (ID: {file['id']})")

# Search for files
search_results = drive.list_files(query="name contains 'report'")
for file in search_results:
    print(f"Found: {file['name']}")
""" 