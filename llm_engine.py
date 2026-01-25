import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
key = os.getenv("AZURE_OPENAI_KEY")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Your region uses Responses API
API_VERSION = "2025-03-01-preview"

client = AzureOpenAI(
    api_key=key,
    azure_endpoint=endpoint,
    api_version=API_VERSION,
)

SYSTEM_PROMPT = """
You are a conservative medical decision-support assistant.

Return ONLY JSON in this schema:
{
  "decision": "consult | no_consult | uncertain",
  "confidence": 0.0,
  "rationale": "",
  "top_findings": [{"test": "", "value": 0, "unit": "", "flag": ""}],
  "suggested_specialty": ""
}
"""

def extract_json(text):
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return text[start:end+1]
    return "{}"

def analyze_findings(findings):
    findings_json = json.dumps(findings, indent=2)

    response = client.responses.create(
        model=deployment,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Findings:\n{findings_json}\nReturn ONLY JSON."}
        ],
        max_output_tokens=500   # temperature removed
    )

    output_text = response.output_text
    json_block = extract_json(output_text)

    try:
        return json.loads(json_block)
    except:
        return {
            "decision": "uncertain",
            "confidence": 0.0,
            "rationale": "Invalid JSON returned by model.",
            "top_findings": [],
            "suggested_specialty": "General Physician",
            "raw": output_text
        }
