from typing import Dict, Any
from agent.graph.node_base import NodeBase
from agent.graph.node_services.create_exercise.subgraph.state import CreateExerciseState


class ScopeClassifierNode(NodeBase):
    def __init__(self, llm=None, **kwargs):
        super().__init__(name="scope_classifier_node", llm=llm, **kwargs)
        
        # Tier 1 eligible subjects and grades (simple cases)
        self.tier1_subjects = ["", ""]
        self.tier1_grades = list(range(1, 5))  # Grade 1-8
    
    async def run(self, state: CreateExerciseState) -> Dict[str, Any]:

        grade = state.get("grade")
        subject = state.get("subject")
        topic = state.get("topic")
        exercise_type = state.get("exercise_type")

        # Check Tier 1
        if self._is_tier1_eligible(grade, subject, exercise_type):
            return {
                "tier": 1,
                "processing_method": "template_based",
                "next_node": "rule_based"
            }
        elif self._is_tier2_eligible(grade, subject, topic):
            return {
                "tier": 2,
                "processing_method": "rag",
                "next_node": "rag"
            }
        else:
            return {
                "tier": 3,
                "processing_method": "llm_fallback",
                "next_node": "llm_fallback"
            }
    
    def _is_tier1_eligible(self, grade: int, subject: str, exercise_type: str) -> bool:
        # Check subject
        if subject not in self.tier1_subjects:
            return False
        
        # Check grade
        if grade not in self.tier1_grades:
            return False
        
        # Check exercise type (no essay for tier 1)
        if exercise_type == "Tự luận":
            return False
        
        return True
    
    def _is_tier2_eligible(self, grade: int, subject: str, topic: str) -> bool:
        
        tier2_subjects = ["toán", "vật lý", "hóa học", "sinh học", "lịch sử", "địa lý", "tiếng anh"]
        tier2_grades = list(range(1, 5))  
        
        return subject in tier2_subjects and grade in tier2_grades
    
