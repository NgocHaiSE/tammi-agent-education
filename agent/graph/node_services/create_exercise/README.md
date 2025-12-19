# Create Exercise Node - Multi-Tier Architecture

## Tổng quan

Create Exercise Node sử dụng kiến trúc **3-tier** để tối ưu hóa chất lượng, tốc độ và chi phí khi tạo bài tập:

- **Tier 1 (Rule-based)**: Template-based generation - Nhanh, rẻ, chất lượng ổn định
- **Tier 2 (RAG)**: Retrieval-Augmented Generation - Cân bằng giữa chất lượng và tốc độ
- **Tier 3 (LLM Fallback)**: Pure LLM generation - Chất lượng cao nhất, chậm hơn, tốn chi phí


Các node sử dụng:
- Các node cho sinh đề: rule_based_node, rag_node, llm_fallback_node
- node validate: validation_node kiểm tra yêu cầu người dùng, check có thiếu các trường thông tin (Tên môn, lớp học) hay không và trả ra các lỗi E01, E02,E03 tương ứng
- scope_classifier_node phân loại tier câu hỏi route tới các hướng giải quyết khác nhau
- quality_check_node để kiểm tra chất lượng câu hỏi (có phù hợp với đối tượng học sinh, kết quả số có đẹp không), có thể bỏ đi để tăng tốc độ xử lý


## Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│                    CREATE EXERCISE NODE                         │
│                  (Main Entry Point)                             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CREATE EXERCISE SUBGRAPH                       │
│                                                                 │
│  ┌──────────────┐                                              │
│  │ValidationNode│  Validate input (grade, subject, topic)      │
│  └──────┬───────┘                                              │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────┐                                       │
│  │ScopeClassifierNode  │  Route to appropriate tier            │
│  │ (Tier Router)       │                                       │
│  └──────┬──────────────┘                                       │
│         │                                                       │
│    ┌────┴────┬──────────┬────────┐                            │
│    │         │          │        │                             │
│  Tier 1    Tier 2    Tier 3   ERROR                            │
│    │         │          │        │                             │
│    ▼         ▼          ▼        ▼                             │
│ ┌─────┐  ┌─────┐  ┌─────────┐  ┌──────────┐                  │
│ │Rule │  │ RAG │  │   LLM   │  │ Response │                  │
│ │Based│  │Node │  │Fallback │  │ Builder  │                  │
│ └──┬──┘  └──┬──┘  └────┬────┘  └────┬─────┘                  │
│    │        │          │             │                         │
│    └────────┴──────────┴─────────────┘                        │
│                      │                                          │
│                      ▼                                          │
│              ┌───────────────┐                                 │
│              │QualityCheckNode│                                │
│              └───────┬───────┘                                 │
│                      │                                          │
│                      ▼                                          │
│              ┌──────────────┐                                  │
│              │ResponseBuilder│                                 │
│              └──────┬───────┘                                  │
│                     │                                           │
└─────────────────────┼───────────────────────────────────────────┘
                      │
                      ▼
                    OUTPUT
```

---

## ExerciseMemory - Session-Aware Context Management

### Overview

**ExerciseMemory** là hệ thống quản lý session và context cho Create Exercise, cho phép:
- ✅ **Multi-turn conversations**: Hỗ trợ hội thoại nhiều lượt
- ✅ **Context continuity**: Tự động điền thông tin từ request trước
- ✅ **Duplicate avoidance**: Tránh tạo câu hỏi trùng lặp
- ✅ **Preference learning**: Học sở thích người dùng
- ✅ **Persistent storage**: Lưu trữ JSON file

### Key Features

#### 1. Context Filling
```python
# Request 1
"Tạo bài tập Toán lớp 6 về phân số"

# Request 2 (cùng session)
"Tạo thêm 3 bài khó hơn"  # ✅ Tự động biết: Toán, lớp 6, phân số
```

#### 2. Duplicate Avoidance
```python
# Lần 1: Tạo 5 bài
["1/2 + 1/3 = ?", "Rút gọn 4/8", ...]

# Lần 2: Tạo 3 bài khác
# ✅ KHÔNG lặp lại các câu đã tạo
["2/5 + 3/7 = ?", "So sánh 3/4 và 5/6", ...]
```

#### 3. Preference Learning
```python
memory.get_preferences()
# {
#   "preferred_subjects": ["toán", "tiếng anh"],
#   "preferred_grades": [6, 7],
#   "preferred_difficulty": "trung bình",
#   "preferred_exercise_type": "trắc nghiệm"
# }
```

### Implementation

**File**: `exercise_memory.py`

**Storage**: `exercise_memory_cache.json`

**Integration Points**:
- `ValidationNode`: Context filling + preference update
- `ResponseBuilderNode`: Save exercise history
- `RAGNode`: Duplicate avoidance

### Usage Example

```python
from agent.graph.node_services.create_exercise.exercise_memory import ExerciseMemory

# Initialize with session
memory = ExerciseMemory(session_id="sess_123")

# Add exercise record
memory.add_exercise_record(
    request_params={
        "grade": 6,
        "subject": "toán",
        "topic": "phân số",
        "num_exercises": 5
    },
    exercises=[...],
    generation_metadata={"tier": 2, "method": "rag"}
)

# Get last context
context = memory.get_last_context()
# {"grade": 6, "subject": "toán", "topic": "phân số"}

# Get previous questions (for duplicate avoidance)
questions = memory.get_previous_questions(limit=20)

# Get statistics
stats = memory.get_stats()
# {"total_requests": 5, "total_exercises": 23, ...}
```

### Session Management

**Auto-reset on session change**:
```python
memory1 = ExerciseMemory(session_id="sess_1")
memory1.add_exercise_record(...)  # Saved

memory2 = ExerciseMemory(session_id="sess_2")
# ✅ Auto-reset: history cleared for new session
```

**Persistent storage**:
```json
{
  "session_id": "sess_123",
  "exercise_history": [...],
  "user_preferences": {...},
  "last_context": {...}
}
```

---


## Tier 1: Rule-based Generation

### Đặc điểm
- **Phương pháp**: Template-based, thuật toán logic thuần Python
- **Tốc độ**: Cực nhanh (< 1s)
- **Chi phí**: Miễn phí (không dùng LLM)
- **Chất lượng**: Ổn định, có thể dự đoán
- **Phạm vi**: Giới hạn ở các bài tập đơn giản, có cấu trúc rõ ràng

### Tiêu chí áp dụng

**Môn học**: 
- Toán
- Tiếng Việt (một số dạng)

**Lớp**: 1-5

**Loại bài tập**:
- Phép tính cơ bản (cộng, trừ, nhân, chia)
- So sánh số
- Tìm x đơn giản
- Bài toán lời văn có template
- Hình học cơ bản (chu vi, diện tích)

### Implementation

**File**: `subgraph/nodes/rule_based_node.py`

**Generator**: `subgraph/generators/rule_generator.py`

### Ví dụ

**Input**: 
- Grade: 3
- Subject: Toán
- Topic: Phân số
- Count: 5

**Output**:
```
1. 1/2 + 1/3 = ? → Đáp án: 5/6
2. Rút gọn 4/8 → Đáp án: 1/2
3. 2/3 × 3/4 = ? → Đáp án: 1/2
4. 5/6 - 1/3 = ? → Đáp án: 1/2
5. So sánh 2/3 và 3/4 → Đáp án: 2/3 < 3/4
```

**Performance**: < 1s, 0 token cost

---

## Tier 2: RAG (Retrieval-Augmented Generation)

### Đặc điểm
- **Phương pháp**: Tìm kiếm context từ database/vector store → LLM synthesis
- **Tốc độ**: Trung bình (2-5s)
- **Chi phí**: Trung bình (1 LLM call nhỏ)
- **Chất lượng**: Cao, dựa trên tài liệu thực tế
- **Phạm vi**: Bài tập trung bình, cần context cụ thể

### Tiêu chí áp dụng

**Môn học**: 
- Toán (nâng cao)
- Vật lý
- Hóa học
- Sinh học
- Lịch sử
- Địa lý

**Lớp**: 1-5

**Loại bài tập**:
- Cần context từ sách giáo khoa
- Dựa trên định lý, công thức cụ thể
- Bài tập có yêu cầu về kiến thức nền

### Implementation

**Flow**:
```python
1. Trích xuất từ khóa từ từ prompts và session
2. Tìm kiếm tài liệu liên quan trong cơ sở dữ liệu
3. Xếp hạng và chọn top K tài liệu khớp nhất
4. Build prompt với ngữ cảnh thu thập được
5. LLM generates bài tập dựa trên context
6. Validate và format output
```

### Tools & Dependencies

```python
# Vector Store
- Qdrant
- Embedding model: text-embedding-3-small

# Search Strategy
- Semantic search by topic
- Keyword filtering by grade + subject
- Hybrid search (semantic + keyword)
Vì là môn toán chủ yếu là ký tự nên sử dụng Hybrid search


## Tier 3: LLM Fallback (Pure Generation)

### Tiêu chí áp dụng

**Khi nào dùng**:
- Không match Tier 1 & 2
- Topic phức tạp, đặc biệt
- Yêu cầu sáng tạo cao
- Môn học đặc thù
- Ngoài lớp học cho phép

**Môn học**: Tất cả

**Lớp**: Tất cả

**Loại bài tập**: Tất cả

### Implementation

### Prompt Engineering
Xây dựng 1 prompt template mẫu cho trường hợp fallback

```python
prompt = f"""Bạn là giáo viên {subject} giỏi. Hãy tạo {num_exercises} bài tập 
{subject} cho học sinh lớp {grade} về chủ đề "{topic}".

Yêu cầu:
- Tạo đúng {num_exercises} bài tập
- Độ khó phù hợp với lớp {grade}
- Bài tập liên quan chặt chẽ đến chủ đề "{topic}"
- Mỗi bài tập phải có câu hỏi và đáp án rõ ràng
- Đáp án phải chính xác và có giải thích (nếu cần)

Format trả về (JSON):
[
  {{"question": "Câu hỏi 1", "answer": "Đáp án 1", "explanation": "..."}},
  {{"question": "Câu hỏi 2", "answer": "Đáp án 2", "explanation": "..."}},
  ...
]

Hãy tạo bài tập ngay:"""
```

## Scope Classifier (Tier Router)

### Routing Logic

**File**: `subgraph/nodes/scope_classifier_node.py`

```python
class ScopeClassifierNode(NodeBase):
    def route(self, grade, subject, topic, exercise_type):
        # Tier 1: Rule-based
        if self._is_tier1_eligible(grade, subject, exercise_type):
            return "tier_1_rule_based"
        
        # Tier 2: RAG
        if self._is_tier2_eligible(grade, subject, topic):
            return "tier_2_rag"
        
        # Tier 3: LLM Fallback
        return "tier_3_llm_fallback"
```

### Decision Tree

```
                    ┌──────────────┐
                    │ Validation OK│
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Classifier  │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Tier 1?    │  │   Tier 2?    │  │   Tier 3     │
│              │  │              │  │              │
│• Toán 1-5    │  │• Lớp 1-5     │  │• All other   │
│• Simple ops  │  │• Has context │  │• Complex     │
│• Templates   │  │• In database │  │• Creative    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                  │
       ▼                 ▼                  ▼
  Rule-based           RAG              LLM Fallback

```

---

## Quality Control

### Quality Check Node

**File**: `subgraph/nodes/quality_check_node.py`

**Checks**:
```python
✓ Exercise count: 3 ≤ count ≤ 10
✓ Required fields: question, answer
✓ Answer format: non-empty, reasonable length
✓ Difficulty matches grade level
✓ Topic relevance: keywords present
✓ No duplicates
✓ Format consistency
```

**Actions on failure**:
- Tier 1/2: Retry with different parameters
- Tier 3: Return with quality warnings
- Log issues for monitoring

---



