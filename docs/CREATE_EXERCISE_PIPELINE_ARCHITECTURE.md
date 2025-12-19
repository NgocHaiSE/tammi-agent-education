# 🏗️ KIẾN TRÚC PIPELINE TẠO BÀI TẬP (CREATE EXERCISE)

## 📋 Tổng quan

Pipeline tạo bài tập được thiết kế theo kiến trúc **Rule-based + RAG + LLM Reasoning** (KHÔNG dùng SerpAPI):
- **Tier 1** (Rule-based): Toán lớp 1-5, xử lý cứng bằng rule + thư viện toán
- **Tier 2** (RAG): Truy xuất tài liệu từ vector DB (Qdrant/Elasticsearch) 
- **Tier 3** (LLM Fallback): Các trường hợp phức tạp, ngoài phạm vi

**KPI Mục tiêu:**
- ⏱️ Thời gian xử lý: ≤ 5s (non-stream), ≤ 4s (stream)
- ✅ Tỷ lệ pass testcase: ≥ 85%

---

## 🎯 Phạm vi hỗ trợ

### ✅ Tier 1: Phạm vi chính thức (Rule-based + Thư viện)
- **Môn**: Toán
- **Lớp**: 1 → 5
- **Dạng bài**:
  - Cộng / Trừ / Nhân / Chia
  - So sánh số
  - Tìm x cơ bản
  - Bài toán lời văn đơn giản 1 bước
  - Hình học cơ bản lớp nhỏ (đếm hình, chu vi hình vuông/chữ nhật)
- **Xử lý**: Python math libraries + Rule engine
- **Tốc độ**: < 1s

### 🔍 Tier 2: RAG-based (Vector Search)
- **Môn**: Toán, Lý, Hóa, Sinh, Văn, Sử...
- **Lớp**: 6 → 12
- **Nguồn dữ liệu**:
  - SGK điện tử (PDF embedded)
  - Đề thi các năm
  - Bài tập mẫu có lời giải
  - Tài liệu tham khảo
- **Xử lý**: Qdrant/Elasticsearch retrieval + LLM synthesis
- **Tốc độ**: 2-4s

### 🔄 Tier 3: LLM Fallback
- **Scope**: Ngoài phạm vi Tier 1 & 2
- **Dạng bài**: Phức tạp, không có trong RAG
- **Xử lý**: Pure LLM reasoning với prompt chuẩn hóa
- **Tốc độ**: 3-5s

---

## 🔀 KIẾN TRÚC TỔNG THỂ

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER REQUEST                                  │
│  {                                                               │
│    "content": "Tạo bài tập toán lớp 9 về phương trình",        │
│    "metadata": {                                                 │
│      "grade": "9",                                              │
│      "subject": "toán",                                         │
│      "topic": "phương trình bậc hai",                          │
│      "difficulty": "medium"  // optional                        │
│    }                                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  STAGE 1: INPUT VALIDATION                       │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ ValidationNode                                           │    │
│  │ • Check required fields: grade, subject, content        │    │
│  │ • Validate grade range (1-12)                          │    │
│  │ • Detect subject (Toán, Lý, Hóa, etc.)                │    │
│  │ • Return errors: E01, E02, E03, E04 if missing         │    │
│  │                                                          │    │
│  │ Outputs:                                                 │    │
│  │ • validated: true/false                                 │    │
│  │ • grade: int                                            │    │
│  │ • subject: string                                       │    │
│  │ • topic: string                                         │    │
│  │ • error_code: E01/E02/E03/E04 (if any)                │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              STAGE 2: SCOPE CLASSIFICATION & ROUTING             │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ ScopeClassifierNode                                      │    │
│  │                                                          │    │
│  │ Decision Logic:                                          │    │
│  │                                                          │    │
│  │ IF (subject == "Toán" AND grade in [1,2,3,4,5] AND     │    │
│  │     exercise_type in ["+","-","×","÷","so_sanh",       │    │
│  │                       "tim_x","bai_toan_loi_van"]):     │    │
│  │    → TIER_1_RULE_BASED                                  │    │
│  │                                                          │    │
│  │ ELIF (grade in [6,7,8,9,10,11,12] OR                   │    │
│  │       subject in ["Lý","Hóa","Sinh","Văn","Sử"]):     │    │
│  │    → TIER_2_RAG_BASED                                   │    │
│  │                                                          │    │
│  │ ELSE:                                                    │    │
│  │    → TIER_3_LLM_FALLBACK                                │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
           ↓                    ↓                    ↓
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │  TIER 1  │        │  TIER 2  │        │  TIER 3  │
    │   RULE   │        │   RAG    │        │   LLM    │
    └──────────┘        └──────────┘        └──────────┘
           ↓                    ↓                    ↓
           ↓                    ↓                    ↓
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │  TIER 1  │        │  TIER 2  │        │  TIER 3  │
    │   RULE   │        │   RAG    │        │   LLM    │
    └──────────┘        └──────────┘        └──────────┘
           ↓                    ↓                    ↓

┌─────────────────────────────────────────────────────────────────┐
│         TIER 1: RULE-BASED GENERATION (Toán lớp 1-5)            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ RuleBasedExerciseNode                                    │    │
│  │                                                          │    │
│  │ 1. Exercise Type Detection                              │    │
│  │    • Phép cộng: a + b = ?                              │    │
│  │    • Phép trừ: a - b = ?                               │    │
│  │    • Phép nhân: a × b = ?                              │    │
│  │    • Phép chia: a ÷ b = ?                              │    │
│  │    • So sánh: a [>, <, =] b                            │    │
│  │    • Tìm x: a + x = b                                  │    │
│  │    • Bài toán lời văn: 1 bước                          │    │
│  │    • Hình học: Chu vi/diện tích hình cơ bản            │    │
│  │                                                          │    │
│  │ 2. Generate using Python Libraries                      │    │
│  │    • random: số ngẫu nhiên theo độ khó                 │    │
│  │    • sympy: giải toán tượng trưng                      │    │
│  │    • numpy: tính toán nhanh                            │    │
│  │                                                          │    │
│  │ 3. Rule Engine Logic                                     │    │
│  │    • Lớp 1: số trong [0, 20]                           │    │
│  │    • Lớp 2: số trong [0, 100]                          │    │
│  │    • Lớp 3: số trong [0, 1000]                         │    │
│  │    • Lớp 4-5: số lớn hơn, phân số, thập phân           │    │
│  │                                                          │    │
│  │ 4. Output Format                                         │    │
│  │    • 5-10 bài tập/câu hỏi                              │    │
│  │    • Đáp án chính xác 100%                             │    │
│  │    • Lời giải từng bước                                │    │
│  │                                                          │    │
│  │ Performance: < 1s                                        │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
           ↓

┌─────────────────────────────────────────────────────────────────┐
│            TIER 2: RAG-BASED GENERATION (Lớp 6-12)              │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ RAGRetrievalNode                                         │    │
│  │                                                          │    │
│  │ 1. Query Construction                                    │    │
│  │    query = f"bài tập {subject} lớp {grade} {topic}"   │    │
│  │    query_embedding = embed_model.encode(query)          │    │
│  │                                                          │    │
│  │ 2. Vector Search (Qdrant/Elasticsearch)                 │    │
│  │    • Collection: "educational_materials"                │    │
│  │    • Top K: 5-10 documents                             │    │
│  │    • Filter: grade, subject, topic                     │    │
│  │    • Score threshold: > 0.7                            │    │
│  │                                                          │    │
│  │ 3. Retrieved Documents                                   │    │
│  │    • SGK điện tử (PDF chunks)                          │    │
│  │    • Đề thi các năm (có lời giải)                      │    │
│  │    • Bài tập mẫu (có hướng dẫn)                        │    │
│  │    • Tài liệu tham khảo                                │    │
│  │                                                          │    │
│  │ 4. Context Assembly                                      │    │
│  │    context = {                                          │    │
│  │      "textbook_content": [...],                        │    │
│  │      "example_exercises": [...],                       │    │
│  │      "solutions": [...]                                │    │
│  │    }                                                     │    │
│  │                                                          │    │
│  │ Performance: 1-2s                                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                              ↓                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ LLMSynthesisNode                                         │    │
│  │                                                          │    │
│  │ 1. Prompt Template Loading                              │    │
│  │    • Subject-specific templates                         │    │
│  │    • Grade-appropriate instructions                     │    │
│  │                                                          │    │
│  │ 2. Context Integration                                   │    │
│  │    prompt = build_prompt(                               │    │
│  │      template=subject_template,                         │    │
│  │      retrieved_docs=context,                            │    │
│  │      grade=grade,                                       │    │
│  │      topic=topic                                        │    │
│  │    )                                                     │    │
│  │                                                          │    │
│  │ 3. LLM Generation                                        │    │
│  │    • Model: GPT-4 / Claude / Gemini                    │    │
│  │    • Temperature: 0.7                                   │    │
│  │    • Max tokens: 2000                                   │    │
│  │                                                          │    │
│  │ 4. Output                                                │    │
│  │    • 3-10 exercises based on retrieved docs             │    │
│  │    • Similar style to textbook                          │    │
│  │    • Detailed solutions                                 │    │
│  │                                                          │    │
│  │ Performance: 2-4s (1-2s retrieval + 1-2s LLM)          │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
           ↓

┌─────────────────────────────────────────────────────────────────┐
│            TIER 3: LLM FALLBACK (Complex/Unknown)                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ LLMFallbackNode                                          │    │
│  │                                                          │    │
│  │ When to use:                                             │    │
│  │ • Dạng bài không nhận diện được                        │    │
│  │ • Môn học đặc biệt (Âm nhạc, Mỹ thuật...)             │    │
│  │ • Yêu cầu tùy chỉnh cao                                │    │
│  │ • RAG không tìm thấy tài liệu (score < 0.7)           │    │
│  │                                                          │    │
│  │ 1. Prompt Engineering                                    │    │
│  │    • Generic exercise generation prompt                 │    │
│  │    • Safety constraints (độ khó phù hợp lớp)          │    │
│  │    • Format requirements                                │    │
│  │                                                          │    │
│  │ 2. LLM Pure Reasoning                                    │    │
│  │    • NO retrieval context                               │    │
│  │    • Rely on LLM knowledge                             │    │
│  │    • Clear instructions for grade-appropriate content   │    │
│  │                                                          │    │
│  │ 3. Post-validation                                       │    │
│  │    • Check difficulty matches grade                     │    │
│  │    • Ensure no advanced concepts                        │    │
│  │                                                          │    │
│  │ Performance: 3-5s                                        │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘

---

                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                 STAGE 3: POST-PROCESSING                         │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ QualityValidationNode                                    │    │
│  │ • Check exercise count (3-10)                          │    │
│  │ • Validate difficulty matches grade                     │    │
│  │ • Ensure answers provided                              │    │
│  │ • Format consistency                                    │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                 STAGE 4: SUGGESTION GENERATION                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ SuggestionGeneratorNode                                  │    │
│  │ • 4-5 follow-up suggestions (≤ 8 words each)           │    │
│  │ • Examples:                                              │    │
│  │   - "Tạo thêm bài tập tương tự"                        │    │
│  │   - "Bài tập nâng cao hơn"                             │    │
│  │   - "Xem lời giải chi tiết"                            │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────┐
                    │  FINAL RESPONSE  │
                    │  {                │
                    │    tier: 1/2/3,   │
                    │    exercises: [], │
                    │    suggestions:[] │
                    │  }                │
                    └──────────────────┘
```

---

## 📦 CÁC COMPONENT CHI TIẾT

### 1️⃣ **ValidationNode**

```python
class ValidationNode(CreateExerciseNodeInterface):
    """Validate and normalize input"""
    
    async def run(self, state: CreateExerciseState):
        payload = state.get("request", {}).get("payload", {})
        metadata = payload.get("metadata", {})
        
        grade = metadata.get("grade")
        subject = metadata.get("subject")
        
        # E04: Missing both
        if not grade and not subject:
            return {
                "error_code": "E04",
                "error_message": "Chưa có thông tin lớp và môn học. Bạn cần tạo bài tập cho lớp mấy, môn gì?",
                "suggestions": [
                    "Toán lớp 3",
                    "Toán lớp 5",
                    "Lý lớp 8"
                ]
            }
        
        # E01: Missing subject
        if not subject:
            return {
                "error_code": "E01",
                "error_message": "Chưa biết môn học nào? Bạn muốn tạo bài tập môn gì?",
                "suggestions": [
                    "Toán",
                    "Lý",
                    "Hóa",
                    "Sinh"
                ]
            }
        
        # E03: Missing grade
        if not grade:
            return {
                "error_code": "E03",
                "error_message": "Học sinh lớp mấy vậy?",
                "suggestions": [
                    "Lớp 1",
                    "Lớp 3",
                    "Lớp 5",
                    "Lớp 9"
                ]
            }
        
        # E02: Invalid subject for grade
        if not self.validate_subject_grade(subject, grade):
            return {
                "error_code": "E02",
                "error_message": f"Môn {subject} không phù hợp với lớp {grade}",
                "suggestions": get_valid_subjects(grade)
            }
        
        return {
            "validated": True,
            "grade": int(grade),
            "subject": subject.lower(),
            "topic": metadata.get("topic", "")
        }
```

### 2️⃣ **ScopeClassifierNode**

```python
class ScopeClassifierNode(CreateExerciseNodeInterface):
    """Classify request into Tier 1/2/3"""
    
    # Rule-based types for Tier 1
    TIER_1_TYPES = {
        "cộng": "addition",
        "trừ": "subtraction", 
        "nhân": "multiplication",
        "chia": "division",
        "so sánh": "comparison",
        "tìm x": "find_x",
        "bài toán": "word_problem",
        "chu vi": "perimeter",
        "diện tích": "area"
    }
    
    async def run(self, state: CreateExerciseState):
        grade = state.get("grade")
        subject = state.get("subject")
        topic = state.get("topic", "").lower()
        question = state.get("question", "").lower()
        
        # TIER 1: Rule-based (Toán lớp 1-5, basic types)
        if subject == "toán" and 1 <= grade <= 5:
            exercise_type = self.detect_exercise_type(topic, question)
            if exercise_type in self.TIER_1_TYPES.values():
                return {
                    "tier": 1,
                    "processing_mode": "rule_based",
                    "exercise_type": exercise_type,
                    "next_node": "rule_based_exercise_node"
                }
        
        # TIER 2: RAG-based (Lớp 6-12, all subjects)
        if 6 <= grade <= 12:
            return {
                "tier": 2,
                "processing_mode": "rag_based",
                "next_node": "rag_retrieval_node"
            }
        
        # TIER 3: LLM Fallback
        return {
            "tier": 3,
            "processing_mode": "llm_fallback",
            "next_node": "llm_fallback_node"
        }
    
    def detect_exercise_type(self, topic: str, question: str) -> str:
        """Detect exercise type from topic/question"""
        combined = f"{topic} {question}"
        
        for keyword, ex_type in self.TIER_1_TYPES.items():
            if keyword in combined:
                return ex_type
        
        return "unknown"
```

### 3️⃣ **RuleBasedExerciseNode** (Tier 1)

```python
class RuleBasedExerciseNode(CreateExerciseNodeInterface):
    """Generate exercises using pure Python rules - FAST < 1s"""
    
    async def run(self, state: CreateExerciseState):
        grade = state.get("grade")
        exercise_type = state.get("exercise_type")
        
        # Generate based on type
        if exercise_type == "addition":
            exercises = self.generate_addition(grade)
        elif exercise_type == "subtraction":
            exercises = self.generate_subtraction(grade)
        elif exercise_type == "multiplication":
            exercises = self.generate_multiplication(grade)
        elif exercise_type == "division":
            exercises = self.generate_division(grade)
        elif exercise_type == "comparison":
            exercises = self.generate_comparison(grade)
        elif exercise_type == "find_x":
            exercises = self.generate_find_x(grade)
        elif exercise_type == "word_problem":
            exercises = self.generate_word_problem(grade)
        elif exercise_type in ["perimeter", "area"]:
            exercises = self.generate_geometry(grade, exercise_type)
        else:
            # Unknown type -> fallback to Tier 3
            return {"tier": 3, "fallback_reason": "unknown_type"}
        
        return {
            "tier": 1,
            "exercises": exercises,
            "generation_method": "rule_based",
            "processing_time": "<1s"
        }
    
    def generate_addition(self, grade: int) -> List[Dict]:
        """Generate addition exercises"""
        import random
        
        # Number range by grade
        ranges = {
            1: (1, 20),
            2: (1, 100),
            3: (1, 1000),
            4: (1, 10000),
            5: (1, 100000)
        }
        min_val, max_val = ranges.get(grade, (1, 100))
        
        exercises = []
        for i in range(5):
            a = random.randint(min_val, max_val)
            b = random.randint(min_val, max_val)
            answer = a + b
            
            exercises.append({
                "id": i + 1,
                "question": f"**Câu {i+1}:** {a} + {b} = ?",
                "answer": answer,
                "solution": f"**Lời giải:** {a} + {b} = {answer}",
                "difficulty": "easy"
            })
        
        return exercises
    
    def generate_subtraction(self, grade: int) -> List[Dict]:
        """Generate subtraction exercises"""
        import random
        
        ranges = {
            1: (1, 20),
            2: (1, 100),
            3: (1, 1000),
            4: (1, 10000),
            5: (1, 100000)
        }
        min_val, max_val = ranges.get(grade, (1, 100))
        
        exercises = []
        for i in range(5):
            a = random.randint(min_val, max_val)
            b = random.randint(min_val, a)  # b <= a to avoid negative
            answer = a - b
            
            exercises.append({
                "id": i + 1,
                "question": f"**Câu {i+1}:** {a} - {b} = ?",
                "answer": answer,
                "solution": f"**Lời giải:** {a} - {b} = {answer}",
                "difficulty": "easy"
            })
        
        return exercises
    
    def generate_find_x(self, grade: int) -> List[Dict]:
        """Generate find x exercises"""
        import random
        from sympy import symbols, Eq, solve
        
        x = symbols('x')
        exercises = []
        
        ranges = {
            1: (1, 20),
            2: (1, 100),
            3: (1, 1000),
            4: (1, 10000),
            5: (1, 100000)
        }
        min_val, max_val = ranges.get(grade, (1, 100))
        
        for i in range(5):
            a = random.randint(min_val, max_val)
            b = random.randint(min_val, max_val)
            
            # Random equation type
            eq_type = random.choice(['add', 'sub'])
            
            if eq_type == 'add':
                # x + a = b
                equation = Eq(x + a, b)
                answer = solve(equation)[0]
                question_text = f"x + {a} = {b}"
                solution_text = f"x = {b} - {a} = {answer}"
            else:
                # x - a = b  
                equation = Eq(x - a, b)
                answer = solve(equation)[0]
                question_text = f"x - {a} = {b}"
                solution_text = f"x = {b} + {a} = {answer}"
            
            exercises.append({
                "id": i + 1,
                "question": f"**Câu {i+1}:** Tìm x biết: {question_text}",
                "answer": int(answer),
                "solution": f"**Lời giải:** {solution_text}",
                "difficulty": "medium"
            })
        
        return exercises
```

### 4️⃣ **RAGRetrievalNode** (Tier 2)

```python
class RAGRetrievalNode(CreateExerciseNodeInterface):
    """Retrieve relevant documents from vector DB"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize vector DB client
        from qdrant_client import QdrantClient
        from sentence_transformers import SentenceTransformer
        
        self.qdrant = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        self.embed_model = SentenceTransformer(
            'keepitreal/vietnamese-sbert'
        )
    
    async def run(self, state: CreateExerciseState):
        grade = state.get("grade")
        subject = state.get("subject")
        topic = state.get("topic", "")
        question = state.get("question", "")
        
        # 1. Construct search query
        query = f"bài tập {subject} lớp {grade} {topic}"
        
        # 2. Generate embedding
        query_vector = self.embed_model.encode(query).tolist()
        
        # 3. Search Qdrant
        search_results = self.qdrant.search(
            collection_name="educational_materials",
            query_vector=query_vector,
            limit=10,
            query_filter={
                "must": [
                    {"key": "grade", "match": {"value": grade}},
                    {"key": "subject", "match": {"value": subject}}
                ]
            },
            score_threshold=0.7
        )
        
        # 4. Extract relevant documents
        retrieved_docs = []
        for hit in search_results:
            retrieved_docs.append({
                "content": hit.payload.get("content"),
                "source": hit.payload.get("source"),
                "doc_type": hit.payload.get("doc_type"),  # textbook, exam, exercise
                "score": hit.score
            })
        
        # 5. Assemble context
        context = self.assemble_context(retrieved_docs)
        
        return {
            "tier": 2,
            "retrieved_docs": retrieved_docs,
            "context": context,
            "num_docs": len(retrieved_docs),
            "avg_score": sum(d["score"] for d in retrieved_docs) / len(retrieved_docs) if retrieved_docs else 0,
            "next_node": "llm_synthesis_node"
        }
    
    def assemble_context(self, docs: List[Dict]) -> Dict:
        """Organize retrieved docs by type"""
        context = {
            "textbook_content": [],
            "example_exercises": [],
            "exam_questions": [],
            "solutions": []
        }
        
        for doc in docs:
            doc_type = doc.get("doc_type", "unknown")
            content = doc.get("content", "")
            
            if doc_type == "textbook":
                context["textbook_content"].append(content)
            elif doc_type == "exercise":
                context["example_exercises"].append(content)
            elif doc_type == "exam":
                context["exam_questions"].append(content)
            elif doc_type == "solution":
                context["solutions"].append(content)
        
        return context
```

### 5️⃣ **LLMSynthesisNode** (Tier 2 - Part 2)

```python
class LLMSynthesisNode(CreateExerciseNodeInterface):
    """Generate exercises using RAG context + LLM"""
    
    async def run(self, state: CreateExerciseState):
        grade = state.get("grade")
        subject = state.get("subject")
        topic = state.get("topic")
        question = state.get("question")
        context = state.get("context", {})
        
        # 1. Load subject-specific prompt template
        prompt = self.build_prompt(
            prompt_type=subject,  # math, physics, chemistry, etc.
            grade=grade,
            topic=topic,
            question=question,
            textbook_content="\n".join(context.get("textbook_content", [])),
            example_exercises="\n".join(context.get("example_exercises", [])),
            exam_questions="\n".join(context.get("exam_questions", [])),
            solutions="\n".join(context.get("solutions", []))
        )
        
        # 2. Call LLM
        messages = [
            {"role": "system", "content": "Bạn là chuyên gia giáo dục, tạo bài tập dựa trên tài liệu tham khảo."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # 3. Parse exercises from response
        exercises = self.parse_exercises(response.content)
        
        return {
            "tier": 2,
            "exercises": exercises,
            "generation_method": "rag_llm",
            "num_retrieved_docs": state.get("num_docs", 0),
            "processing_time": "2-4s"
        }
    
    def parse_exercises(self, content: str) -> List[Dict]:
        """Parse exercises from LLM response"""
        # Simple parsing logic - can be enhanced
        exercises = []
        lines = content.split("\n")
        
        current_exercise = {}
        for line in lines:
            if line.startswith("**Câu"):
                if current_exercise:
                    exercises.append(current_exercise)
                current_exercise = {"question": line}
            elif line.startswith("**Đáp án"):
                current_exercise["answer"] = line
            elif line.startswith("**Lời giải"):
                current_exercise["solution"] = line
        
        if current_exercise:
            exercises.append(current_exercise)
        
        return exercises
```

### 6️⃣ **LLMFallbackNode** (Tier 3)

```python
class LLMFallbackNode(CreateExerciseNodeInterface):
    """Pure LLM generation without RAG"""
    
    async def run(self, state: CreateExerciseState):
        grade = state.get("grade")
        subject = state.get("subject")
        topic = state.get("topic")
        question = state.get("question")
        fallback_reason = state.get("fallback_reason", "unknown")
        
        logger.warning(
            f"Using LLM fallback for grade={grade}, subject={subject}, "
            f"reason={fallback_reason}"
        )
        
        # Generic prompt without RAG context
        prompt = self.build_generic_prompt(
            grade=grade,
            subject=subject,
            topic=topic,
            question=question
        )
        
        # Call LLM
        messages = [
            {"role": "system", "content": "Bạn là chuyên gia giáo dục."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # Parse exercises
        exercises = self.parse_exercises(response.content)
        
        # Validate difficulty
        if not self.validate_grade_appropriate(exercises, grade):
            logger.warning("Exercises may not be grade-appropriate")
        
        return {
            "tier": 3,
            "exercises": exercises,
            "generation_method": "llm_fallback",
            "fallback_reason": fallback_reason,
            "processing_time": "3-5s"
        }
    
    def build_generic_prompt(self, grade, subject, topic, question) -> str:
        return f"""Tạo bài tập {subject} cho học sinh lớp {grade}.

Chủ đề: {topic}
Yêu cầu: {question}

QUAN TRỌNG:
- Độ khó phù hợp với lớp {grade}
- Không dùng kiến thức vượt chương trình
- Tạo 3-5 bài tập
- Kèm đáp án chi tiết

Hãy tạo bài tập theo yêu cầu."""
```

---

## 🗄️ RAG DATA ARCHITECTURE

### Vector Database Schema (Qdrant/Elasticsearch)

```python
EDUCATIONAL_MATERIALS_SCHEMA = {
    "collection_name": "educational_materials",
    "vector_size": 768,  # vietnamese-sbert embedding size
    "fields": {
        # Metadata
        "doc_id": "string",
        "doc_type": "enum[textbook,exercise,exam,solution]",
        "subject": "enum[toán,lý,hóa,sinh,văn,sử,địa,anh]",
        "grade": "int[1-12]",
        "topic": "string",
        "chapter": "string",
        
        # Content
        "content": "text",  # Main content (embedded)
        "title": "string",
        "difficulty": "enum[easy,medium,hard]",
        
        # Source tracking
        "source": "string",  # SGK lớp X, Đề thi 2023, etc.
        "page_number": "int",
        "created_at": "timestamp",
        
        # Quality
        "verified": "boolean",
        "quality_score": "float[0-1]"
    }
}
```

### Data Ingestion Pipeline

```python
class EducationalDataIngestion:
    """Ingest and embed educational materials"""
    
    async def ingest_textbook(self, pdf_path: str, grade: int, subject: str):
        """Extract and embed textbook content"""
        # 1. Extract text from PDF
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        
        # 2. Chunk text (by page or section)
        chunks = []
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            
            # Split into smaller chunks if needed (max 512 tokens)
            sub_chunks = self.split_text(text, max_length=512)
            
            for chunk_id, chunk_text in enumerate(sub_chunks):
                chunks.append({
                    "content": chunk_text,
                    "doc_type": "textbook",
                    "subject": subject,
                    "grade": grade,
                    "source": f"SGK {subject} lớp {grade}",
                    "page_number": page_num + 1,
                    "chunk_id": chunk_id
                })
        
        # 3. Generate embeddings
        embeddings = self.embed_model.encode([c["content"] for c in chunks])
        
        # 4. Upload to Qdrant
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            points.append({
                "id": f"textbook_{subject}_{grade}_{i}",
                "vector": embedding.tolist(),
                "payload": chunk
            })
        
        self.qdrant.upsert(
            collection_name="educational_materials",
            points=points
        )
        
        logger.info(f"Ingested {len(chunks)} chunks from {pdf_path}")
    
    async def ingest_exam_papers(self, exam_json: str):
        """Ingest exam questions with solutions"""
        import json
        
        with open(exam_json) as f:
            exams = json.load(f)
        
        points = []
        for exam in exams:
            for question in exam["questions"]:
                # Embed question + solution together
                content = f"{question['text']}\n\nLời giải: {question['solution']}"
                embedding = self.embed_model.encode(content).tolist()
                
                points.append({
                    "id": f"exam_{exam['year']}_{question['id']}",
                    "vector": embedding,
                    "payload": {
                        "content": content,
                        "doc_type": "exam",
                        "subject": exam["subject"],
                        "grade": exam["grade"],
                        "source": f"Đề thi {exam['year']}",
                        "difficulty": question.get("difficulty", "medium")
                    }
                })
        
        self.qdrant.upsert(
            collection_name="educational_materials",
            points=points
        )
```

### Data Sources

| Source Type | Format | Count (Target) | Status |
|-------------|--------|----------------|--------|
| SGK điện tử | PDF | 50+ books | 🔄 Ingesting |
| Đề thi các năm | JSON | 500+ exams | 📝 Planned |
| Bài tập mẫu | Markdown | 1000+ exercises | 📝 Planned |
| Tài liệu tham khảo | PDF/Web | 200+ docs | 📝 Planned |

---

## ⚡ PERFORMANCE OPTIMIZATION

### 1. **Tier-based Routing Performance**

| Tier | Processing Method | Avg Latency | Use Case % |
|------|-------------------|-------------|------------|
| **Tier 1** | Rule-based | < 1s | 30% (Toán 1-5) |
| **Tier 2** | RAG + LLM | 2-4s | 60% (Lớp 6-12) |
| **Tier 3** | LLM Fallback | 3-5s | 10% (Edge cases) |

### 2. **RAG Optimization Techniques**

```python
# Technique 1: Vector cache for common queries
class RAGCache:
    """Cache retrieval results for common queries"""
    
    def __init__(self):
        self.cache = {}  # {query_hash: (docs, timestamp)}
        self.ttl = 3600  # 1 hour
    
    def get(self, query: str) -> Optional[List]:
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        if query_hash in self.cache:
            docs, timestamp = self.cache[query_hash]
            if time.time() - timestamp < self.ttl:
                return docs
        return None
    
    def set(self, query: str, docs: List):
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        self.cache[query_hash] = (docs, time.time())

# Technique 2: Hybrid search (vector + keyword)
async def hybrid_search(query: str, grade: int, subject: str):
    """Combine vector similarity + keyword matching"""
    
    # Vector search
    vector_results = await qdrant.search(
        query_vector=embed(query),
        limit=20
    )
    
    # Keyword search (Elasticsearch)
    keyword_results = await es.search(
        query={
            "bool": {
                "must": [
                    {"match": {"content": query}},
                    {"term": {"grade": grade}},
                    {"term": {"subject": subject}}
                ]
            }
        },
        size=20
    )
    
    # Merge and rerank
    combined = merge_and_rerank(vector_results, keyword_results)
    return combined[:10]

# Technique 3: Query expansion
def expand_query(original_query: str, subject: str) -> List[str]:
    """Expand query with synonyms and related terms"""
    
    SYNONYMS = {
        "phương trình": ["giải phương trình", "hệ phương trình", "nghiệm"],
        "hình học": ["tính diện tích", "chu vi", "thể tích"],
        "đạo hàm": ["vi phân", "đạo hàm cấp 1", "quy tắc đạo hàm"]
    }
    
    queries = [original_query]
    for key, synonyms in SYNONYMS.items():
        if key in original_query:
            for syn in synonyms:
                queries.append(original_query.replace(key, syn))
    
    return queries
```

### 3. **LLM Call Optimization**

```python
# Batch processing for multiple exercises
async def batch_generate(requests: List[Dict]) -> List[Dict]:
    """Generate exercises in batch to reduce LLM calls"""
    
    # Group by subject + grade
    groups = defaultdict(list)
    for req in requests:
        key = f"{req['subject']}_{req['grade']}"
        groups[key].append(req)
    
    results = []
    for group_key, group_reqs in groups.items():
        # Single LLM call for the group
        batch_prompt = create_batch_prompt(group_reqs)
        response = await llm.ainvoke(batch_prompt)
        
        # Parse and distribute results
        exercises_list = parse_batch_response(response)
        results.extend(exercises_list)
    
    return results
```

---

## 📊 PERFORMANCE TARGETS vs CURRENT

| Metric | BA Target | Current | Status |
|--------|-----------|---------|--------|
| **Tier 1 Latency** | ≤ 1s | < 1s | ✅ |
| **Tier 2 Latency** | ≤ 4s | 2-4s | ✅ |
| **Tier 3 Latency** | ≤ 5s | 3-5s | ✅ |
| **Test Pass Rate** | ≥ 85% | 🔄 Testing | 📝 |
| **RAG Recall@10** | ≥ 80% | 🔄 Measuring | 📝 |
| **Exercise Quality** | ≥ 4.0/5 | 🔄 Measuring | 📝 |

---

## 🔐 ERROR HANDLING (BA Specification)

### Error Codes

```python
ERROR_CODES = {
    "E01": {
        "message": "Chưa biết môn học nào? Bạn muốn tạo bài tập môn gì?",
        "action": "ask_for_subject",
        "suggestions": ["Toán", "Lý", "Hóa", "Sinh", "Văn"]
    },
    "E02": {
        "message": "Môn {subject} không phù hợp với lớp {grade}",
        "action": "clarify_subject_grade",
        "suggestions_fn": "get_valid_subjects(grade)"
    },
    "E03": {
        "message": "Học sinh lớp mấy vậy?",
        "action": "ask_for_grade",
        "suggestions": ["Lớp 1", "Lớp 3", "Lớp 5", "Lớp 9", "Lớp 12"]
    },
    "E04": {
        "message": "Chưa có thông tin lớp và môn học. Bạn cần tạo bài tập cho lớp mấy, môn gì?",
        "action": "ask_for_both",
        "suggestions": ["Toán lớp 3", "Lý lớp 9", "Hóa lớp 10"]
    },
    "E05": {
        "message": "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau.",
        "action": "system_error",
        "retry": True
    }
}
```

### Fallback Strategy

```
┌─────────────────────────────────────┐
│         TIER 1 FAILS?               │
│  (Rule engine error/unknown type)   │
└─────────────────────────────────────┘
                ↓
        ┌──────────────┐
        │ Fallback to  │
        │   TIER 2     │
        │   (RAG)      │
        └──────────────┘
                ↓
┌─────────────────────────────────────┐
│         TIER 2 FAILS?               │
│  (No docs found / low relevance)    │
└─────────────────────────────────────┘
                ↓
        ┌──────────────┐
        │ Fallback to  │
        │   TIER 3     │
        │   (LLM)      │
        └──────────────┘
                ↓
┌─────────────────────────────────────┐
│         TIER 3 FAILS?               │
│  (LLM error / timeout)              │
└─────────────────────────────────────┘
                ↓
        ┌──────────────┐
        │ Return E05   │
        │ System Error │
        └──────────────┘
```

---

## 🧪 TESTING STRATEGY

### Test Categories (30+ tests per node)

#### 1. **Tier 1 Rule-based Tests**

```python
TIER_1_TESTS = [
    # Addition
    {"grade": 1, "type": "addition", "expected_count": 5, "expected_time": "<1s"},
    {"grade": 3, "type": "addition", "expected_range": (1, 1000)},
    
    # Subtraction
    {"grade": 2, "type": "subtraction", "expected_no_negative": True},
    
    # Multiplication
    {"grade": 4, "type": "multiplication", "expected_count": 5},
    
    # Find x
    {"grade": 5, "type": "find_x", "expected_solution_steps": True},
    
    # Geometry
    {"grade": 3, "type": "perimeter", "shape": "square"},
    {"grade": 4, "type": "area", "shape": "rectangle"},
    
    # Edge cases
    {"grade": 1, "type": "unknown", "expected_fallback": "tier2"},
    {"grade": 6, "type": "addition", "expected_tier": 2}  # Grade out of range
]
```

#### 2. **Tier 2 RAG Tests**

```python
TIER_2_TESTS = [
    # RAG retrieval
    {
        "grade": 9,
        "subject": "toán",
        "topic": "phương trình bậc hai",
        "expected_docs": ">= 5",
        "expected_relevance": ">= 0.7"
    },
    
    # Cross-subject
    {
        "grade": 10,
        "subject": "lý",
        "topic": "định luật Ohm",
        "expected_docs": ">= 3",
        "contains": ["điện trở", "cường độ"]
    },
    
    # No docs found (fallback to Tier 3)
    {
        "grade": 11,
        "subject": "hóa",
        "topic": "very_obscure_topic",
        "expected_fallback": "tier3"
    }
]
```

#### 3. **Tier 3 LLM Fallback Tests**

```python
TIER_3_TESTS = [
    # Generic fallback
    {
        "grade": 12,
        "subject": "văn",
        "topic": "phân tích tác phẩm",
        "expected_tier": 3,
        "expected_quality": ">= 3.5/5"
    },
    
    # Grade-appropriate check
    {
        "grade": 1,
        "subject": "toán",
        "topic": "complex_calculus",  # Should be rejected
        "expected_error": "E02"
    }
]
```

### E2E Integration Tests

```python
async def test_e2e_flow():
    """Test full pipeline from request to response"""
    
    # Test 1: Tier 1 happy path
    response = await create_exercise_pipeline({
        "grade": 3,
        "subject": "toán",
        "topic": "phép cộng",
        "content": "Tạo 5 bài tập cộng hai số"
    })
    
    assert response["tier"] == 1
    assert len(response["exercises"]) == 5
    assert response["processing_time"] < 1.0
    
    # Test 2: Tier 2 happy path
    response = await create_exercise_pipeline({
        "grade": 9,
        "subject": "toán",
        "topic": "phương trình bậc hai",
        "content": "Tạo bài tập về phương trình bậc hai"
    })
    
    assert response["tier"] == 2
    assert response["num_retrieved_docs"] >= 5
    assert response["processing_time"] < 4.0
    
    # Test 3: Error handling
    response = await create_exercise_pipeline({
        "content": "Tạo bài tập"  # Missing grade & subject
    })
    
    assert response["error_code"] == "E04"
    assert len(response["suggestions"]) >= 3
```

---

## 🚀 IMPLEMENTATION ROADMAP

### Phase 1: Core Pipeline (Week 1-2)
- ✅ ValidationNode
- ✅ ScopeClassifierNode  
- ✅ RuleBasedExerciseNode (Tier 1)
- 📝 Basic error handling

### Phase 2: RAG Integration (Week 3)
- 📝 Setup Qdrant/Elasticsearch
- 📝 Data ingestion pipeline
- 📝 RAGRetrievalNode
- 📝 LLMSynthesisNode (Tier 2)

### Phase 3: Testing & Optimization (Week 4)
- 📝 30+ unit tests per node
- 📝 E2E integration tests
- 📝 Performance tuning
- 📝 Documentation

---

## 📚 REFERENCES

- BA Specification: `edu-agent.md`
- Source Code: [tammi-agent-education](https://github.com/cuongnguyengit/tammi-agent-education)
- API Gateway: [tammi-agent-api-gateway](https://github.com/cuongnguyengit/tammi-agent-api-gateway)
- LangGraph: https://langchain-ai.github.io/langgraph/
- Qdrant: https://qdrant.tech/documentation/
- Vietnamese SBERT: https://huggingface.co/keepitreal/vietnamese-sbert

---

**Version**: 2.0.0 (Rule + RAG + LLM Architecture)  
**Last Updated**: 2025-12-05  
**Status**: 🏗️ In Development (Tier 1 complete, Tier 2 in progress)
