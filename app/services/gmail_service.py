"""Gmail service for email monitoring and sending."""

import logging
import os
import base64
from email.mime.text import MIMEText
from typing import Optional, List, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Gmail API scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",  # Read and send emails
]

# Combined scopes for Calendar + Gmail
COMBINED_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailService:
    """Service for interacting with Gmail API."""

    def __init__(self, credentials_path: Optional[str] = None):
        """Initialize Gmail client.
        
        Args:
            credentials_path: Path to OAuth credentials JSON file.
                             If None, uses settings.GOOGLE_CREDENTIALS_PATH
        """
        self.creds: Optional[Credentials] = None
        self.service = None
        
        credentials_path = credentials_path or settings.GOOGLE_CREDENTIALS_PATH
        if credentials_path:
            self._authenticate(credentials_path)
        else:
            logger.warning(
                "No Google credentials path provided. Gmail service will be disabled."
            )

    def _authenticate(self, credentials_path: str):
        """Authenticate with Gmail API using OAuth 2.0.
        
        Args:
            credentials_path: Path to OAuth credentials JSON file
        """
        try:
            token_path = os.path.join(os.path.dirname(credentials_path), "token.json")
            
            # Try to load existing token
            if os.path.exists(token_path):
                # Check if token has Gmail scope
                existing_creds = Credentials.from_authorized_user_file(token_path, COMBINED_SCOPES)
                # If token exists but doesn't have Gmail scope, we need to re-authenticate
                if existing_creds.valid:
                    if "gmail.modify" in existing_creds.scopes:
                        self.creds = existing_creds
                    else:
                        logger.info("Token exists but missing Gmail scope. Re-authenticating...")
                        self.creds = None
                else:
                    self.creds = existing_creds

            # If no valid credentials, authenticate
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    try:
                        self.creds.refresh(Request())
                        # After refresh, check if we have Gmail scope
                        if "gmail.modify" not in self.creds.scopes:
                            logger.info("Token refreshed but missing Gmail scope. Re-authenticating...")
                            self.creds = None
                    except Exception as e:
                        logger.warning(f"Failed to refresh token: {e}. Re-authenticating...")
                        self.creds = None
                
                if not self.creds or not self.creds.valid:
                    if not os.path.exists(credentials_path):
                        logger.warning(
                            f"Google credentials file not found at {credentials_path}. "
                            "Gmail integration will be disabled."
                        )
                        return

                    # Use combined scopes to get both Calendar and Gmail access
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, COMBINED_SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)

                    # Save the credentials for the next run
                    with open(token_path, "w") as token:
                        token.write(self.creds.to_json())

            # Build the Gmail service
            self.service = build("gmail", "v1", credentials=self.creds)
            logger.info("Gmail service initialized successfully")

        except Exception as e:
            logger.warning(
                f"Failed to initialize Gmail service: {e}. "
                "Gmail integration will be disabled."
            )
            self.service = None

    def get_unread_emails(self, query: Optional[str] = None, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get unread emails.
        
        Args:
            query: Optional Gmail search query (e.g., "is:unread")
            max_results: Maximum number of emails to return
            
        Returns:
            List of email dictionaries with id, threadId, snippet, etc.
        """
        if not self.service:
            logger.warning("Gmail service not initialized")
            return []

        try:
            # Default query to get unread emails
            search_query = query or "is:unread"
            
            # List messages
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=search_query, maxResults=max_results)
                .execute()
            )
            
            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} unread emails")
            
            return messages
            
        except HttpError as e:
            logger.error(f"Error fetching emails: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching emails: {e}")
            return []

    def get_email_by_id(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Get full email details by ID.
        
        Args:
            email_id: Gmail message ID
            
        Returns:
            Email dictionary with full headers and body, or None
        """
        if not self.service:
            logger.warning("Gmail service not initialized")
            return None

        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=email_id, format="full")
                .execute()
            )
            
            return message
            
        except HttpError as e:
            logger.error(f"Error fetching email {email_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching email: {e}")
            return None

    def extract_participants(self, email_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract participants (FROM, TO, CC) from email.
        
        Args:
            email_data: Full email dictionary from get_email_by_id()
            
        Returns:
            Dictionary with 'from', 'to', 'cc' lists of email addresses
        """
        participants = {"from": [], "to": [], "cc": []}
        
        headers = email_data.get("payload", {}).get("headers", [])
        
        for header in headers:
            name = header.get("name", "").lower()
            value = header.get("value", "")
            
            if name == "from":
                # Extract email from "Name <email>" format
                participants["from"] = self._parse_email_addresses(value)
            elif name == "to":
                participants["to"] = self._parse_email_addresses(value)
            elif name == "cc":
                participants["cc"] = self._parse_email_addresses(value)
        
        return participants

    def _parse_email_addresses(self, address_string: str) -> List[str]:
        """Parse email addresses from header value.
        
        Args:
            address_string: Header value like "Name <email@example.com>" or "email@example.com"
            
        Returns:
            List of email addresses
        """
        import re
        
        # Pattern to match email addresses
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        emails = re.findall(email_pattern, address_string)
        return emails

    def is_centi_mentioned(self, email_data: Dict[str, Any], centi_email: str) -> bool:
        """Check if Centi was CC'd or mentioned in email.
        
        Args:
            email_data: Full email dictionary
            centi_email: Centi's email address
            
        Returns:
            True if Centi is in TO or CC
        """
        participants = self.extract_participants(email_data)
        
        # Check if Centi is in TO or CC
        all_recipients = participants["to"] + participants["cc"]
        return centi_email.lower() in [e.lower() for e in all_recipients]

    def is_owner_in_thread(
        self, thread_data: Dict[str, Any], owner_email: str
    ) -> bool:
        """Check if calendar owner is present in thread.
        
        Args:
            thread_data: Full thread dictionary from get_thread_by_id()
            owner_email: Calendar owner email address
            
        Returns:
            True if owner is found in any message in the thread
        """
        if not thread_data:
            return False
        
        owner_email_lower = owner_email.lower()
        messages = thread_data.get("messages", [])
        
        for message in messages:
            participants = self.extract_participants(message)
            all_participants = (
                participants["from"] + participants["to"] + participants["cc"]
            )
            
            # Check if owner is in any participant list
            if owner_email_lower in [e.lower() for e in all_participants]:
                return True
        
        return False

    def is_owner_in_email(self, email_data: Dict[str, Any], owner_email: str) -> bool:
        """Check if calendar owner is in current email.
        
        Args:
            email_data: Full email dictionary
            owner_email: Calendar owner email address
            
        Returns:
            True if owner is found in FROM, TO, or CC
        """
        participants = self.extract_participants(email_data)
        all_participants = (
            participants["from"] + participants["to"] + participants["cc"]
        )
        
        owner_email_lower = owner_email.lower()
        return owner_email_lower in [e.lower() for e in all_participants]

    def send_reply(
        self,
        thread_id: str,
        to: List[str],
        subject: str,
        body: str,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
    ) -> Optional[str]:
        """Send reply in email thread.
        
        Args:
            thread_id: Gmail thread ID to reply to
            to: List of recipient email addresses
            subject: Email subject (should start with "Re: " for replies)
            body: Email body (plain text or HTML)
            in_reply_to: Message-ID of email being replied to (for threading)
            references: References header for threading
            
        Returns:
            Message ID if successful, None otherwise
        """
        if not self.service:
            logger.warning("Gmail service not initialized")
            return None

        try:
            # Create message
            message = MIMEText(body)
            message["To"] = ", ".join(to)
            message["Subject"] = subject
            
            # Add threading headers if provided
            if in_reply_to:
                message["In-Reply-To"] = in_reply_to
            if references:
                message["References"] = references
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            # Send message
            send_result = (
                self.service.users()
                .messages()
                .send(
                    userId="me",
                    body={"raw": raw_message, "threadId": thread_id}
                )
                .execute()
            )
            
            message_id = send_result.get("id")
            logger.info(f"Reply sent successfully: {message_id}")
            return message_id
            
        except HttpError as e:
            logger.error(f"Error sending reply: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending reply: {e}")
            return None

    def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read.
        
        Args:
            email_id: Gmail message ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            logger.warning("Gmail service not initialized")
            return False

        try:
            self.service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            
            logger.info(f"Email {email_id} marked as read")
            return True
            
        except HttpError as e:
            logger.error(f"Error marking email as read: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error marking email as read: {e}")
            return False

    def get_thread_by_id(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get full email thread.
        
        Args:
            thread_id: Gmail thread ID
            
        Returns:
            Thread dictionary with all messages, or None
        """
        if not self.service:
            logger.warning("Gmail service not initialized")
            return None

        try:
            thread = (
                self.service.users()
                .threads()
                .get(userId="me", id=thread_id, format="full")
                .execute()
            )
            
            return thread
            
        except HttpError as e:
            logger.error(f"Error fetching thread {thread_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching thread: {e}")
            return None