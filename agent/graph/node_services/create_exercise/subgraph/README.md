# Create Exercise Subgraph

Subgraph xử lý logic tạo bài tập với dynamic routing dựa trên độ phức tạp.

## Kiến trúc

```
Main Graph (GraphState)
    ↓
CreateExerciseNode
    ↓
Create Exercise Subgraph (CreateExerciseState)
    ├─ ValidationNode → Validate input
    ├─ ScopeClassifierNode → Route (Tier 1 vs Tier 3)
    ├─ RuleBasedNode (Tier 1) → Template generation
    ├─ LLMFallbackNode (Tier 3) → LLM generation
    ├─ QualityCheckNode → Validate exercises
    └─ ResponseBuilderNode → Format output
    ↓
Return to CreateExerciseNode
    ↓
Return to Main Graph → END
```

## Files

### Core Files
- **`builder.py`** - Subgraph builder với state transformation
- **`state.py`** - CreateExerciseState schema
- **`__init__.py`** - Exports

### Nodes
- **`validation_node.py`** - Validate input (grade, subject, topic)
- **`scope_classifier_node.py`** - Route to Tier 1 or Tier 3
- **`rule_based_node.py`** - Template-based generation (Tier 1)
- **`llm_fallback_node.py`** - LLM-based generation (Tier 3)
- **`quality_check_node.py`** - Validate generated exercises
- **`response_builder_node.py`** - Format final response

## Usage

### 1. Subgraph được gọi tự động từ CreateExerciseNode

```python
# agent/graph/node_services/create_exercise/create_exercise.py

@node_register(name="create_exercise")
class CreateExerciseNode(NodeBase):
    def __init__(self, llm, **kwargs):
        super().__init__(name="create_exercise", llm=llm, **kwargs)
        self.subgraph = create_create_exercise_graph(self.llm, self)
    
    async def run(self, state: GraphState) -> Dict[str, Any]:
        # Prepare input
        subgraph_input = {...}
        
        # Invoke subgraph
        result = await self.subgraph.ainvoke(subgraph_input)
        
        # Return to parent
        return {
            "node_responses": result.get("node_responses", []),
            "data_artifacts": {...}
        }
```

### 2. Input từ User Request

```json
{
  "payload": {
    "content": "Tạo bài tập toán lớp 6 về phân số",
    "metadata": {
      "grade": "6",
      "subject": "Toán",
      "topic": "Phân số",
      "num_exercises": 5
    }
  }
}
```

### 3. Output về Main Graph

```python
{
    "node_responses": [
        AIMessage(content="Đây là 5 bài tập Toán lớp 6...", ...)
    ],
    "data_artifacts": {
        "exercises": [...],
        "generation_metadata": {
            "tier": 1,
            "method": "rule_based"
        },
        "quality_passed": True
    }
}
```

## Flow Execution

### Tier 1 (Rule-based) - Simple cases
```
ValidationNode 
  → grade=6, subject="Toán", topic="Phân số"
ScopeClassifierNode 
  → tier=1 (simple, trong phạm vi)
RuleBasedNode 
  → Generate từ template
QualityCheckNode 
  → Validate exercises
ResponseBuilderNode 
  → Format AIMessage
```

### Tier 3 (LLM Fallback) - Complex cases
```
ValidationNode 
  → grade=12, subject="Vật lý", topic="Cơ học lượng tử"
ScopeClassifierNode 
  → tier=3 (phức tạp, cần LLM)
LLMFallbackNode 
  → Generate bằng LLM
QualityCheckNode 
  → Validate exercises
ResponseBuilderNode 
  → Format AIMessage
```

### Error Path - Validation failed
```
ValidationNode 
  → Error: Missing grade (E03)
ResponseBuilderNode (direct)
  → Format error message
```

## State Schema

### CreateExerciseState

```python
class CreateExerciseState(TypedDict):
    # Input từ parent
    request: Dict[str, Any]
    history_chat: List[BaseMessage]
    
    # Validation
    validated: bool
    validation_errors: Optional[str]
    grade: Optional[str]
    subject: Optional[str]
    topic: Optional[str]
    exercise_type: Optional[str]
    num_exercises: int
    
    # Routing
    tier: int  # 1=RuleBased, 3=LLM
    processing_method: str
    
    # Generation
    exercises: List[Dict[str, Any]]
    generation_metadata: Dict[str, Any]
    
    # Quality
    quality_passed: bool
    quality_issues: List[str]
    
    # Output
    node_responses: List[BaseMessage]
    suggestions: List[str]
```

## Error Codes

- **E01**: Missing subject
- **E02**: Invalid grade-subject combination
- **E03**: Missing grade
- **E04**: Missing both grade and subject

## Documentation

Xem chi tiết:
- **`docs/PARENT_SUBGRAPH_INTEGRATION.md`** - Parent-Subgraph integration
- **`docs/CREATE_EXERCISE_PIPELINE_ARCHITECTURE.md`** - Detailed subgraph architecture

## Testing

```bash
# Unit tests
pytest tests/unit/graph/node_services/create_exercise/subgraph/

# Integration tests
pytest tests/integration/create_exercise/

# E2E tests
pytest tests/e2e/test_create_exercise.py
```

## Development

### Adding a new node

1. Create node file in `nodes/`
2. Implement `NodeBase.run(state: CreateExerciseState)`
3. Add to `builder.py`:
   ```python
   workflow.add_node("my_node", my_node.run)
   workflow.add_edge("prev_node", "my_node")
   ```

### Modifying routing logic

Edit routing functions in `builder.py`:
```python
def route_after_classifier(state: CreateExerciseState) -> str:
    tier = state.get("tier", 3)
    
    if tier == 1:
        return "rule_based"
    elif tier == 2:
        return "hybrid"  # New path
    else:
        return "llm_fallback"
```

## Performance

- **Tier 1 (Rule-based)**: < 1s (no LLM call)
- **Tier 3 (LLM Fallback)**: 3-8s (1 LLM call)
- **Validation**: < 100ms
- **Quality Check**: < 200ms
