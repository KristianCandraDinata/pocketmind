import os

DOMAIN = os.getenv("CONSULTATION_DOMAIN", "student_support")

AVAILABLE_DOMAINS = [
    "mpasi",
    "student_support",
]

if DOMAIN not in AVAILABLE_DOMAINS:
    raise ValueError(
        f"Domain tidak valid: {DOMAIN}. "
        f"Pilih salah satu: {AVAILABLE_DOMAINS}"
    )
