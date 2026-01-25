from llm_engine import analyze_findings

sample_findings = [
    {"test": "Hemoglobin", "value": 10.2, "unit": "g/dL", "ref_low": 12.0, "ref_high": 16.0},
    {"test": "WBC", "value": 7800.0, "unit": "/µL", "ref_low": 4.0, "ref_high": 11.0},
    {"test": "Platelets", "value": 150.0, "unit": "x10^3/µL", "ref_low": 150.0, "ref_high": 400.0},
    {"test": "Creatinine", "value": 1.1, "unit": "mg/dL", "ref_low": 0.6, "ref_high": 1.3}
]

output = analyze_findings(sample_findings)
print(output)
