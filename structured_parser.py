# structured_parser.py
import os
import json
from openai import AzureOpenAI

# Initialize client
client = AzureOpenAI(
    api_version=os.getenv("AZURE_FOUNDRY_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_FOUNDRY_ENDPOINT"),
    api_key=os.getenv("AZURE_FOUNDRY_KEY"),
)

def extract_structured_labs(raw_text: str):
    """
    Uses GPT-5 to extract structured lab test values from ANY medical report text.
    """

    prompt = f"""
You are a medical data extraction model built to convert ANY medical lab report text
into clean, structured JSON.

The input text may be:
- from any country or hospital
- in any layout (tables, paragraphs, multiline, broken OCR)
- with noisy text, phone numbers, timestamps, addresses, headings
- with qualitative results (Reactive / Non-Reactive / Positive / Negative)
- with numeric results (125 mg/dl)
- with textual reference ranges ("30-100 sufficient", "<20 deficient", ">100 toxic")
- with uncommon units or missing units

Your job:
1. Identify **every laboratory test** mentioned.
2. Extract:
    - test name (standardized)
    - value (float if numeric, string if qualitative)
    - unit (null if not present)
    - ref_low (null if not present)
    - ref_high (null if not present)
    - interpretation:
        - "low"
        - "normal"
        - "high"
        - "positive"
        - "negative"
        - "abnormal"
3. Ignore:
    - phone numbers
    - hospital addresses
    - timestamps (05:54 AM)
    - doctor names / registration numbers
    - administrative info
4. If multiple values appear, choose the clinically correct one.
5. If reference ranges are textual (example: "<20 deficient"), convert them
   into equivalent numeric reference ranges.
6. Infer missing ranges using medical knowledge (normal Vitamin D range, PTH range, CBC ranges etc.).
7. NEVER hallucinate values not found in text.
8. Always return **valid JSON ONLY**:

{{
  "tests": [
    {{
      "name": "string",
      "value": float or string,
      "unit": "string or null",
      "ref_low": float or null,
      "ref_high": float or null,
      "interpretation": "low|normal|high|positive|negative|abnormal"
    }},
    ...
  ]
}}

Input text:
--------------------
{raw_text}
--------------------
"""

    # Use Azure Foundry Responses API
    response = client.responses.create(
        model=os.getenv("AZURE_FOUNDRY_DEPLOYMENT"),
        input=[{"role": "user", "content": prompt}],
    )

    # The responses API returns a structured object with output_text
    json_text = response.output_text

    # Parse JSON safely
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        # If formatting was slightly off, attempt to recover JSON block
        start = json_text.find("{")
        end = json_text.rfind("}") + 1
        return json.loads(json_text[start:end])
