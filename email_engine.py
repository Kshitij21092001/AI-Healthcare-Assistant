# email_engine.py
import os, requests, json
from dotenv import load_dotenv

load_dotenv()
LOGIC_APP_URL = os.getenv("LOGIC_APP_URL")

def send_report_email(to_email, subject, body, attachments=None):
    if not LOGIC_APP_URL:
        print("Error: LOGIC_APP_URL is missing.")
        return False, "LOGIC_APP_URL not configured"

    # We are intentionally IGNORING 'attachments' to prevent Logic App crashes.
    # The Doctor will see the full analysis table in the email body.
    
    payload = {
        "to": to_email,
        "subject": subject,
        "body": body
        # Removed 'hasAttachment', 'filename', 'attachmentBase64' to keep it simple
    }

    print(f"DEBUG: Sending Email -> To: {to_email}")

    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(LOGIC_APP_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code in (200, 202):
            print("SUCCESS: Logic App accepted the request.")
            return True, "Email sent successfully"
        else:
            print(f"FAILURE: Logic App returned {response.status_code}")
            return False, f"Logic App Error: {response.text}"
            
    except Exception as e:
        return False, f"Network Error: {e}"