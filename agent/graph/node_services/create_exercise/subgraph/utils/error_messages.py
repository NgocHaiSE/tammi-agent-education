"""Error Message Templates - theo BA"""

ERROR_TEMPLATES = {
    "E01": {
        "code": "E01",
        "message": "Chưa biết môn học nào? Bạn muốn tạo bài tập môn gì?",
        "suggestions": ["Toán lớp 1", "Toán lớp 3", "Toán lớp 5"]
    },
    "E02": {
        "code": "E02",
        "message": "Môn {subject} không phù hợp với lớp {grade}. Hiện tại chỉ hỗ trợ Toán lớp 1-5.",
        "suggestions": ["Toán lớp 1", "Toán lớp 3", "Toán lớp 5"]
    },
    "E03": {
        "code": "E03",
        "message": "Học sinh lớp mấy vậy?",
        "suggestions": ["Lớp 1", "Lớp 2", "Lớp 3", "Lớp 4", "Lớp 5"]
    },
    "E04": {
        "code": "E04",
        "message": "Chưa có thông tin lớp và môn học. Bạn cần tạo bài tập cho lớp mấy, môn gì?",
        "suggestions": ["Toán lớp 1", "Toán lớp 3", "Toán lớp 5"]
    }
}