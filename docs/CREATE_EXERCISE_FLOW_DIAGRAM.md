# Create Exercise - Parent-Subgraph Connection Flow

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MAIN AGENT GRAPH                                │
│                          (GraphState)                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ User Request
                                   │ {grade: "5", subject: "Toán", topic: "Phân số"}
                                   ▼
                    ┌──────────────────────────────┐
                    │ SubIntentClassificationNode  │
                    │  - Classify intent           │
                    │  - Set sub_intent            │
                    └──────────────────────────────┘
                                   │
                                   │ sub_intent = "create_exercise"
                                   ▼
                         ┌─────────────────┐
                         │ route_to_node() │
                         │  (Router)       │
                         └─────────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
    ┌───────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
    │ search_material│   │ correct_exercise│   │ create_exercise │ ◄── Selected
    └────────────────┘   └─────────────────┘   └─────────────────┘
                                                          │
                                                          │ GraphState
                                                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CREATE EXERCISE NODE                               │
│                     (CreateExerciseNode)                                │
│  - Prepare subgraph input (CreateExerciseState)                         │
│  - Invoke subgraph                                                      │
│  - Transform output back to GraphState                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ CreateExerciseState
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   CREATE EXERCISE SUBGRAPH                              │
│                   (CreateExerciseState)                                 │
│                                                                         │
│   Entry                                                                 │
│     ▼                                                                   │
│   ┌─────────────────┐                                                  │
│   │ ValidationNode  │                                                  │
│   │ - Extract params│                                                  │
│   │ - Validate input│                                                  │
│   └────────┬────────┘                                                  │
│            │                                                            │
│       ┌────┴────┐                                                      │
│       │ Valid?  │                                                      │
│       └────┬────┘                                                      │
│            │ Yes                                                        │
│            ▼                                                            │
│   ┌────────────────────┐                                               │
│   │ScopeClassifierNode │                                                    │
│   │ - Check tier       │                                               │
│   │ - Route execution  │                                               │
│   └─────────┬──────────┘                                               │
│             │                                                           │
│      ┌──────┴──────┐                                                   │
│      │   Tier?     │                                                   │
│      └──────┬──────┘                                                   │
│             │                                                           │
│    ┌────────┴────────--------------                                                │
│    │               |              │                                                 │
│  Tier 1            Tier2         Tier 3                                              │
│    │                              │                                                 │
│    ▼                 ▼                                                 │
│ ┌─────────────┐                               ┌──────────────┐                                     │
│ │RuleBasedNode│      RAG          │LLMFallbackNode│                                    │
│ │- Template   │     - Qdrant              │- LLM Generate │                                    │
│ │- Fast (<1s) │     - LLM reasoning                   │                                                
│ └──────┬──────┘                               └──────┬────────┘                                    
│        │                 │                                             │
│        └────────┬────────┘                                             │
│                 │ exercises                                            │
│                 ▼                                                      │
│        ┌─────────────────┐                                             │
│        │QualityCheckNode │                                             │
│        │- Validate output│                                             │
│        │- Check quality  │                                             │
│        └────────┬────────┘                                             │
│                 │ quality_passed                                       │
│                 ▼                                                      │
│      ┌────────────────────┐                                            │
│      │ResponseBuilderNode │                                            │
│      │- Format exercises  │                                            │
│      │- Build AIMessage   │                                            │
│      │- Add suggestions   │                                            │
│      └─────────┬──────────┘                                            │
│                │                                                        │
│                ▼                                                        │
│              END                                                        │
│                                                                         │
└─────────────────┬───────────────────────────────────────────────────────┘
                  │ node_responses + data_artifacts
                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CREATE EXERCISE NODE                               │
│  - Extract node_responses                                               │
│  - Extract data_artifacts (exercises, metadata)                         │
│  - Return to parent graph                                               │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ {node_responses, data_artifacts}
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         MAIN AGENT GRAPH                                │
│  - Merge node_responses                                                 │
│  - Merge data_artifacts                                                 │
│  - Route to END                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                               ┌───────┐
                               │  END  │
                               └───────┘
```

## State Transformation

### Input: GraphState → CreateExerciseState

```python
# In CreateExerciseNode.run()

GraphState = {
    "request": {
        "payload": {
            "content": "Tạo bài tập toán lớp 6",
            "metadata": {
                "grade": "6",
                "subject": "Toán",
                "topic": "Phân số",
                "num_exercises": 5
            }
        }
    },
    "history_chat": [...]
}

         ↓ Transform

CreateExerciseState = {
    "request": {...},              # From GraphState
    "history_chat": [...],         # From GraphState
    "validated": False,            # Initialize
    "grade": None,                 # Will be filled by ValidationNode
    "subject": None,               # Will be filled by ValidationNode
    "topic": None,                 # Will be filled by ValidationNode
    "exercise_type": None,         # Will be filled by ValidationNode
    "num_exercises": 5,            # From metadata
    "tier": 0,                     # Will be filled by ScopeClassifierNode
    "processing_method": "",       # Will be filled by ScopeClassifierNode
    "exercises": None,             # Will be filled by generation node
    "generation_metadata": {},     # Will be filled by generation node
    "quality_passed": False,       # Will be filled by QualityCheckNode
    "quality_issues": [],          # Will be filled by QualityCheckNode
    "node_responses": [],          # Will be filled by ResponseBuilderNode
    "suggestions": []              # Will be filled by ResponseBuilderNode
}
```

### Output: CreateExerciseState → GraphState

```python
# In CreateExerciseNode.run()

CreateExerciseState = {
    "validated": True,
    "grade": "6",
    "subject": "Toán",
    "topic": "Phân số",
    "exercise_type": "Tổng hợp",
    "tier": 1,
    "processing_method": "rule_based",
    "exercises": [
        {"question": "...", "answer": "..."},
        # ... more
    ],
    "generation_metadata": {
        "tier": 1,
        "method": "rule_based",
        "generated_count": 5
    },
    "quality_passed": True,
    "node_responses": [
        AIMessage(content="Đây là 5 bài tập...")
    ],
    "suggestions": ["Tạo thêm bài tập khó hơn", ...]
}

         ↓ Transform

GraphState Update = {
    "node_responses": [
        AIMessage(content="Đây là 5 bài tập...")
    ],
    "data_artifacts": {
        "exercises": [...],
        "generation_metadata": {...},
        "quality_passed": True,
        "quality_issues": [],
        "tier": 1,
        "processing_method": "rule_based"
    }
}
```

## Routing Logic

### 1. Main Graph Routing

```python
def _route_to_node(state: GraphState) -> str:
    """Route based on sub_intent"""
    sub_intent = state["request"]["payload"]["sub_intent"]
    
    mapping = {
        "create_exercise": "create_exercise",  # ← Routes here
        "search_material": "search_material",
        "correct_exercise": "correct_exercise",
        "tutor_subject": "tutor_subject"
    }
    
    return mapping.get(sub_intent, "default")
```

### 2. Subgraph Routing - After Validation

```python
def route_after_validation(state: CreateExerciseState) -> str:
    """Route based on validation result"""
    if state["validated"]:
        return "scope_classifier"  # Continue to classifier
    else:
        return "response_builder"  # Skip to error response
```

### 3. Subgraph Routing - After Classification

```python
def route_after_classifier(state: CreateExerciseState) -> str:
    """Route based on tier"""
    tier = state["tier"]
    
    if tier == 1:
        return "rule_based"      # Simple cases
    else:
        return "llm_fallback"    # Complex cases
```

### 4. Subgraph Routing - After Quality Check

```python
def route_after_quality(state: CreateExerciseState) -> str:
    """Always go to response builder"""
    return "response_builder"  # Format response (with or without issues)
```

## Data Flow Example

### Tier 1 Flow (Rule-based)

```
User Input:
  grade = "6"
  subject = "Toán"  
  topic = "Phân số"
  num_exercises = 5

     ↓ ValidationNode

State Update:
  validated = True
  grade = 6
  subject = "Toán"
  topic = "Phân số"
  exercise_type = "Tổng hợp"

     ↓ ScopeClassifierNode

State Update:
  tier = 1
  processing_method = "rule_based"

     ↓ RuleBasedNode

State Update:
  exercises = [
    {question: "Tính 1/2 + 1/3", answer: "5/6"},
    {question: "Rút gọn 4/8", answer: "1/2"},
    # ... 3 more
  ]
  generation_metadata = {
    tier: 1,
    method: "rule_based",
    generated_count: 5,
    generation_time: "<1s"
  }

     ↓ QualityCheckNode

State Update:
  quality_passed = True
  quality_issues = []

     ↓ ResponseBuilderNode

State Update:
  node_responses = [
    AIMessage(
      content="Đây là 5 bài tập Toán lớp 6 về Phân số:\n\n1. Tính 1/2 + 1/3...",
      additional_kwargs={
        "tts_message": "Đã tạo 5 bài tập Toán cho lớp 6."
      }
    )
  ]
  suggestions = [
    "Tạo bài tập phân số khó hơn",
    "Tạo bài tập về so sánh phân số"
  ]
```

### Tier 3 Flow (LLM Fallback)

```
User Input:
  grade = "12"
  subject = "Vật lý"
  topic = "Cơ học lượng tử"
  num_exercises = 3

     ↓ ValidationNode

State Update:
  validated = True
  grade = 12
  subject = "Vật lý"
  topic = "Cơ học lượng tử"
  exercise_type = "Tổng hợp"

     ↓ ScopeClassifierNode

State Update:
  tier = 3
  processing_method = "llm_fallback"

     ↓ LLMFallbackNode

State Update:
  exercises = [
    {question: "Nguyên lý bất định Heisenberg...", answer: "..."},
    {question: "Giải thích hiện tượng lượng tử hóa...", answer: "..."},
    {question: "Phương trình Schrödinger...", answer: "..."}
  ]
  generation_metadata = {
    tier: 3,
    method: "llm_fallback",
    model: "gpt-4",
    generated_count: 3,
    generation_time: "5.2s"
  }

     ↓ QualityCheckNode

State Update:
  quality_passed = True
  quality_issues = []

     ↓ ResponseBuilderNode

State Update:
  node_responses = [
    AIMessage(
      content="Đây là 3 bài tập Vật lý lớp 12 về Cơ học lượng tử:...",
      additional_kwargs={
        "tts_message": "Đã tạo 3 bài tập Vật lý cho lớp 12."
      }
    )
  ]
```

## Error Handling

### Validation Error Flow

```
User Input:
  grade = None  ← Missing!
  subject = "Toán"
  topic = "Phân số"

     ↓ ValidationNode

State Update:
  validated = False
  validation_errors = "E03"
  error_messages = "Vui lòng cho biết lớp học."
  
     ↓ Router (Skip to ResponseBuilder)

     ↓ ResponseBuilderNode

State Update:
  node_responses = [
    AIMessage(
      content="Vui lòng cho biết lớp học.",
      additional_kwargs={
        "tts_message": "Vui lòng cho biết lớp học.",
        "error_code": "E03"
      }
    )
  ]
```

### Quality Check Failure (Non-blocking)

```
     ↓ QualityCheckNode

State Update:
  quality_passed = False
  quality_issues = [
    "Exercise 2: Missing answer",
    "Too few exercises (expected 5, got 3)"
  ]

     ↓ ResponseBuilderNode

State Update:
  node_responses = [
    AIMessage(
      content="Đã tạo 3 bài tập (có một số vấn đề chất lượng)...",
      additional_kwargs={
        "quality_issues": ["..."],
        "warning": "Some exercises may need manual review"
      }
    )
  ]
```

## Performance Metrics

| Flow Type | Nodes Executed | LLM Calls | Avg Latency |
|-----------|---------------|-----------|-------------|
| Tier 1 (Rule-based) | 5 nodes | 0 | < 1s |
| Tier 3 (LLM Fallback) | 5 nodes | 1 | 3-8s |
| Validation Error | 2 nodes | 0 | < 200ms |

## Key Benefits

1. **Separation of Concerns**: Each node has single responsibility
2. **Dynamic Routing**: Intelligent tier selection (Rule-based vs LLM)
3. **Error Handling**: Graceful degradation with validation
4. **State Isolation**: Subgraph state independent from parent
5. **Testability**: Each node can be tested independently
6. **Extensibility**: Easy to add new tiers or nodes
7. **Performance**: Fast path for simple cases (Tier 1)
