from parser_engine import parse_report_text

# Insert the text you got from OCR => you can copy-paste it here
sample_text = """
Hemoglobin 10.2 g/dL (12-16)
WBC: 7800 /µL
Platelets - 150 x10^3/µL (150-400)
Creatinine 1.1 mg/dL
"""

findings = parse_report_text(sample_text)

print(findings)
