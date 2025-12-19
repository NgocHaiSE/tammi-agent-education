from typing import Dict, Any
from agent.graph.node_base import NodeBase
from agent.graph.node_services.create_exercise.subgraph.state import CreateExerciseState
from agent.graph.node_services.create_exercise.subgraph.generators.rule_generator import RuleBasedExerciseGenerator


class RuleBasedNode(NodeBase):
    def __init__(self, llm=None, **kwargs):
        super().__init__(name="rule_based_node", llm=llm, **kwargs)
        self.generator = RuleBasedExerciseGenerator()

    async def run(self, state: CreateExerciseState) -> Dict[str, Any]:
        grade = state.get("grade")
        subject = state.get("subject")
        topic = state.get("topic")
        exercise_type = state.get("exercise_type", "mixed")
        num_exercises = state.get("num_exercises", 5)

        # Map topic/type to generator's exercise_type
        generator_type = self._map_to_generator_type(topic, exercise_type)
        
        # Generate exercises using rule-based generator
        exercises = self.generator.generate(
            grade=grade,
            exercise_type=generator_type,
            count=num_exercises
        )

        return {
            "exercises": exercises,
            "generation_metadata": {
                "tier": 1,
                "method": "rule_based",
                "subject": subject,
                "generated_count": len(exercises),
                "generation_time": "<1s"
            },
            "next_node": "quality_check"
        }
    
    def _map_to_generator_type(self, topic: str, exercise_type: str) -> str:
        """Map topic/exercise_type to generator's internal types."""
        topic_lower = topic.lower() if topic else ""
        
        # Map based on topic
        if "cộng" in topic_lower or "addition" in topic_lower:
            return "Phép cộng"
        elif "trừ" in topic_lower or "subtraction" in topic_lower:
            return "Phép trừ"
        elif "nhân" in topic_lower or "multiplication" in topic_lower:
            return "Phép nhân"
        elif "chia" in topic_lower or "division" in topic_lower:
            return "Phép chia"
        else:
            # Default to mixed
            return "mixed"