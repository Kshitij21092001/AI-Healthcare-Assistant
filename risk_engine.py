# risk_engine.py
def compute_risk_and_insights(findings):
    """
    returns {"score": 0-100, "flags": [...], "insights": [...]}
    Simple rules:
     - abnormal critical adds more points
     - multiple abnormalities increases score
     - domain-specific: high PTH + low VitD -> endocrine high risk
    """
    score = 0
    flags = []
    insights = []

    # helper to find test
    def get_test(name):
        for t in findings:
            if t.get("name","").lower() == name.lower() or t.get("test","").lower() == name.lower():
                return t
        return None

    # generic checks
    for t in findings:
        val = t.get("value")
        interp = t.get("interpretation","").lower()
        name = t.get("name") or t.get("test")
        if isinstance(val, (int,float)):
            # mild abnormality
            if interp == "low" or interp == "high" or interp == "abnormal":
                score += 15
                flags.append({"test": name, "flag": interp})
            # critical thresholds (ad-hoc)
            if name and ("hemoglobin" in name.lower() and val < 7):
                score += 30
                flags.append({"test": name, "flag": "critical"})
        else:
            if interp in ("positive","reactive"):
                score += 25
                flags.append({"test": name, "flag": interp})

    # domain insight: Vit D + PTH
    vit = get_test("Vitamin D") or get_test("25(OH) Vitamin D") or get_test("25(oh) vitamin d")
    pth = get_test("PTH") or get_test("Parathyroid Hormone")

    if vit and pth:
        try:
            v = float(vit["value"])
            p = float(pth["value"])
            if v < 30 and p > (pth.get("ref_high") or 65):
                score += 20
                insights.append("Low Vitamin D with elevated PTH suggests secondary hyperparathyroidism; endocrine referral recommended.")
        except:
            pass

    # cap score
    if score > 100: score = 100
    return {"score": score, "flags": flags, "insights": insights}
