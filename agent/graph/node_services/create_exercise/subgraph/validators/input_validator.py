"""Input Validator Utilities"""

def validate_grade(grade: int) -> bool:
    """Check if grade is valid (1-5 for rule-based)"""
    return 1 <= grade <= 5

def validate_subject(subject: str) -> bool:
    """Check if subject is supported"""
    return subject.lower() in ["toán", "math", "toán học"]

def normalize_subject(subject: str) -> str:
    """Normalize subject name"""
    mapping = {
        "math": "toán",
        "toán học": "toán",
        "toan": "toán"
    }
    return mapping.get(subject.lower(), subject.lower())