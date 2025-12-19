"""
ExerciseMemory - Session-aware memory for exercise generation.

Provides persistent storage for:
- Exercise generation history per session
- User preferences (subject, grade, difficulty)
- Last context for contextual follow-up requests
- Duplicate avoidance

Similar to SymptomMemory but optimized for exercise generation.
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from agent.utils.logging import get_logger

logger = get_logger(__name__)


class ExerciseMemory:
    """Singleton class for managing exercise generation history per session.
    
    Features:
    - Session-aware storage (auto-reset on session change)
    - Exercise history tracking with timestamps
    - User preference learning from patterns
    - Context extraction for follow-up requests
    - JSON file persistence
    
    Example:
        >>> memory = ExerciseMemory(session_id="sess_123")
        >>> memory.add_exercise_record(
        ...     request_params={"grade": 6, "subject": "toán", "topic": "phân số"},
        ...     exercises=[{"question": "...", "answer": "..."}],
        ...     generation_metadata={"tier": 2, "method": "rag"}
        ... )
        >>> last_context = memory.get_last_context()
        >>> print(last_context)  # {"grade": 6, "subject": "toán", "topic": "phân số"}
    """
    
    _instance = None  # Singleton instance
    
    # Cache file path (same directory as this file)
    CACHE_FILE = os.path.join(
        os.path.dirname(__file__), "exercise_memory_cache.json"
    )
    
    def __new__(cls, *args, **kwargs):
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(ExerciseMemory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, session_id: str = None):
        """Initialize ExerciseMemory with session tracking.
        
        Args:
            session_id: Current session ID. If different from stored session,
                       cache will be reset.
        """
        if self._initialized:
            # Already initialized, check if session changed
            if session_id and session_id != self.session_id:
                logger.info(f"Session changed from {self.session_id} to {session_id}, resetting cache")
                self._reset_for_new_session(session_id)
            return
        
        # First time initialization
        self.session_id: str = session_id or "default"
        self.exercise_history: List[Dict[str, Any]] = []
        self.conversation_history: List[Dict[str, Any]] = []  # NEW: Track conversation
        self.user_preferences: Dict[str, Any] = {
            "preferred_subjects": [],
            "preferred_grades": [],
            "preferred_difficulty": None,
            "preferred_exercise_type": None
        }
        self.last_context: Dict[str, Any] = {}
        
        # Load from file if exists
        self.load_from_file()
        self._initialized = True
        
        logger.debug(f"ExerciseMemory initialized for session {self.session_id}")
    
    def _reset_for_new_session(self, new_session_id: str):
        """Reset cache when switching to a new session.
        
        Args:
            new_session_id: The new session ID.
        """
        self.session_id = new_session_id
        self.exercise_history = []
        self.conversation_history = []  # Reset conversation
        self.user_preferences = {
            "preferred_subjects": [],
            "preferred_grades": [],
            "preferred_difficulty": None,
            "preferred_exercise_type": None
        }
        self.last_context = {}
        self.save_to_file()
        logger.info(f"Cache reset for new session: {new_session_id}")
    
    def add_exercise_record(
        self,
        request_params: Dict[str, Any],
        exercises: List[Dict[str, Any]],
        generation_metadata: Dict[str, Any]
    ):
        """Add a new exercise generation record to history.
        
        Args:
            request_params: Request parameters (grade, subject, topic, etc.)
            exercises: List of generated exercises
            generation_metadata: Metadata about generation (tier, method, model)
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "request": request_params,
            "generated_exercises": exercises,
            "metadata": generation_metadata
        }
        
        self.exercise_history.append(record)
        
        # Update last context
        self.last_context = {
            "grade": request_params.get("grade"),
            "subject": request_params.get("subject"),
            "topic": request_params.get("topic"),
            "exercise_type": request_params.get("exercise_type"),
            "difficulty": request_params.get("difficulty")
        }
        
        # Update preferences
        self.update_preferences(request_params)
        
        logger.debug(
            f"Added exercise record: {request_params.get('subject')} "
            f"lớp {request_params.get('grade')}, {len(exercises)} exercises"
        )
    
    def get_exercise_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent exercise generation history.
        
        Args:
            limit: Maximum number of records to return (most recent first)
            
        Returns:
            List of exercise records, sorted by timestamp (newest first)
        """
        # Return most recent records
        return self.exercise_history[-limit:] if self.exercise_history else []
    
    def get_last_context(self) -> Dict[str, Any]:
        """Get context from the last exercise generation request.
        
        Useful for filling missing parameters in follow-up requests.
        
        Returns:
            Dict with grade, subject, topic, exercise_type, difficulty
        """
        return self.last_context.copy()
    
    def update_partial_context(self, **kwargs):
        """Update partial context with extracted values.
        
        Only updates fields that have non-empty values.
        Useful when validation fails but some info was extracted.
        
        Args:
            **kwargs: Fields to update (grade, subject, topic, difficulty, exercise_type)
        """
        for key, value in kwargs.items():
            if value:  # Only update if value is not empty/None
                self.last_context[key] = value
                logger.debug(f"Updated partial context: {key}={value}")
        
        # Auto-save after update
        self.save_to_file()
    
    def update_preferences(self, request_params: Dict[str, Any]):
        """Learn user preferences from request patterns.
        
        Tracks frequently used subjects, grades, difficulty levels, etc.
        
        Args:
            request_params: Request parameters to learn from
        """
        # Track subject preferences
        subject = request_params.get("subject")
        if subject and subject not in self.user_preferences["preferred_subjects"]:
            self.user_preferences["preferred_subjects"].append(subject)
        
        # Track grade preferences
        grade = request_params.get("grade")
        if grade and grade not in self.user_preferences["preferred_grades"]:
            self.user_preferences["preferred_grades"].append(grade)
        
        # Track difficulty (use most recent)
        difficulty = request_params.get("difficulty")
        if difficulty:
            self.user_preferences["preferred_difficulty"] = difficulty
        
        # Track exercise type (use most recent)
        exercise_type = request_params.get("exercise_type")
        if exercise_type:
            self.user_preferences["preferred_exercise_type"] = exercise_type
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get learned user preferences.
        
        Returns:
            Dict with preferred_subjects, preferred_grades, preferred_difficulty, etc.
        """
        return self.user_preferences.copy()
    
    def add_conversation_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a conversation message to history.
        
        Args:
            role: 'human' or 'ai'
            content: Message content
            metadata: Optional metadata (extracted params, generation info, etc.)
        """
        if role not in ["human", "ai"]:
            logger.warning(f"Invalid role '{role}', should be 'human' or 'ai'")
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            message["metadata"] = metadata
        
        self.conversation_history.append(message)
        logger.debug(f"Added {role} message to conversation history")
    
    def get_conversation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent conversation history.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of conversation messages, oldest first
        """
        return self.conversation_history[-limit:] if self.conversation_history else []
    
    def get_previous_questions(self, limit: int = 20) -> List[str]:
        """Get list of previously generated questions to avoid duplicates.
        
        Args:
            limit: Maximum number of questions to return
            
        Returns:
            List of question strings
        """
        questions = []
        for record in reversed(self.exercise_history):
            for exercise in record.get("generated_exercises", []):
                question = exercise.get("question", "")
                if question:
                    questions.append(question)
                    if len(questions) >= limit:
                        return questions
        return questions
    
    def save_to_file(self):
        """Save current state to JSON file."""
        data = {
            "session_id": self.session_id,
            "exercise_history": self.exercise_history,
            "conversation_history": self.conversation_history,
            "user_preferences": self.user_preferences,
            "last_context": self.last_context
        }
        
        try:
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved exercise memory to {self.CACHE_FILE}")
        except Exception as e:
            logger.error(f"Failed to save exercise memory: {e}")
    
    def load_from_file(self) -> bool:
        """Load state from JSON file if it exists.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.CACHE_FILE):
                logger.debug("No cache file found, starting fresh")
                return False
            
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    logger.debug("Cache file is empty")
                    return False
                
                data = json.loads(content)
                
                # Check if session matches
                saved_session_id = data.get("session_id")
                if saved_session_id != self.session_id:
                    logger.info(
                        f"Session mismatch: saved={saved_session_id}, "
                        f"current={self.session_id}, starting fresh"
                    )
                    return False
                
                # Load data
                self.exercise_history = data.get("exercise_history", [])
                self.conversation_history = data.get("conversation_history", [])
                self.user_preferences = data.get("user_preferences", {
                    "preferred_subjects": [],
                    "preferred_grades": [],
                    "preferred_difficulty": None,
                    "preferred_exercise_type": None
                })
                self.last_context = data.get("last_context", {})
                
                logger.info(
                    f"Loaded exercise memory: {len(self.exercise_history)} records"
                )
                return True
                
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load exercise memory: {e}")
            return False
    
    def clear_history(self):
        """Clear all exercise history and preferences."""
        self.exercise_history = []
        self.conversation_history = []
        self.user_preferences = {
            "preferred_subjects": [],
            "preferred_grades": [],
            "preferred_difficulty": None,
            "preferred_exercise_type": None
        }
        self.last_context = {}
        
        # Delete cache file
        if os.path.exists(self.CACHE_FILE):
            try:
                os.remove(self.CACHE_FILE)
                logger.info("Cleared exercise memory and deleted cache file")
            except Exception as e:
                logger.error(f"Failed to delete cache file: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about exercise generation history.
        
        Returns:
            Dict with total_exercises, total_requests, subjects_used, etc.
        """
        total_exercises = sum(
            len(record.get("generated_exercises", []))
            for record in self.exercise_history
        )
        
        subjects_used = set()
        grades_used = set()
        for record in self.exercise_history:
            req = record.get("request", {})
            if req.get("subject"):
                subjects_used.add(req["subject"])
            if req.get("grade"):
                grades_used.add(req["grade"])
        
        return {
            "total_requests": len(self.exercise_history),
            "total_exercises": total_exercises,
            "subjects_used": list(subjects_used),
            "grades_used": sorted(list(grades_used)),
            "session_id": self.session_id
        }
