"""
Centralized suggestion prompts configuration for different sub_intents.

This ensures suggestions are consistent across the application
and defined in one place.
"""

from typing import Dict, List


SUGGESTIONS_MAP: Dict[str, List[str]] = {
    "search_material": [
        "Tìm tài liệu nâng cao hơn?",
        "Cần video hướng dẫn không?",
        "Xem khóa học online nào tốt?",
    ],
    "create_exercise": [
        "Tạo thêm bài tập nâng cao?",
        "Xem đáp án chi tiết?",
        "Tạo đề thi thử được không?",
    ],
    "correct_exercise": [
        "Giải thích thêm phần nào?",
        "Có ví dụ tương tự không?",
        "Cách làm khác là gì?",
    ],
    "tutor_subject": [
        "Lộ trình học tiếp theo?",
        "Phương pháp học nào hiệu quả?",
        "Tài liệu ôn tập nào tốt?",
    ],
}


def get_suggestions(sub_intent: str) -> List[str]:
    """
    Get contextual suggestions for a given sub_intent.
    
    Args:
        sub_intent: The sub_intent of the conversation
        
    Returns:
        List of suggestion prompts appropriate for the context.
        Returns search_material suggestions as default if sub_intent not found.
    """
    return SUGGESTIONS_MAP.get(sub_intent, SUGGESTIONS_MAP.get("search_material", []))
