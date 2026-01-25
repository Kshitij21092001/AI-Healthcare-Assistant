import os
from dotenv import load_dotenv
load_dotenv()  # ensure .env is loaded

print("Python OK")

# Form Recognizer check
FORM_ENDPOINT = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
FORM_KEY = os.getenv("AZURE_FORM_RECOGNIZER_KEY")
if not FORM_ENDPOINT or not FORM_KEY:
    print("Form Recognizer env not set. Set AZURE_FORM_RECOGNIZER_ENDPOINT and AZURE_FORM_RECOGNIZER_KEY")
else:
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.formrecognizer import DocumentAnalysisClient
    try:
        client = DocumentAnalysisClient(endpoint=FORM_ENDPOINT, credential=AzureKeyCredential(FORM_KEY))
        # simple call: get account info or list models (lightweight)
        print("Form Recognizer endpoint and key appear configured.")
    except Exception as e:
        print("Form Recognizer connection failed:", e)

# OpenAI / Azure OpenAI check
if os.getenv("AZURE_OPENAI_KEY"):
    print("Azure OpenAI config found. Will use Azure OpenAI.")
elif os.getenv("OPENAI_API_KEY"):
    print("OpenAI API key found. Will use OpenAI.")
else:
    print("No OpenAI credentials found — set AZURE_OPENAI_KEY+DEPLOYMENT or OPENAI_API_KEY.")
