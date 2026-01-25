import socket

# Force IPv4 by overriding the system address resolution
def force_ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    # AF_INET forces IPv4
    return socket.orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

# Save the original function just in case
socket.orig_getaddrinfo = socket.getaddrinfo
# Apply the "patch"
socket.getaddrinfo = force_ipv4_getaddrinfo


import os
import time
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.exceptions import ServiceRequestError

load_dotenv()

# FORM_ENDPOINT = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
# FORM_KEY = os.getenv("AZURE_FORM_RECOGNIZER_KEY")

FORM_ENDPOINT = "https://newmedicalocr.cognitiveservices.azure.com/"
FORM_KEY = "2AmmQSrrHxnEvJmCTr5PVatxRXxyVD3kbs8qPemMTswfTTZLNOzkJQQJ99BLACfhMk5XJ3w3AAALACOGgMbp" 

print(f"DEBUG: Testing Endpoint -> '{FORM_ENDPOINT}'") # verify no extra spaces print here

def test_ocr(file_path, max_retries=3, retry_delay=5):
    client = DocumentAnalysisClient(
        endpoint=FORM_ENDPOINT,
        credential=AzureKeyCredential(FORM_KEY)
    )

    for attempt in range(max_retries):
        try:
            with open(file_path, "rb") as f:
                poller = client.begin_analyze_document("prebuilt-document", document=f)
                result = poller.result()
            break  # Success, exit retry loop
        except ServiceRequestError as e:
            if "Failed to resolve" in str(e) and attempt < max_retries - 1:
                print(f"DNS resolution failed (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise e  # Re-raise if max retries reached or different error

    print("=== TEXT EXTRACTED FROM DOCUMENT ===")

    # The correct way to get all text in the document
    full_text = result.content

    print(full_text[:2000])  # Show first 2000 chars
    print("\n---- END OF SAMPLE EXTRACT ----")


if __name__ == "__main__":
    # Replace with any sample PDF or image you have
    test_ocr("sample_report.png")
