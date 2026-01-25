import os
import time
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.exceptions import ServiceRequestError
from dotenv import load_dotenv

load_dotenv()

FORM_ENDPOINT = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
FORM_KEY = os.getenv("AZURE_FORM_RECOGNIZER_KEY")

def extract_text_from_file(file_path, max_retries=3, retry_delay=5):
    client = DocumentAnalysisClient(
        endpoint=FORM_ENDPOINT,
        credential=AzureKeyCredential(FORM_KEY)
    )

    for attempt in range(max_retries):
        try:
            with open(file_path, "rb") as f:
                poller = client.begin_analyze_document("prebuilt-document", document=f)
                result = poller.result()
            return result.content  # Success, return the content
        except ServiceRequestError as e:
            if "Failed to resolve" in str(e) and attempt < max_retries - 1:
                print(f"DNS resolution failed (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise e  # Re-raise if max retries reached or different error

        except Exception as e:
            if "getaddrinfo failed" in str(e):
                raise RuntimeError("Your OCR endpoint is unreachable. Please check AZURE_FORM_RECOGNIZER_ENDPOINT in .env")
