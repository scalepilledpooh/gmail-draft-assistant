#!/usr/bin/env python3
"""
Gmail Draft Assistant: Fetch your most recent messages and generate reply drafts.

This script queries your Gmail inbox for messages received within a given number of days,
creates a suggested reply for each, and allows you to approve or edit the draft before saving
it to your Gmail drafts folder (threads are preserved).

Usage:
    python gmail_drafts.py [--credentials CREDENTIALS_JSON]
                            [--token TOKEN_JSON]
                            [--days DAYS] [--max MAX]
                            [--lm-url LM_URL] [--lm-model LM_MODEL]

Dependencies:
    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib openai

To enable relevance filtering with a local LMStudio OpenAI-compatible server,
serve your gemma-3n model file via LMStudio's HTTP API and then pass
--lm-url http://HOST:PORT/v1. For example:

  lm-cli serve \
    --model-path ~/.lmstudio/models/lmstudio-community/gemma-3n-E4B-it-text-GGUF/gemma-3n-E4B-it-Q4_K_M.gguf \
    --api --host 127.0.0.1 --port 8000

and then:
  python gmail_drafts.py --lm-url http://127.0.0.1:8000/v1
"""
import os
import sys
import argparse
import base64
from openai import OpenAI
import tempfile
import subprocess
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Import personal configuration
try:
    from config import (
        USER_NAME, USER_PHONE, EMAIL_SIGNATURE, ASSISTANT_PERSONA,
        REPLY_SYSTEM_PROMPT, get_template_reply, RELEVANCE_SYSTEM_PROMPT,
        RESPONSE_SYSTEM_PROMPT, RELEVANCE_CRITERIA
    )
except ImportError:
    print("Error: config.py not found. Please create config.py with your personal details.")
    print("See config_example.py for template.")
    sys.exit(1)

# Scopes: read messages, create drafts, and modify messages (for archiving)
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
]


def authenticate(credentials_path, token_path):
    """Perform OAuth2 flow and return an authorized Gmail API service."""
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def list_recent_messages(service, days=1, max_results=5):
    """List message IDs from the inbox newer than given days."""
    query = f'newer_than:{days}d'
    results = service.users().messages().list(
        userId='me', labelIds=['INBOX'], q=query, maxResults=max_results * 10  # Get many more messages to account for strict filtering
    ).execute()
    return results.get('messages', [])


def get_message_metadata(service, msg_id):
    """Fetch subject, sender, threadId, and snippet for a message ID."""
    try:
        msg = service.users().messages().get(
            userId='me', id=msg_id, format='full'
        ).execute()
        headers = msg.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(no subject)')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        snippet = msg.get('snippet', '')
        thread_id = msg.get('threadId')
        return subject, sender, snippet, thread_id
    except Exception as e:
        print(f"Warning: Failed to fetch message {msg_id}: {e}")
        return '(error)', '(error)', '(error)', None


def generate_reply_body(client: OpenAI, subject: str, sender: str, snippet: str, lm_model: str) -> str:
    """Generate a contextual reply using the LM with professional and friendly tone."""
    name = sender.split('<')[0].strip()
    
    user_prompt = f"From: {sender}\nSubject: {subject}\nContent: {snippet}\n\nGenerate a professional reply:"
    
    try:
        resp = client.chat.completions.create(
            model=lm_model,
            messages=[
                {'role': 'system', 'content': REPLY_SYSTEM_PROMPT},
                {'role': 'user', 'content': user_prompt},
            ],
            max_tokens=150,
            temperature=0.2,
            timeout=15,  # 15 second timeout
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise e  # Re-raise to let the calling function handle it


def edit_body(initial_body):
    """Open the initial body in the user's editor and return the modified content."""
    editor = os.environ.get('EDITOR', 'vi')
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as tmp:
        tmp.write(initial_body)
        tmp.flush()
        path = tmp.name
    subprocess.call([editor, path])
    with open(path, 'r') as tmp:
        content = tmp.read()
    os.unlink(path)
    return content


def create_draft(service, reply_body, subject, sender, thread_id):
    """Create a draft reply in Gmail preserving the thread."""
    message = MIMEText(reply_body)
    message['to'] = sender
    message['subject'] = f'Re: {subject}'
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId='me', body={
            'message': {'raw': raw, 'threadId': thread_id}
        }
    ).execute()
    return draft.get('id')


def archive_message(service, msg_id):
    """Archive a message by removing the INBOX label."""
    try:
        service.users().messages().modify(
            userId='me', id=msg_id, body={'removeLabelIds': ['INBOX']}
        ).execute()
        return True
    except Exception as e:
        print(f"Warning: Failed to archive message {msg_id}: {e}")
        return False


def has_existing_draft(service, thread_id):
    """Check if there's already a draft for this thread."""
    try:
        drafts = service.users().drafts().list(userId='me').execute()
        for draft in drafts.get('drafts', []):
            if draft.get('message', {}).get('threadId') == thread_id:
                return True
        return False
    except Exception as e:
        print(f"Warning: Failed to check existing drafts: {e}")
        return False

def check_relevance(client: OpenAI, snippet: str, lm_model: str) -> bool:
    """Use a local OpenAI-compatible LMStudio client to decide if the snippet is important."""
    resp = client.chat.completions.create(
        model=lm_model,
        messages=[
            {'role': 'system', 'content': RELEVANCE_SYSTEM_PROMPT},
            {'role': 'user', 'content': snippet},
        ],
        max_tokens=3,
        temperature=0,
    )
    answer = resp.choices[0].message.content.strip().lower()
    return answer.startswith('yes')


def needs_response(client: OpenAI, snippet: str, lm_model: str) -> bool:
    """Use a local OpenAI-compatible LMStudio client to decide if the snippet needs a reply."""
    resp = client.chat.completions.create(
        model=lm_model,
        messages=[
            {'role': 'system', 'content': RESPONSE_SYSTEM_PROMPT},
            {'role': 'user', 'content': snippet},
        ],
        max_tokens=3,
        temperature=0,
    )
    answer = resp.choices[0].message.content.strip().lower()
    return answer.startswith('yes')


def main():
    parser = argparse.ArgumentParser(description='Generate Gmail reply drafts for recent messages.')
    parser.add_argument(
        '--credentials',
        default='credentials.json',
        help='Path to OAuth2 client credentials JSON file (place your client_secret JSON as credentials.json)'
    )
    parser.add_argument('--token', default='token.json', help='Path to OAuth2 token JSON file')
    parser.add_argument('--days', type=int, default=1, help='Look back this many days')
    parser.add_argument('--max', type=int, default=5, help='Max messages to process')
    parser.add_argument('--lm-url', default='http://localhost:1234/v1',
                        help='Optional: Base URL of a local OpenAI-compatible LMStudio API (e.g. http://localhost:1234/v1)')
    parser.add_argument('--lm-model', default='google/gemma-3n-e4b',
                        help='Optional: model name to use at the LMStudio endpoint (default: google/gemma-3n-e4b)')
    parser.add_argument('--no-filter', action='store_true',
                        help='Disable relevance filtering and process all messages')
    parser.add_argument('--archive', action='store_true',
                        help='Archive messages that are not deemed relevant')
    parser.add_argument('--auto-draft', action='store_true',
                        help='Automatically create drafts for emails that need responses')
    args = parser.parse_args()

    service = authenticate(args.credentials, args.token)
    lm_client = None
    if args.lm_url:
        try:
            lm_client = OpenAI(base_url=args.lm_url.rstrip('/'), api_key='lm-studio')
            models = [m.id for m in lm_client.models.list().data]
            print(f"Local LMStudio models loaded: {models}")
            if args.lm_model not in models:
                print(f"Warning: configured model '{args.lm_model}' not found in loaded models.")
        except Exception as err:
            print(f"Warning: Could not connect to LMStudio at {args.lm_url}: {err}")
            print("Continuing without relevance filtering...")
            lm_client = None
    messages = list_recent_messages(service, days=args.days, max_results=args.max)
    if not messages:
        print('No recent messages found.')
        return

    print(f'Found {len(messages)} recent messages. Processing emails...')
    total_processed = 0
    drafts_created = 0
    ai_drafts = 0
    template_drafts = 0
    existing_drafts = 0
    emails_kept = 0
    emails_archived = 0
    
    for i, msg in enumerate(messages, 1):
        total_processed += 1
        subject, sender, snippet, thread_id = get_message_metadata(service, msg['id'])
        
        # Skip messages that failed to load
        if subject == '(error)':
            print(f"Skipping message {i} (processed {total_processed} total): failed to load metadata.")
            continue
        
        # Check if email is relevant (important to keep)
        is_relevant = True
        if lm_client and not args.no_filter:
            is_relevant = check_relevance(lm_client, snippet or subject, args.lm_model)
        
        if not is_relevant:
            print(f"Message {i} (processed {total_processed} total): not relevant - archiving")
            if args.archive:
                if archive_message(service, msg['id']):
                    print(f"  → Archived message {i}")
                    emails_archived += 1
                else:
                    print(f"  → Failed to archive message {i}")
            continue
        
        # Email is relevant - check if it needs a response
        needs_reply = False
        if lm_client and args.auto_draft:
            needs_reply = needs_response(lm_client, snippet or subject, args.lm_model)
        
        if needs_reply:
            # Check if there's already a draft for this thread
            if thread_id and has_existing_draft(service, thread_id):
                print(f"Message {i} (processed {total_processed} total): needs response - existing draft found, skipping")
                existing_drafts += 1
            else:
                # Create draft automatically using AI if available, otherwise use template
                if lm_client:
                    try:
                        body = generate_reply_body(lm_client, subject, sender, snippet, args.lm_model)
                        print(f"Message {i} (processed {total_processed} total): needs response - AI draft created")
                        ai_drafts += 1
                    except Exception as e:
                        print(f"Message {i}: AI generation failed ({e}), using template")
                        name = sender.split('<')[0].strip()
                        body = get_template_reply(name, subject)
                        template_drafts += 1
                else:
                    # Fallback to template when no LM client
                    name = sender.split('<')[0].strip()
                    body = get_template_reply(name, subject)
                    print(f"Message {i} (processed {total_processed} total): needs response - template draft created")
                    template_drafts += 1
                
                draft_id = create_draft(service, body, subject, sender, thread_id)
                print(f"  → Draft saved (ID: {draft_id})")
                drafts_created += 1
        else:
            # Keep email but don't create draft
            print(f"Message {i} (processed {total_processed} total): important but no response needed - keeping in inbox")
            emails_kept += 1
    
    # Summary
    print(f"\n=== Summary ===")
    print(f"Total processed: {total_processed}")
    print(f"Drafts created: {drafts_created}")
    if drafts_created > 0:
        print(f"  - AI drafts: {ai_drafts}")
        print(f"  - Template drafts: {template_drafts}")
    if existing_drafts > 0:
        print(f"Existing drafts found: {existing_drafts}")
    print(f"Emails kept: {emails_kept}")
    if args.archive:
        print(f"Emails archived: {emails_archived}")


if __name__ == '__main__':
    main()