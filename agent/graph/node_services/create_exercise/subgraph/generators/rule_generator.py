import random
from typing import Dict, List


"""Rule-based Exercise Generator"""

class RuleBasedExerciseGenerator:
    """
    Generate exercises using pure Python logic.
    
    Supports:
    - Cộng/Trừ/Nhân/Chia (với range theo lớp)
    - So sánh số
    - Tìm x cơ bản
    - Bài toán lời văn (templates)
    - Chu vi/Diện tích (shapes)
    """
    
    def generate(self, grade: int, exercise_type: str, count: int) -> List[Dict]:
        """Generate exercises"""
        if exercise_type == "Phép cộng":
            return self._generate_addition(grade, count)
        elif exercise_type == "Phép trừ":
            return self._generate_subtraction(grade, count)
        elif exercise_type == "Phép nhân":
            return self._generate_multiply(grade, count)
        elif exercise_type == "Phép chia":
            return self._generate_division(grade, count)
        elif exercise_type == "mixed":
            return self._generate_mixed(grade, count)
    
    def _generate_addition(self, grade: int, count: int) -> List[Dict]:
        """Generate addition exercises"""
        min_val, max_val = self._get_range(grade)
        exercises = []
        
        for _ in range(count):
            a = random.randint(min_val, max_val)
            b = random.randint(min_val, max_val)
            answer = a + b
            
            exercises.append({
                "question": f"{a} + {b} = ?",
                "answer": str(answer),
                "type": "Phép cộng",
                "difficulty": self._get_difficulty(grade)
            })
        
        return exercises
    
    def _generate_subtraction(self, grade: int, count: int) -> List[Dict]:
        """Generate subtraction exercises"""
        min_val, max_val = self._get_range(grade)
        exercises = []
        
        for _ in range(count):
            a = random.randint(min_val, max_val)
            b = random.randint(min_val, a)  # Ensure non-negative result
            answer = a - b
            
            exercises.append({
                "question": f"{a} - {b} = ?",
                "answer": str(answer),
                "type": "Phép trừ",
                "difficulty": self._get_difficulty(grade)
            })
        
        return exercises
    
    def _generate_multiply(self, grade: int, count: int) -> List[Dict]:
        """Generate multiplication exercises"""
        min_val, max_val = self._get_range(grade)
        # Use smaller range for multiplication
        max_val = min(max_val, 12)
        exercises = []
        
        for _ in range(count):
            a = random.randint(1, max_val)
            b = random.randint(1, max_val)
            answer = a * b
            
            exercises.append({
                "question": f"{a} × {b} = ?",
                "answer": str(answer),
                "type": "Phép nhân",
                "difficulty": self._get_difficulty(grade)
            })
        
        return exercises
    
    def _generate_division(self, grade: int, count: int) -> List[Dict]:
        """Generate division exercises"""
        min_val, max_val = self._get_range(grade)
        max_val = min(max_val, 12)
        exercises = []
        
        for _ in range(count):
            b = random.randint(1, max_val)
            quotient = random.randint(1, max_val)
            a = b * quotient  # Ensure clean division
            
            exercises.append({
                "question": f"{a} ÷ {b} = ?",
                "answer": str(quotient),
                "type": "Phép chia",
                "difficulty": self._get_difficulty(grade)
            })
        
        return exercises
    
    def _generate_mixed(self, grade: int, count: int) -> List[Dict]:
        """Generate mixed exercises (combination of all types)"""
        exercises = []
        types = ["addition", "subtraction", "multiplication", "division"]
        
        for i in range(count):
            # Rotate through types
            exercise_type = types[i % len(types)]
            
            if exercise_type == "addition":
                ex = self._generate_addition(grade, 1)[0]
            elif exercise_type == "subtraction":
                ex = self._generate_subtraction(grade, 1)[0]
            elif exercise_type == "multiplication":
                ex = self._generate_multiply(grade, 1)[0]
            else:
                ex = self._generate_division(grade, 1)[0]
            
            exercises.append(ex)
        
        return exercises
    
    def _get_range(self, grade: int) -> tuple:
        """Get number range based on grade level"""
        ranges = {
            1: (1, 10),
            2: (1, 20),
            3: (1, 50),
            4: (1, 100),
            5: (1, 1000),
            6: (1, 10000),
            7: (1, 100000),
            8: (1, 1000000),
        }
        return ranges.get(grade, (1, 100))
    
    def _get_difficulty(self, grade: int) -> str:
        """Get difficulty level based on grade"""
        if grade <= 2:
            return "Dễ"
        elif grade <= 5:
            return "Trung bình"
        else:
            return "Khó"