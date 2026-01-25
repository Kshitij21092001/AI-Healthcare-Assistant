from pipeline import analyze_medical_report

result = analyze_medical_report("sample_report.png")

print(result)  # <-- Print full object to inspect

if "error" in result:
    print("\nError:", result["error"])
else:
    print("\n--- Findings ---")
    print(result["findings"])
    print("\n--- LLM Output ---")
    print(result["llm_output"])
    print("\n--- Doctors ---")
    print(result["doctors"])
