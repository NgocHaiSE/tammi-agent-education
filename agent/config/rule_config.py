"""
Rule Engine Configuration for Create Exercise (Rule-based)
Defines paramters for generating exercises using rule-based.
Used for Math from grade 1 to grade 5 with standard curriculum.
"""

from typing import Dict, Tuple, List
from dataclasses import dataclass

NUMBER_RANGES: Dict[int, Tuple[int, int]] = {
    1: (1, 20),
    2: (1, 100),
    3: (1, 1000),
    4: (1, 10000),
    5: (1, 100000)
}

@dataclass
class ExerciseType:
    """Definition of exercise type"""
    name: str
    keyword: List[str]
    description: str
    min_grade: int
    max_grade: int

EXERCISE_TYPES = {
    "Phép cộng": ExerciseType(
        name="Phép cộng",
        keyword=["cộng", "tổng", "+", "plus", "add", "tăng", "thêm"],
        description="Phép cộng",
        min_grade=1,
        max_grade=5
    ), 
    "Phép trừ": ExerciseType(
        name="Phép trừ",
        keyword=["trừ", "hiệu", "-", "minus", "subtract"],
        description="Phép trừ",
        min_grade=1,
        max_grade=5
    ),
    "Phép nhân": ExerciseType(
        name="Phép nhân",
        keyword=["nhân", "tích", "*", "times", "multiply"],
        description="Phép nhân",
        min_grade=2,
        max_grade=5
    ),
    "Phép chia": ExerciseType(
        name="Phép chia",
        keyword=["chia", "thương", "/", "divide", "divided"],
        description="Phép chia",
        min_grade=3,
        max_grade=5
    ),
    "Phép so sánh": ExerciseType(
        name="Phép so sánh",
        keyword=["so sánh", "lớn hơn", "nhỏ hơn", "bằng", "bằng nhau", "greater than", "less than", "equal to"],
        description="Phép so sánh",
        min_grade=1,
        max_grade=3
    ),
    "Tìm x": ExerciseType(
        name="Tìm x",
        keyword=["tìm x", "giải phương trình", "find x", "solve for x"],
        description="Tìm giá trị của x trong phương trình đơn giản",
        min_grade=3,
        max_grade=5
    ),
    "Bài toán có lời văn": ExerciseType(
        name="Bài toán có lời văn",
        keyword=["bài toán có lời văn", "word problem", "story problem"],
        description="Bài toán có lời văn liên quan đến các phép tính cơ bản",
        min_grade=1,
        max_grade=5
    ),
    "Chu vi": ExerciseType(
        name="Chu vi",
        keyword=["chu vi", "perimeter"],
        description="Tính chu vi các hình học cơ bản",
        min_grade=3,
        max_grade=5
    ),
    "Diện tích": ExerciseType(
        name="Diện tích",
        keyword=["diện tích", "area"],
        description="Tính diện tích các hình học cơ bản",
        min_grade=4,
        max_grade=5
    ),
}

@dataclass
class DifficultyParams:
    """Parameters defining difficulty levels"""
    num_exercises: int
    complexity: str  
    use_decimals: bool
    use_fractions: bool
    multi_step: bool

DIFFICULTY_BY_GRADE: Dict[int, DifficultyParams] = {
    1: DifficultyParams(
        num_exercises=5,
        complexity="simple",
        use_decimals=False,
        use_fractions=False,
        multi_step=False
    ),
    2: DifficultyParams(
        num_exercises=5,
        complexity="simple",
        use_decimals=False,
        use_fractions=False,
        multi_step=False
    ),
    3: DifficultyParams(
        num_exercises=7,
        complexity="medium",
        use_decimals=False,
        use_fractions=False,
        multi_step=False
    ),
    4: DifficultyParams(
        num_exercises=8,
        complexity="medium",
        use_decimals=True,
        use_fractions=True,
        multi_step=False
    ),
    5: DifficultyParams(
        num_exercises=10,
        complexity="complex",
        use_decimals=True,
        use_fractions=True,
        multi_step=True
    ),
}

WORD_PROBLEM_TEMPLATES = {
    "addition": [
        "Bạn {name1} có {a} quyển vở. Bạn {name2} cho thêm {b} quyển. Hỏi bạn {name1} có tất cả bao nhiêu quyển vở?",
        "Trong giỏ có {a} quả táo. Mẹ mua thêm {b} quả. Hỏi trong giỏ có tất cả bao nhiêu quả táo?",
        "Lớp 1A có {a} học sinh nam và {b} học sinh nữ. Hỏi lớp 1A có tất cả bao nhiêu học sinh?",
    ],
    "subtraction": [
        "Bạn {name1} có {a} cái kẹo. Bạn ấy cho {name2} {b} cái. Hỏi bạn {name1} còn lại bao nhiêu cái kẹo?",
        "Cửa hàng có {a} quyển vở. Đã bán {b} quyển. Hỏi cửa hàng còn lại bao nhiêu quyển vở?",
        "Mẹ có {a} nghìn đồng. Mẹ mua đồ hết {b} nghìn đồng. Hỏi mẹ còn lại bao nhiêu tiền?",
    ],
    "multiplication": [
        "Một hộp có {a} cái bánh. Có {b} hộp như vậy. Hỏi có tất cả bao nhiêu cái bánh?",
        "Mỗi bạn có {a} quyển vở. Có {b} bạn. Hỏi có tất cả bao nhiêu quyển vở?",
        "Một xe chở {a} thùng hàng. Có {b} xe như vậy. Hỏi có tất cả bao nhiêu thùng hàng?",
    ],
    "division": [
        "Chia {a} cái kẹo cho {b} bạn, mỗi bạn được bao nhiêu cái?",
        "Có {a} quyển vở xếp đều vào {b} hộp. Hỏi mỗi hộp có bao nhiêu quyển vở?",
        "Chia {a} quả cam cho {b} người, mỗi người được bao nhiêu quả?",
    ],
}

STUDENT_NAMES = ["An", "Bình", "Chi", "Dũng", "Hoa", "Nam", "Lan", "Minh", "Nga", "Tuấn", "Hải", "Cường"]

@dataclass
class GeometryShape:
    """Geometry shape definition"""
    name: str
    name_vi: str
    perimeter_formula: str
    area_formula: str


GEOMETRY_SHAPES = {
    "square": GeometryShape(
        name="square",
        name_vi="hình vuông",
        perimeter_formula="4 × a",
        area_formula="a × a"
    ),
    "rectangle": GeometryShape(
        name="rectangle",
        name_vi="hình chữ nhật",
        perimeter_formula="(a + b) × 2",
        area_formula="a × b"
    ),
    "triangle": GeometryShape(
        name="triangle",
        name_vi="hình tam giác",
        perimeter_formula="a + b + c",
        area_formula="(đáy × cao) / 2"
    ),
}

def validate_grade_subject(grade: int, subject: str) -> bool:
    """Validate if grade and subject are valid for rule-based generation"""
    if subject.lower() != "toán":
        return False
    if grade < 1 or grade > 5:
        return False
    return True


def detect_exercise_type(topic: str, question: str) -> str:
    """Detect exercise type from topic and question"""
    combined = f"{topic.lower()} {question.lower()}"
    
    for ex_type, config in EXERCISE_TYPES.items():
        for keyword in config.keywords:
            if keyword in combined:
                return ex_type
    
    return "unknown"


def get_number_range(grade: int) -> Tuple[int, int]:
    """Get number range for a grade"""
    return NUMBER_RANGES.get(grade, (1, 100))


def get_difficulty_params(grade: int) -> DifficultyParams:
    """Get difficulty parameters for a grade"""
    return DIFFICULTY_BY_GRADE.get(grade, DIFFICULTY_BY_GRADE[3])