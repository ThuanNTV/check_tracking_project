import re

def detect_carrier(tracking_number):
    patterns = {
        "J&T Express": r"^\d{10,12}$",
         "Shopee Express (SPX)": r"^SPX(VN)?\d{12}",
    }

    for carrier, pattern in patterns.items():
        if re.match(pattern, tracking_number, re.IGNORECASE):
            return carrier
    return "Unknown"