# Create Exercise Subgraph - Parent Graph Integration

## Tổng quan

Document này mô tả cách tích hợp giữa **graph cha (Main Agent Graph)** và **subgraph Create Exercise**.

## Kiến trúc tổng thể

```
Main Agent Graph (GraphState)
    ↓
SubIntentClassificationNode → route_to_node()
    ↓
CreateExerciseNode (NodeBase)
    ↓
Create Exercise Subgraph (CreateExerciseState)
    ├─ ValidationNode
    ├─ ScopeClassifierNode (Router)
    ├─ RuleBasedNode (Tier 1)
    ├─ LLMFallbackNode (Tier 3)  
    ├─ QualityCheckNode
    └─ ResponseBuilderNode
    ↓
Return to CreateExerciseNode
    ↓
Return to Main Agent Graph
    ↓
END
```

## Chi tiết các thành phần

### 1. Main Agent Graph

**File**: `agent/graph/graph_builder.py`

**State**: `GraphState` (định nghĩa trong `agent/graph/graph_state.py`)

```python
class GraphState(TypedDict):
    request: Dict[str, Any]           # Request từ user
    history_chat: List[BaseMessage]   # Lịch sử chat
    node_responses: List[BaseMessage] # Responses từ các node
    data_artifacts: Dict[str, Any]    # Data artifacts
```

**Routing logic**:
```python
def _route_to_node(state: GraphState) -> str:
    sub_intent = state.get("request", {}).get("payload", {}).get("sub_intent")
    
    node_mapping = {
        SubIntents.CREATE_EXERCISE: "create_exercise",
        # ... other intents
    }
    
    return node_mapping.get(sub_intent, "default")
```

### 2. CreateExerciseNode (Parent Node)

**File**: `agent/graph/node_services/create_exercise/create_exercise.py`

**Vai trò**: Node trung gian giữa graph cha và subgraph

**Chức năng**:
1. Nhận `GraphState` từ graph cha
2. Chuẩn bị input cho subgraph (tạo `CreateExerciseState`)
3. Gọi subgraph và chờ kết quả
4. Trả về `node_responses` và `data_artifacts` cho graph cha

**Code**:
```python
@node_register(name="create_exercise", priority=85)
class CreateExerciseNode(NodeBase):
    def __init__(self, llm: BaseChatModel, **kwargs):
        super().__init__(name="create_exercise", llm=llm, **kwargs)
        self.subgraph = create_create_exercise_graph(self.llm, self)
    
    async def run(self, state: GraphState) -> Dict[str, Any]:
        # Chuẩn bị input cho subgraph
        subgraph_input = {
            "request": state.get("request", {}),
            "history_chat": state.get("history_chat", []),
            "validated": False,
            "grade": None,
            "subject": None,
            # ... các field khác
        }
        
        # Gọi subgraph
        result = await self.subgraph.ainvoke(subgraph_input)
        
        # Trả về cho graph cha
        return {
            "node_responses": result.get("node_responses", []),
            "data_artifacts": {
                "exercises": result.get("exercises", []),
                "generation_metadata": result.get("generation_metadata", {}),
                # ... metadata khác
            }
        }
```

### 3. Create Exercise Subgraph

**File**: `agent/graph/node_services/create_exercise/subgraph/builder.py`

**State**: `CreateExerciseState` (định nghĩa trong `subgraph/state.py`)

```python
class CreateExerciseState(TypedDict):
    # Input từ parent
    request: Dict[str, Any]
    history_chat: List[BaseMessage]
    
    # Validation phase
    validated: bool
    validation_errors: Optional[str]
    grade: Optional[str]
    subject: Optional[str]
    topic: Optional[str]
    exercise_type: Optional[str]
    num_exercises: int
    
    # Routing phase
    tier: int  # 1=RuleBased, 3=LLMFallback
    processing_method: str
    
    # Generation phase
    exercises: Optional[List[Dict[str, Any]]]
    generation_metadata: Dict[str, Any]
    
    # Quality check phase
    quality_passed: bool
    quality_issues: List[str]
    
    # Output
    node_responses: List[BaseMessage]
    suggestions: List[str]
```

**Nodes trong subgraph**:

1. **ValidationNode**: Validate input và extract parameters
   - Input: `request.payload.metadata` (grade, subject, topic, etc.)
   - Output: `validated`, `grade`, `subject`, `topic`, `exercise_type`
   - Routing: `validated=True` → ScopeClassifier, `validated=False` → ResponseBuilder

2. **ScopeClassifierNode**: Phân loại tier (Rule-based vs LLM)
   - Input: `grade`, `subject`, `exercise_type`
   - Output: `tier`, `processing_method`
   - Routing: `tier=1` → RuleBasedNode, `tier=3` → LLMFallbackNode

3. **RuleBasedNode** (Tier 1): Template-based generation
   - Input: `grade`, `subject`, `exercise_type`, `num_exercises`
   - Output: `exercises`, `generation_metadata`
   - Next: QualityCheckNode

4. **LLMFallbackNode** (Tier 3): LLM-based generation
   - Input: `grade`, `subject`, `topic`, `num_exercises`
   - Output: `exercises`, `generation_metadata`
   - Next: QualityCheckNode

5. **QualityCheckNode**: Kiểm tra chất lượng exercises
   - Input: `exercises`, `grade`
   - Output: `quality_passed`, `quality_issues`
   - Next: ResponseBuilderNode

6. **ResponseBuilderNode**: Build final response
   - Input: `exercises`, `validated`, `quality_passed`
   - Output: `node_responses`, `suggestions`
   - Next: END

## Flow thực thi

### Happy Path (Tier 1 - Rule-based)

```
1. Main Graph receives request
   ↓
2. SubIntentClassification → sub_intent="create_exercise"
   ↓
3. route_to_node() → "create_exercise"
   ↓
4. CreateExerciseNode.run(GraphState)
   ↓
5. Prepare CreateExerciseState input
   ↓
6. subgraph.ainvoke(CreateExerciseState)
   ├─ ValidationNode
   │  └─ Extract: grade=6, subject="Toán", topic="Phân số"
   ↓
   ├─ ScopeClassifierNode
   │  └─ Check: Tier 1 eligible (simple case)
   ↓
   ├─ RuleBasedNode
   │  └─ Generate: 5 exercises from template
   ↓
   ├─ QualityCheckNode
   │  └─ Validate: quality_passed=True
   ↓
   └─ ResponseBuilderNode
      └─ Format: AIMessage with exercises
   ↓
7. Return CreateExerciseState with node_responses
   ↓
8. CreateExerciseNode extracts result
   ↓
9. Return to Main Graph: {node_responses, data_artifacts}
   ↓
10. Main Graph → END
```

### Alternative Path (Tier 3 - LLM Fallback)

```
6. subgraph.ainvoke(CreateExerciseState)
   ├─ ValidationNode
   │  └─ Extract: grade=12, subject="Vật lý", topic="Cơ học lượng tử"
   ↓
   ├─ ScopeClassifierNode
   │  └─ Check: Tier 3 (complex topic)
   ↓
   ├─ LLMFallbackNode
   │  └─ LLM Generate: Custom exercises
   ↓
   ├─ QualityCheckNode
   │  └─ Validate: quality_passed=True
   ↓
   └─ ResponseBuilderNode
      └─ Format: AIMessage with exercises
```

### Error Path (Validation Failed)

```
6. subgraph.ainvoke(CreateExerciseState)
   ├─ ValidationNode
   │  └─ Error: Missing grade (E03)
   ↓
   └─ ResponseBuilderNode (direct)
      └─ Format: AIMessage with error
```

## State Mapping

### GraphState → CreateExerciseState (Input)

```python
# CreateExerciseNode prepares input
subgraph_input = {
    # From GraphState
    "request": state.get("request", {}),
    "history_chat": state.get("history_chat", []),
    
    # Initialize subgraph fields
    "validated": False,
    "validation_errors": None,
    "grade": None,
    "subject": None,
    "topic": None,
    "exercise_type": None,
    "num_exercises": metadata.get("num_exercises", 5),
    "tier": 0,
    "processing_method": "",
    "exercises": None,
    "generation_metadata": {},
    "quality_passed": False,
    "quality_issues": [],
    "node_responses": [],
    "suggestions": [],
    "metadata": metadata,
}
```

### CreateExerciseState → GraphState (Output)

```python
# CreateExerciseNode extracts result
return {
    "node_responses": result.get("node_responses", []),
    "data_artifacts": {
        "exercises": result.get("exercises", []),
        "generation_metadata": result.get("generation_metadata", {}),
        "quality_passed": result.get("quality_passed", False),
        "quality_issues": result.get("quality_issues", []),
        "tier": result.get("tier", 0),
        "processing_method": result.get("processing_method", ""),
        "validation_errors": result.get("validation_errors"),
        "error_messages": result.get("error_messages"),
    }
}
```

## API Request Example

### Input Request (từ user)

```json
{
  "session_id": "sess_123",
  "request_id": "req_456",
  "payload": {
    "type": "text",
    "content": "Tạo bài tập toán lớp 6 về phân số",
    "intent": "education",
    "sub_intent": null,  // Sẽ được classify thành "create_exercise"
    "metadata": {
      "grade": "6",
      "subject": "Toán",
      "topic": "Phân số",
      "num_exercises": 5
    }
  }
}
```

### Output Response (từ agent)

```json
{
  "node_responses": [
    {
      "type": "ai",
      "content": "Đây là 5 bài tập Toán lớp 6 về Phân số:\n\n1. ...\n2. ...",
      "additional_kwargs": {
        "tts_message": "Đã tạo 5 bài tập Toán cho lớp 6."
      }
    }
  ],
  "data_artifacts": {
    "exercises": [
      {"question": "...", "answer": "..."},
      // ... 4 more
    ],
    "generation_metadata": {
      "tier": 1,
      "method": "rule_based",
      "generated_count": 5
    },
    "quality_passed": true,
    "quality_issues": []
  }
}
```

## Error Handling

### Validation Errors

**E01**: Missing subject
```json
{
  "error_code": "E01",
  "error_messages": "Vui lòng cho biết môn học bạn muốn tạo bài tập."
}
```

**E02**: Invalid grade-subject combination
```json
{
  "error_code": "E02",
  "error_messages": "Môn Toán không có ở lớp 15."
}
```

**E03**: Missing grade
```json
{
  "error_code": "E03",
  "error_messages": "Vui lòng cho biết lớp học."
}
```

**E04**: Missing both grade and subject
```json
{
  "error_code": "E04",
  "error_messages": "Vui lòng cho biết lớp học và môn học."
}
```

### Subgraph Errors

Nếu có lỗi trong subgraph execution:
```python
return {
    "node_responses": [AIMessage(
        content="Xin lỗi, tôi gặp khó khăn trong việc tạo bài tập."
    )],
    "data_artifacts": {
        "error": str(e),
        "error_type": type(e).__name__
    }
}
```

## Tối ưu hóa

### 1. State Caching
- Graph cha cache compiled graph với `@lru_cache`
- Subgraph được tạo mỗi khi invoke (lightweight)

### 2. Parallel Execution
- ValidationNode và ScopeClassifierNode chạy nhanh (sync)
- RuleBasedNode không cần LLM (< 1s)
- LLMFallbackNode chạy async với LLM

### 3. Memory Management
- CreateExerciseState chỉ tồn tại trong scope của subgraph
- Chỉ return cần thiết về GraphState (node_responses + data_artifacts)

## Testing

### Unit Tests
```python
# Test ValidationNode
test_validation_node_valid_input()
test_validation_node_missing_grade()
test_validation_node_invalid_combination()

# Test ScopeClassifierNode
test_classifier_tier1_simple()
test_classifier_tier3_complex()

# Test RuleBasedNode
test_rule_based_generation()

# Test LLMFallbackNode
test_llm_fallback_generation()

# Test ResponseBuilderNode
test_response_builder_success()
test_response_builder_error()
```

### Integration Tests
```python
# Test full subgraph flow
test_subgraph_tier1_flow()
test_subgraph_tier3_flow()
test_subgraph_validation_error()

# Test parent-subgraph integration
test_create_exercise_node_calls_subgraph()
test_state_mapping_input()
test_state_mapping_output()
```

### E2E Tests
```python
# Test full agent flow
test_create_exercise_e2e_tier1()
test_create_exercise_e2e_tier3()
test_create_exercise_e2e_validation_error()
```

## Debugging

### Enable Debug Logging
```python
import logging
logging.getLogger("agent.graph.node_services.create_exercise").setLevel(logging.DEBUG)
```

### Debug State at Each Node
```python
# In each node's run() method
logger.debug(f"Node input state: {state}")
logger.debug(f"Node output: {output}")
```

### Trace Subgraph Execution
```python
# In CreateExerciseNode.run()
logger.info(f"Subgraph input: {subgraph_input}")
logger.info(f"Subgraph result: {result}")
```

## Tài liệu tham khảo

- `agent/graph/graph_builder.py` - Main graph construction
- `agent/graph/graph_state.py` - GraphState definition
- `agent/graph/node_services/create_exercise/create_exercise.py` - CreateExerciseNode
- `agent/graph/node_services/create_exercise/subgraph/builder.py` - Subgraph builder
- `agent/graph/node_services/create_exercise/subgraph/state.py` - CreateExerciseState
- `docs/CREATE_EXERCISE_PIPELINE_ARCHITECTURE.md` - Detailed subgraph architecture
