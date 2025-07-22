"""
Google Docs Integration Module
Handles creation and updating of Google Docs for NotebookLM workflows
"""

import os
import json
import logging
from typing import Optional, List, Dict
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import Config
from .utils import chunk_text, convert_markdown_to_docs_format

class GoogleDocsIntegrator:
    """Integration with Google Docs API for NotebookLM workflows."""
    
    # Scopes required for Google Docs operations
    SCOPES = [
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.service = None
        self.drive_service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google APIs."""
        creds = None
        
        # Check for existing token
        token_path = Path('token.json')
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
            except Exception as e:
                self.logger.warning(f"Failed to load existing token: {e}")
        
        # If there are no valid credentials, request authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.warning(f"Failed to refresh token: {e}")
                    creds = None
            
            if not creds:
                # Check for credentials file
                credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
                if not os.path.exists(credentials_file):
                    raise FileNotFoundError(
                        f"Google credentials file not found at {credentials_file}. "
                        "Please download it from Google Cloud Console and place it in the project root, "
                        "or set the GOOGLE_CREDENTIALS_FILE environment variable."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open('token.json', 'w') as token_file:
                token_file.write(creds.to_json())
        
        # Build the services
        self.service = build('docs', 'v1', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)
        
        self.logger.info("Google Docs authentication successful")
    
    def create_document(self, title: str, content: str) -> str:
        """Create a new Google Document with the specified content."""
        try:
            # Create the document
            document = {
                'title': title
            }
            
            doc = self.service.documents().create(body=document).execute()
            document_id = doc.get('documentId')
            
            self.logger.info(f"Created Google Doc with ID: {document_id}")
            
            # Add content to the document
            self._insert_content(document_id, content)
            
            return document_id
            
        except HttpError as e:
            self.logger.error(f"Google Docs API error: {e}")
            raise Exception(f"Failed to create Google Doc: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error creating document: {e}")
            raise
    
    def update_document(self, document_id: str, content: str, append: bool = False):
        """Update an existing Google Document with new content."""
        try:
            if not append:
                # Clear existing content first
                self._clear_document(document_id)
            
            # Insert new content
            self._insert_content(document_id, content)
            
            self.logger.info(f"Updated Google Doc: {document_id}")
            
        except HttpError as e:
            self.logger.error(f"Google Docs API error: {e}")
            raise Exception(f"Failed to update Google Doc: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error updating document: {e}")
            raise
    
    def _clear_document(self, document_id: str):
        """Clear all content from a document."""
        try:
            # Get document to find the content length
            document = self.service.documents().get(documentId=document_id).execute()
            content = document.get('body', {}).get('content', [])
            
            if not content:
                return
            
            # Calculate total content length
            total_length = 0
            for element in content:
                if 'paragraph' in element:
                    for text_element in element['paragraph']['elements']:
                        if 'textRun' in text_element:
                            total_length += len(text_element['textRun']['content'])
            
            if total_length > 1:  # Keep at least one character for insertion point
                # Delete all content except the last character
                requests = [{
                    'deleteContentRange': {
                        'range': {
                            'startIndex': 1,
                            'endIndex': total_length
                        }
                    }
                }]
                
                self.service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': requests}
                ).execute()
                
        except Exception as e:
            self.logger.warning(f"Failed to clear document content: {e}")
    
    def _insert_content(self, document_id: str, content: str):
        """Insert content into a Google Document."""
        try:
            # Convert markdown to Google Docs format
            formatted_requests = convert_markdown_to_docs_format(content)
            
            if not formatted_requests:
                # Fallback to plain text insertion
                requests = [{
                    'insertText': {
                        'location': {'index': 1},
                        'text': content
                    }
                }]
            else:
                requests = formatted_requests
            
            # Google Docs API has limits on request size, so chunk large requests
            chunk_size = 100  # Maximum requests per batch
            for i in range(0, len(requests), chunk_size):
                chunk = requests[i:i + chunk_size]
                
                self.service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': chunk}
                ).execute()
                
                self.logger.debug(f"Inserted content chunk {i//chunk_size + 1}")
            
        except Exception as e:
            self.logger.error(f"Failed to insert content: {e}")
            # Fallback to simple text insertion
            try:
                simple_requests = [{
                    'insertText': {
                        'location': {'index': 1},
                        'text': content[:1000000]  # Limit to 1MB
                    }
                }]
                
                self.service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': simple_requests}
                ).execute()
                
            except Exception as fallback_error:
                self.logger.error(f"Fallback content insertion failed: {fallback_error}")
                raise
    
    def get_document_content(self, document_id: str) -> str:
        """Retrieve content from an existing Google Document."""
        try:
            document = self.service.documents().get(documentId=document_id).execute()
            
            content_parts = []
            body = document.get('body', {})
            
            for element in body.get('content', []):
                if 'paragraph' in element:
                    paragraph_text = []
                    for text_element in element['paragraph']['elements']:
                        if 'textRun' in text_element:
                            paragraph_text.append(text_element['textRun']['content'])
                    content_parts.append(''.join(paragraph_text))
            
            return '\n'.join(content_parts)
            
        except HttpError as e:
            self.logger.error(f"Failed to get document content: {e}")
            raise Exception(f"Failed to retrieve document: {e}")
    
    def share_document(self, document_id: str, email: str = None, make_public: bool = False):
        """Share a Google Document."""
        try:
            if make_public:
                # Make document public (view only)
                permission = {
                    'type': 'anyone',
                    'role': 'reader'
                }
                self.drive_service.permissions().create(
                    fileId=document_id,
                    body=permission
                ).execute()
                
                self.logger.info(f"Document {document_id} made publicly accessible")
                
            elif email:
                # Share with specific email
                permission = {
                    'type': 'user',
                    'role': 'reader',
                    'emailAddress': email
                }
                self.drive_service.permissions().create(
                    fileId=document_id,
                    body=permission,
                    sendNotificationEmail=True
                ).execute()
                
                self.logger.info(f"Document {document_id} shared with {email}")
                
        except HttpError as e:
            self.logger.error(f"Failed to share document: {e}")
            raise Exception(f"Failed to share document: {e}")
    
    def create_from_multiple_sources(self, title: str, sources: List[Dict]) -> str:
        """Create a document from multiple content sources."""
        try:
            # Create the main document
            document_id = self.create_document(title, "")
            
            # Prepare combined content
            combined_content = []
            combined_content.append(f"# {title}")
            combined_content.append("")
            combined_content.append(f"*Generated on: {self._get_timestamp()}*")
            combined_content.append("")
            
            # Add table of contents
            combined_content.append("## Table of Contents")
            combined_content.append("")
            for i, source in enumerate(sources, 1):
                source_title = source.get('title', f"Source {i}")
                combined_content.append(f"{i}. [{source_title}](#{self._create_anchor(source_title)})")
            combined_content.append("")
            combined_content.append("---")
            combined_content.append("")
            
            # Add each source
            for i, source in enumerate(sources, 1):
                source_title = source.get('title', f"Source {i}")
                source_url = source.get('url', '')
                source_content = source.get('content', '')
                
                combined_content.append(f"## {i}. {source_title}")
                combined_content.append("")
                if source_url:
                    combined_content.append(f"*Source: {source_url}*")
                    combined_content.append("")
                combined_content.append(source_content)
                combined_content.append("")
                combined_content.append("---")
                combined_content.append("")
            
            # Update the document with combined content
            final_content = "\n".join(combined_content)
            self._clear_document(document_id)
            self._insert_content(document_id, final_content)
            
            return document_id
            
        except Exception as e:
            self.logger.error(f"Failed to create document from multiple sources: {e}")
            raise
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for document metadata."""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _create_anchor(self, text: str) -> str:
        """Create URL anchor from text."""
        import re
        return re.sub(r'[^a-zA-Z0-9-]', '-', text.lower()).strip('-')
    
    def list_user_documents(self, query: str = None) -> List[Dict]:
        """List user's Google Documents."""
        try:
            # Search for documents
            search_query = "mimeType='application/vnd.google-apps.document'"
            if query:
                search_query += f" and name contains '{query}'"
            
            results = self.drive_service.files().list(
                q=search_query,
                spaces='drive',
                fields='files(id, name, createdTime, modifiedTime)',
                orderBy='modifiedTime desc'
            ).execute()
            
            documents = results.get('files', [])
            return documents
            
        except HttpError as e:
            self.logger.error(f"Failed to list documents: {e}")
            return []
    
    def get_document_url(self, document_id: str) -> str:
        """Get the shareable URL for a Google Document."""
        return f"https://docs.google.com/document/d/{document_id}/edit"
    
    def validate_document_access(self, document_id: str) -> bool:
        """Validate that we can access a specific document."""
        try:
            self.service.documents().get(documentId=document_id).execute()
            return True
        except:
            return False
