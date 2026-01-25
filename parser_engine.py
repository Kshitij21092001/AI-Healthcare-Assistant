# parser_engine.py
import re

# -------------------------------------------------------------
# REGEXES
# -------------------------------------------------------------
VALUE_RE = re.compile(r"(-?\d+(\.\d+)?)")
RANGE_RE = re.compile(r"(\d+(\.\d+)?)[\s\-–to]{1,3}(\d+(\.\d+)?)")
UNIT_RE = re.compile(
    r"(mg/dl|g/dl|µiu/ml|uiu/ml|x10\^3/µl|/µl|iu/l|mmol/l|µmol/l|ng/ml|%)",
    re.I,
)

# -------------------------------------------------------------
# RECOGNIZED TEST NAMES
# -------------------------------------------------------------
NAME_MAP = {
    "hb": "Hemoglobin",
    "hemoglobin": "Hemoglobin",
    "hgb": "Hemoglobin",
    "wbc": "WBC",
    "white blood": "WBC",
    "platelet": "Platelets",
    "platelets": "Platelets",
    "rbc": "RBC",
    "creatinine": "Creatinine",
    "glucose": "Glucose",
    "fasting glucose": "Glucose Fasting",
    "blood sugar": "Blood Sugar Random",
    "tsh": "TSH",
    "ns-1": "NS1 ANTIGEN DENGUE",
    "ns1": "NS1 ANTIGEN DENGUE",
    "dengue": "NS1 ANTIGEN DENGUE",
    "malaria": "Malaria Parasite",
    "typhidot": "Typhidot",
    "igm":"IgM",
}

# -------------------------------------------------------------
# FALLBACK NORMAL RANGES (for LLM context)
# -------------------------------------------------------------
DEFAULT_RANGES = {
    "Hemoglobin": {"low": 12.0, "high": 16.0, "unit": "g/dL"},
    "WBC": {"low": 4.0, "high": 11.0, "unit": "x10^3/µL"},
    "Platelets": {"low": 150, "high": 400, "unit": "x10^3/µL"},
    "Creatinine": {"low": 0.6, "high": 1.3, "unit": "mg/dL"},
    "TSH": {"low": 0.4, "high": 4.0, "unit": "µIU/mL"},
    "Glucose": {"low": 70, "high": 99, "unit": "mg/dL"},
    "Blood Sugar Random": {"low": 80, "high": 160, "unit":"mg/dL"},
}

# -------------------------------------------------------------
# QUALITATIVE MAPPINGS
# -------------------------------------------------------------
QUALITATIVE_KEYWORDS = {
    "negative": "negative",
    "non reactive": "negative",
    "non-reactive": "negative",
    "non - reactive": "negative",
    "nonreactive": "negative",
    "positive": "positive",
    "reactive": "positive",
    "detected": "positive",
    "not detected": "negative",
    "nil":"negative"
}

# -------------------------------------------------------------
# IGNORE BLOCK HEADERS (Hospital/Doctor/Metadata)
# -------------------------------------------------------------
IGNORE_HEADERS = [
    "advanta", "hospital", "super speciality", "jhajjar",
    "patient id", "patient", "date",
    "dr.", "regd", "consultant", "pathologist",
]


# =============================================================
# HELPER FUNCTIONS
# =============================================================

def detect_test_name(text_lower):
    for key, canonical in NAME_MAP.items():
        if key in text_lower:
            return canonical
    return None


def is_test_header(line):
    l = line.lower()

    # clearly hospital/doctor metadata
    if any(h in l for h in IGNORE_HEADERS):
        return False

    # known test keywords
    for k in NAME_MAP:
        if k in l:
            return True

    # uppercase headings like BIOCHEMISTRY
    if line.isupper() and len(line) > 3:
        return True

    return False


def parse_qualitative(text_lower):
    for key, val in QUALITATIVE_KEYWORDS.items():
        if key in text_lower:
            return val
    return None


# =============================================================
# MAIN PARSER FUNCTION
# =============================================================

def parse_report_text(raw_text):
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    findings = []

    # 1. GROUP LINES INTO BLOCKS --------------------------------------
    blocks = []
    current = []

    for line in lines:
        l = line.lower()

        # skip metadata lines
        if any(h in l for h in IGNORE_HEADERS):
            continue

        # start new test block
        if is_test_header(line):
            if current:
                blocks.append(current)
            current = [line]
        else:
            if current:
                current.append(line)

    if current:
        blocks.append(current)

    # 2. PROCESS EACH BLOCK -------------------------------------------
    for block in blocks:
        combined = " ".join(block)
        combined_l = combined.lower()

        # --- Detect Test Name ---
        test_name = detect_test_name(combined_l)
        if not test_name:
            # fallback: use first 2-3 words as test name
            test_name = block[0].split(":")[0][:40].strip()

        # --- Extract Value ---
        value = None
        vm = VALUE_RE.search(combined_l)
        if vm:
            try:
                value = float(vm.group())
            except:
                value = None

        # --- Extract Unit ---
        unit = None
        um = UNIT_RE.search(combined)
        if um:
            unit = um.group()

        # --- Extract Range ---
        ref_low = ref_high = None
        rm = RANGE_RE.search(combined_l)
        if rm:
            try:
                ref_low = float(rm.group(1))
                ref_high = float(rm.group(3))
            except:
                pass

        # --- Extract Qualitative ---
        qual = parse_qualitative(combined_l)

        # FILTER OUT GARBAGE NUMERIC VALUES ----------------------------
        if value is not None:
            if value > 500 or value < -5:        # drop phone numbers, reg no., junk
                continue
            if unit is None and (ref_low is None or ref_high is None):
                continue  # numeric with no unit or range = junk

        # VALID NUMERIC TEST -------------------------------------------
        if value is not None:
            # apply fallback range if needed
            if test_name in DEFAULT_RANGES and ref_low is None:
                r = DEFAULT_RANGES[test_name]
                ref_low = r["low"]
                ref_high = r["high"]
                if unit is None:
                    unit = r["unit"]

            findings.append({
                "test": test_name,
                "value": value,
                "unit": unit,
                "ref_low": ref_low,
                "ref_high": ref_high
            })
            continue

        # VALID QUALITATIVE TEST ---------------------------------------
        if qual is not None:
            findings.append({
                "test": test_name,
                "value": qual,
                "unit": None,
                "ref_low": None,
                "ref_high": None
            })
            continue

    return findings
