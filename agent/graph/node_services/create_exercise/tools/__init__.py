"""
Exercise Creation Tools Module

Công cụ LangChain cho việc tạo bài tập:

1. context_collector_tool
   - Thu thập context từ Neo4j Graph
   - Lấy chapter, topic, concepts, keywords
   - Tìm kiếm bài tập mẫu liên quan

2. exercise_generator_tool
   - Tạo bài tập dựa trên context
   - Hỗ trợ nhiều loại bài tập
   - Sử dụng LLM để sinh bài chất lượng

3. exercise_analyzer_tool
   - Phân tích chất lượng bài tập
   - Kiểm tra các tiêu chí (clarity, relevance, difficulty, etc.)
   - Cung cấp gợi ý cải thiện

Ví dụ sử dụng:
    from agent.graph.node_services.create_exercise.tools import (
        context_collector_tool,
        exercise_generator_tool,
        exercise_analyzer_tool
    )

    # Thu thập context
    context = await context_collector_tool(
        state=state,
        query="Câu hỏi về ...",
        subject="math",
        grade="10"
    )

    # Tạo bài tập
    exercises = await exercise_generator_tool(
        state=state,
        context=context,
        exercise_type="multiple_choice",
        num_exercises=3
    )

    # Phân tích chất lượng
    analysis = await exercise_analyzer_tool(
        state=state,
        exercises=exercises['exercises'],
        context=context
    )
"""

from agent.graph.node_services.create_exercise.tools.context_collector_tool import (
    context_collector_tool,
    ContextCollectorToolInput
)
from agent.graph.node_services.create_exercise.tools.exercise_generator_tool import (
    exercise_generator_tool,
    ExerciseGeneratorToolInput
)
from agent.graph.node_services.create_exercise.tools.exercise_analyzer_tool import (
    exercise_analyzer_tool,
    ExerciseAnalyzerToolInput
)

__all__ = [
    # Tools
    "context_collector_tool",
    "exercise_generator_tool",
    "exercise_analyzer_tool",
    # Input Schemas
    "ContextCollectorToolInput",
    "ExerciseGeneratorToolInput",
    "ExerciseAnalyzerToolInput",
]

__version__ = "1.0.0"
__description__ = "LangChain tools for exercise creation with Neo4j integration"
