# pipeline.py
from ocr_engine import extract_text_from_file   # should support multi-page PDFs
from structured_parser import extract_structured_labs
from llm_engine import analyze_findings
from doctor_engine import get_doctors_by_specialty
from risk_engine import compute_risk_and_insights
from memory_engine import add_message
import os

def analyze_medical_report(file_path):
    # OCR: should extract full text for multi-page PDFs
    raw_text = extract_text_from_file(file_path)

    if not raw_text or len(raw_text.strip()) < 5:
        return {"error":"OCR failed or returned empty","raw_text":raw_text}

    # Save user upload to memory
    add_message("user", f"Uploaded document: {os.path.basename(file_path)}")

    # Structured extraction via LLM
    parsed = extract_structured_labs(raw_text)
    findings = parsed.get("tests", [])

    # normalize field names for downstream modules
    for f in findings:
        # ensure canonical keys
        if "name" not in f and "test" in f:
            f["name"] = f["test"]
        # ensure interpretation exists
        if "interpretation" not in f:
            f["interpretation"] = f.get("interpretation","unknown")

    if not findings:
        add_message("assistant", "AI parser could not extract structured results.")
        return {"error":"No results extracted","raw_text":raw_text}

    # LLM triage (existing)
    llm_output = analyze_findings(findings)

    # Standardize specialty
    specialty_raw = llm_output.get("suggested_specialty","") or "general_physician"
    mappings = {
        "primary_care":"General Physician","general_physician":"General Physician",
        "infectious_disease":"Infectious Disease","hematology":"Hematology",
        "endocrinology":"Endocrinology","nephrology":"Nephrology",
        "cardiology":"Cardiology","pathology":"Pathology"
    }
    specialty = mappings.get(specialty_raw.lower(), "General Physician")

    doctors = get_doctors_by_specialty(specialty)
    # risk scoring & insights
    risk = compute_risk_and_insights(findings)

    # Save assistant summary to memory
    summary = f"Analyzed {os.path.basename(file_path)}: decision={llm_output.get('decision')}, specialty={specialty}"
    add_message("assistant", summary)

    return {
        "raw_text": raw_text,
        "findings": findings,
        "llm_output": llm_output,
        "doctors": doctors,
        "risk": risk
    }
