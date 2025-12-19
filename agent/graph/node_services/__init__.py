"""
Node services for graph nodes.

Automatically imports all node classes to trigger @node_register decorators.
"""

# Import all node classes to register them in the global registry
from .sub_intent_classification.sub_intent_classification import SubIntentClassificationNode
from .search_material.search_material import SearchMaterialNode
from .create_exercise.create_exercise import CreateExerciseNode
from .correct_exercise.correct_exercise import CorrectExerciseNode
from .tutor_subject.tutor_subject import TutorSubjectNode

__all__ = [
    "SubIntentClassificationNode",
    "SearchMaterialNode",
    "CreateExerciseNode",
    "CorrectExerciseNode",
    "TutorSubjectNode",
]
