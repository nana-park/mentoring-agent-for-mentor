from mentoring.config import GOOGLE_TOKEN_FILE, GOOGLE_CREDENTIALS_FILE
import os
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/documents.readonly'
]

class GoogleWorkspaceClient:
    def __init__(self):
        self.creds = None
        self._authenticate()

    def _authenticate(self):
        token_path = GOOGLE_TOKEN_FILE
        creds_path = GOOGLE_CREDENTIALS_FILE

        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    raise FileNotFoundError("credentials.json not found! Please download it from Google Cloud Console.")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(self.creds.to_json())

    def fetch_unread_meeting_notes(self, keywords=["회의록"]):
        gmail_service = build('gmail', 'v1', credentials=self.creds)
        
        # Build dynamic query: from:meetings-noreply@google.com (subject:"key1" OR subject:"key2")
        # However, for robustness if emails don't come from meetings-noreply, we should probably just use subject OR
        subject_query = " OR ".join([f'subject:"{k}"' for k in keywords])
        query = f'({subject_query})'
        
        results = gmail_service.users().messages().list(userId='me', q=query, maxResults=500).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("No meeting notes found in Gmail matching the keywords.")
            return []

        notes = []
        for message in messages:
            msg_id = message['id']
            msg = gmail_service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            subject = ""
            for header in msg['payload']['headers']:
                if header['name'] == 'Subject':
                    subject = header['value']
                    break
                    
            parts = [msg['payload']]
            html_body = ""
            while parts:
                part = parts.pop(0)
                if part.get('parts'):
                    parts.extend(part['parts'])
                if part.get('body') and part['body'].get('data'):
                    import base64
                    data = part['body']['data']
                    byte_code = base64.urlsafe_b64decode(data)
                    html_body += byte_code.decode("utf-8")
                    
            # Find ALL docs links in the email body
            matches = set(re.findall(r'https://docs\.google\.com/document/d/([a-zA-Z0-9-_]+)', html_body))
            if not matches:
                continue
                
            docs_service = build('docs', 'v1', credentials=self.creds)
            
            for idx, doc_id in enumerate(matches):
                try:
                    document = docs_service.documents().get(documentId=doc_id).execute()
                    
                    text_content = ""
                    for element in document.get('body').get('content'):
                        if 'paragraph' in element:
                            elements = element.get('paragraph').get('elements')
                            for elem in elements:
                                text_content += elem.get('textRun', {}).get('content', '')
                    
                    # Ensure unique ID in Ingestion History for multiple docs in one email
                    unique_source_id = f"{msg_id}_{idx}" if len(matches) > 1 else msg_id
                    
                    notes.append({
                        "msg_id": unique_source_id,
                        "subject": subject + (f" (문서 {idx+1})" if len(matches) > 1 else ""),
                        "text": text_content
                    })
                except Exception as e:
                    print(f"Could not fetch docs for {doc_id}: {e}")
                
        return notes
