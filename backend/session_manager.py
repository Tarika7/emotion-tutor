import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List
import json

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SessionConfig:
    """Session configuration"""
    session_id: str
    topic_data: dict
    questions: dict
    subject: str
    total_time_minutes: int
    created_at: float
    full_text: str = "" # PERSISTED PDF CONTEXT

    def to_dict(self):
        return {
            'session_id': self.session_id,
            'subject': self.subject,
            'total_time_minutes': self.total_time_minutes,
            'created_at': self.created_at,
            'topic_count': len(self.topic_data.get('topics', []))
        }

@dataclass
class SessionMetrics:
    """Session performance metrics"""
    total_interactions: int = 0
    correct_answers: int = 0
    total_time_spent: float = 0.0
    emotion_history: List[dict] = field(default_factory=list)
    distraction_events: List[dict] = field(default_factory=list)
    topic_mastery: dict = field(default_factory=dict)
    consecutive_incorrect: int = 0  # streak of wrong answers in a row


# ============================================================================
# CORE SESSION STATE  (THE KEY FIX — all sequential state lives here)
# ============================================================================

class AdaptiveSessionState:
    """
    Tracks WHERE we are in the curriculum and WHAT has been asked.
    This is the single source of truth for question progression.
    
    3-Level Hierarchy: Topic → Lesson → Question
    """
    def __init__(self, topics: list):
        self.topics = topics
        self.current_topic_index = 0
        self.current_lesson_index = 0    # NEW: Lesson level
        self.current_question_index = 0
        self.question_history = []      # list of {topic_id, lesson_id, question, answer, is_correct, emotion}
        self.correctness_log = []       # bool per answer
        self.last_question_text = None  # track last question to prevent repeats
        self.last_emotion = "Engaged"
        self.pending_question_id = None # ID of currently pending (unanswered) question
        self.pending_question_data = {} # Cache of the last returned question for consistency

    @property
    def current_topic(self):
        if self.current_topic_index < len(self.topics):
            topic = self.topics[self.current_topic_index]
            # Ensure name/title consistency
            if 'name' not in topic and 'title' in topic:
                topic['name'] = topic['title']
            elif 'title' not in topic and 'name' in topic:
                topic['title'] = topic['name']
            return topic
        return None

    @property
    def current_lesson(self):
        """Get current lesson from current topic. Falls back to a virtual lesson if none exist."""
        topic = self.current_topic
        if topic:
            lessons = topic.get('lessons', [])
            if lessons and self.current_lesson_index < len(lessons):
                return lessons[self.current_lesson_index]
            # Fallback for topics without explicit lessons
            return {
                "id": f"{topic.get('id', 't')}_l1",
                "name": f"Understanding {topic.get('name', 'Content')}",
                "title": f"Understanding {topic.get('name', 'Content')}", # Compatibility
                "topic_id": topic.get('id')
            }
        return None

    def get_topic_by_id(self, topic_id):
        return next((t for t in self.topics if t.get('id') == topic_id), None)

    def get_topic_index_by_id(self, topic_id):
        for i, t in enumerate(self.topics):
            if t.get('id') == topic_id:
                return i
        return 0

    def advance_question(self, topic_id: str, is_correct: bool, emotion: str):
        """
        Advance state after an answer.
        3-Level Progression: Topic → Lesson → Question
        
        Progression logic:
          - If correct (or bored): move to next question
          - If incorrect + frustrated: stay on same question for re-teaching
          - When questions exhausted in lesson: move to next lesson
          - When lessons exhausted in topic: move to next topic
        """
        print(f"\n[ADVANCE] BEFORE: topic_idx={self.current_topic_index}, lesson_idx={self.current_lesson_index}, q_idx={self.current_question_index}")
        
        self.last_emotion = emotion
        topic_idx = self.get_topic_index_by_id(topic_id)
        
        # Safety check: ensure we don't go out of bounds
        if topic_idx is not None:
            self.current_topic_index = topic_idx
        
        topic = self.get_topic_by_id(topic_id)
        lessons = topic.get('lessons', []) if topic else []
        
        if self.current_lesson_index < len(lessons):
            lesson = lessons[self.current_lesson_index]
            lesson_qs = lesson.get('questions', []) if lesson else []
            questions_in_lesson = len(lesson_qs)
        else:
            lesson_qs = []
            questions_in_lesson = 0

        # Advancement decision
        should_advance = is_correct or emotion == 'Bored' or emotion == 'Engaged'
        
        if should_advance:
            # Move to next question in this lesson
            self.current_question_index += 1
            print(f"[ADVANCE] Advanced to q_index={self.current_question_index} (correct={is_correct}, emotion={emotion})")
            
            # DETERMINISTIC ADVANCEMENT FOR TOPICS (if no explicit lessons)
            # We want at least 3 questions per topic if it has multiple concepts
            target_questions = max(3, len(topic.get('key_concepts', []))) if topic else 3
            
            # Check if exhausted questions in current lesson/topic
            if (questions_in_lesson > 0 and self.current_question_index >= questions_in_lesson) or \
               (questions_in_lesson == 0 and self.current_question_index >= target_questions):
                
                print(f"[ADVANCE] Content exhausted ({max(questions_in_lesson, target_questions)} questions).")
                
                if lessons and self.current_lesson_index < len(lessons) - 1:
                    print(f"[ADVANCE] Moving to next lesson in topic.")
                    self.current_lesson_index += 1
                    self.current_question_index = 0
                else:
                    print(f"[ADVANCE] Topic fully completed. Moving to next topic.")
                    self.current_topic_index += 1
                    self.current_lesson_index = 0
                    self.current_question_index = 0
                    
                    if self.current_topic_index >= len(self.topics):
                        print(f"[ADVANCE] All topics completed! Looping back to start.")
                        self.current_topic_index = 0
        else:
            # Stay on same question for re-teaching (Frustrated + incorrect)
            print(f"[ADVANCE] Staying on q_index={self.current_question_index} (frustrated & incorrect)")

        print(f"[ADVANCE] AFTER: topic_idx={self.current_topic_index}, lesson_idx={self.current_lesson_index}, q_idx={self.current_question_index}\n")

    def mark_question(self, topic_id, lesson_id, question_text, answer_text, is_correct, emotion):
        """Log this question attempt with 3-level hierarchy."""
        self.question_history.append({
            'topic_id': topic_id,
            'lesson_id': lesson_id,
            'question': question_text,
            'answer': answer_text,
            'is_correct': is_correct,
            'emotion': emotion,
            'timestamp': time.time()
        })
        self.correctness_log.append(is_correct)

    def set_pending_question(self, question_id: str, question_data: dict):
        """Mark a question as pending (returned but not yet answered)."""
        self.pending_question_id = question_id
        self.pending_question_data = question_data.copy()
        print(f"[STATE] Pending question set: {question_id} for topic {question_data.get('topic_id', '?')}")

    def clear_pending_question(self):
        """Clear the pending question after successful answer."""
        self.pending_question_id = None
        self.pending_question_data = {}
        print(f"[STATE] Pending question cleared")

    def get_pending_question(self):
        """Return the pending question if one exists, else None."""
        return self.pending_question_data if self.pending_question_id else None

    def debug_state(self):
        topic = self.current_topic
        lesson = self.current_lesson
        t_id = topic.get('id', '?') if topic else 'None'
        t_title = topic.get('title', '?') if topic else 'None'
        l_id = lesson.get('id', '?') if lesson else 'None'
        l_title = lesson.get('title', '?') if lesson else 'None'
        pending_info = f" | pending={self.pending_question_id}" if self.pending_question_id else ""
        print(f"[DEBUG] topic_idx={self.current_topic_index} ({t_id}: {t_title}) | "
              f"lesson_idx={self.current_lesson_index} ({l_id}: {l_title}) | "
              f"q_idx={self.current_question_index} | "
              f"history_len={len(self.question_history)} | "
              f"emotion={self.last_emotion}{pending_info}")


# ============================================================================
# SESSION MANAGER
# ============================================================================

class SessionManager:
    """Manages learning sessions"""

    def __init__(self):
        self.current_session: Optional[SessionConfig] = None
        self.session_start_time = None
        self.metrics = SessionMetrics()
        self.adaptive_state: Optional[AdaptiveSessionState] = None
        self.distraction_blocked_until = None
        self.distraction_block_active = False
        # AI Enhancement Layer (one instance per session)
        self.emotion_engine      = None
        self.learning_classifier = None
        self.adaptation_engine   = None
        self.engagement_tracker  = None

    def create_session(self, session_id: str, topic_data: dict, questions: dict,
                       subject: str, time_minutes: int) -> dict:
        """Create a new learning session and initialise all state."""

        self.current_session = SessionConfig(
            session_id=session_id,
            topic_data=topic_data,
            questions=questions,
            subject=subject,
            total_time_minutes=time_minutes,
            created_at=time.time(),
            full_text=topic_data.get('full_text', '') # Save context
        )
        self.session_start_time = time.time()
        self.metrics = SessionMetrics()

        topics = topic_data.get('topics', [])

        # Init adaptive state
        self.adaptive_state = AdaptiveSessionState(topics)

        # Init AI Enhancement Layer
        from emotion_engine import EmotionFusionEngine
        from learning_state import LearningStateClassifier
        from adaptation_engine import AdaptationEngine
        from engagement_tracker import EngagementTracker
        self.emotion_engine      = EmotionFusionEngine()
        self.learning_classifier = LearningStateClassifier()
        self.adaptation_engine   = AdaptationEngine()
        self.engagement_tracker  = EngagementTracker()
        self.metrics.consecutive_incorrect = 0
        print("[SESSION] AI Enhancement Layer initialised")

        # Init topic mastery
        for topic in topics:
            topic_id = topic.get('id', 'unknown')
            self.metrics.topic_mastery[topic_id] = {
                'questions_asked': 0,
                'correct_answers': 0,
                'mastery_score': 0.0,
                'difficulty_level': topic.get('difficulty', 1),
                'expected_answer': '',
                'current_question_text': ''
            }

        print(f"[SESSION] Created session {session_id} with {len(topics)} topics")

        return {
            'status': 'success',
            'session_id': session_id,
            'total_time': time_minutes,
            'topics': len(topics),
            'start_time': datetime.fromtimestamp(self.session_start_time).isoformat()
        }

    def get_session_info(self) -> dict:
        """Get current session info"""
        if not self.current_session or not self.session_start_time:
            return {'status': 'no_session'}

        elapsed = time.time() - self.session_start_time
        remaining = (self.current_session.total_time_minutes * 60) - elapsed

        return {
            'session_id': self.current_session.session_id,
            'subject': self.current_session.subject,
            'elapsed_seconds': round(elapsed, 1),
            'remaining_seconds': round(max(0, remaining), 1),
            'total_seconds': self.current_session.total_time_minutes * 60,
            'progress_percent': min(100, (elapsed / (self.current_session.total_time_minutes * 60)) * 100),
            'is_time_critical': remaining < 300,
            'is_time_up': remaining <= 0,
            'topic_data': self.current_session.topic_data   # CRITICAL: for /get_next_lesson
        }

    def get_next_question_context(self, topic_id: str, emotion: str) -> dict:
        """
        Return the context needed to generate (or retrieve) the next question.
        Also returns the sequential state for debug logging.
        """
        if not self.adaptive_state or not self.current_session:
            return {}

        state = self.adaptive_state
        state.last_emotion = emotion

        topics = self.current_session.topic_data.get('topics', [])

        # Navigate to the requested topic (may differ from auto-advancing index)
        topic_idx = state.get_topic_index_by_id(topic_id)
        if topic_idx is None:
            topic_idx = state.current_topic_index

        topic = topics[topic_idx] if topic_idx < len(topics) else (topics[-1] if topics else {})

        # Adjust difficulty based on emotion
        base_difficulty = topic.get('difficulty', 1)
        if emotion == 'Frustrated':
            difficulty = max(1, base_difficulty - 1)
            style_hint = 'simplified, heavily encouraging'
        elif emotion == 'Confused':
            difficulty = max(1, base_difficulty - 1)
            style_hint = 'structured, concrete analogies'
        elif emotion == 'Bored':
            difficulty = min(5, base_difficulty + 1)
            style_hint = 'challenging, puzzle-like'
        else:  # Engaged
            difficulty = base_difficulty
            style_hint = 'enthusiastic, progressive'

        q_index = state.current_question_index
        lesson = state.current_lesson
        pregenerated_questions = lesson.get('questions', []) if lesson else []
        
        current_question = {}
        if q_index < len(pregenerated_questions):
            current_question = pregenerated_questions[q_index]

        topic_q_history = [
            h['question'] for h in state.question_history
            if h['topic_id'] == topic_id
        ]

        print(f"[CONTEXT] topic={topic.get('id')}, lesson={state.current_lesson_index}, q_idx={q_index}, emotion={emotion}, "
              f"difficulty={difficulty}, questions_asked_on_topic={len(topic_q_history)}")

        return {
            'topic': topic,
            'lesson': lesson,
            'topic_index': topic_idx,
            'lesson_index': state.current_lesson_index,
            'question_index': q_index,
            'pregenerated_question': current_question,
            'difficulty': difficulty,
            'style_hint': style_hint,
            'emotion': emotion,
            'previously_asked': topic_q_history,
            'total_topics': len(topics),
            'is_last_topic': topic_idx >= len(topics) - 1
        }

    def store_expected_answer(self, topic_id: str, question_text: str, answer_text: str, hint: str = ""):
        """Store the expected answer for grading the next submission."""
        # Auto-create mastery entry if topic_id is not pre-seeded (e.g. after name->id resolution)
        if topic_id not in self.metrics.topic_mastery:
            self.metrics.topic_mastery[topic_id] = {
                'questions_asked': 0,
                'correct_answers': 0,
                'mastery_score': 0.0,
                'difficulty_level': 1,
                'expected_answer': '',
                'current_question_text': ''
            }
        self.metrics.topic_mastery[topic_id]['expected_answer'] = answer_text
        self.metrics.topic_mastery[topic_id]['current_question_text'] = question_text
        self.metrics.topic_mastery[topic_id]['hint'] = hint
        self.adaptive_state.last_question_text = question_text

    def record_answer(self, topic_id: str, user_answer: str, is_correct: bool,
                      emotion: str, time_taken: float, distraction_detected: bool):
        """Record answer, update mastery, advance state, clear pending question."""
        print(f"\n[RECORD_ANSWER] Processing answer for topic={topic_id}, is_correct={is_correct}")
        
        self.record_interaction(topic_id, is_correct, emotion, time_taken, distraction_detected)

        q_text = self.metrics.topic_mastery.get(topic_id, {}).get('current_question_text', '')
        
        # Get lesson_id from current lesson
        lesson = self.adaptive_state.current_lesson
        lesson_id = lesson.get('id', 'unknown') if lesson else 'unknown'
        
        self.adaptive_state.mark_question(topic_id, lesson_id, q_text, user_answer, is_correct, emotion)
        
        # Clear the pending question BEFORE advancing (question was answered)
        self.adaptive_state.clear_pending_question()
        
        # Now advance the state for the NEXT question
        self.adaptive_state.advance_question(topic_id, is_correct, emotion)
        self.adaptive_state.debug_state()
        
        print(f"[RECORD_ANSWER] Answer processed. State is now ready for next question.\n")

    def record_interaction(self, topic_id: str, correct: bool, emotion: str,
                           time_taken: float, distraction_detected: bool) -> None:
        """Record a learning interaction"""
        if not self.current_session:
            return

        self.metrics.total_interactions += 1
        if correct:
            self.metrics.correct_answers += 1
        self.metrics.total_time_spent += time_taken

        self.metrics.emotion_history.append({
            'timestamp': time.time(),
            'emotion': emotion,
            'topic': topic_id,
            'correct': correct
        })

        if topic_id in self.metrics.topic_mastery:
            self.metrics.topic_mastery[topic_id]['questions_asked'] += 1
            if correct:
                self.metrics.topic_mastery[topic_id]['correct_answers'] += 1
            asked = self.metrics.topic_mastery[topic_id]['questions_asked']
            correct_count = self.metrics.topic_mastery[topic_id]['correct_answers']
            self.metrics.topic_mastery[topic_id]['mastery_score'] = (
                correct_count / asked * 100 if asked > 0 else 0
            )

        if distraction_detected:
            self.metrics.distraction_events.append({
                'timestamp': time.time(),
                'topic': topic_id,
                'emotion': emotion
            })

    def block_distraction(self, duration_seconds: int = 3) -> dict:
        self.distraction_block_active = True
        self.distraction_blocked_until = time.time() + duration_seconds
        return {
            'blocked': True,
            'reason': 'distraction_detected',
            'block_duration': duration_seconds,
            'message': 'FOCUS REQUIRED - Remove distractions to continue learning.',
            'retry_after': duration_seconds
        }

    def check_distraction_block(self) -> dict:
        if not self.distraction_block_active:
            return {'blocked': False}
        if time.time() > self.distraction_blocked_until:
            self.distraction_block_active = False
            return {'blocked': False, 'message': 'Distraction cleared! Resuming lesson...'}
        time_remaining = self.distraction_blocked_until - time.time()
        return {
            'blocked': True,
            'time_remaining': round(time_remaining, 1),
            'message': f'Please remove distractions ({round(time_remaining, 1)}s remaining)'
        }

    def get_session_summary(self) -> dict:
        if not self.current_session:
            return {'status': 'no_session'}

        elapsed = time.time() - self.session_start_time
        correctness_rate = (
            self.metrics.correct_answers / self.metrics.total_interactions * 100
            if self.metrics.total_interactions > 0 else 0
        )

        emotions = [e['emotion'] for e in self.metrics.emotion_history]
        emotion_counts = {
            'Engaged': emotions.count('Engaged'),
            'Confused': emotions.count('Confused'),
            'Frustrated': emotions.count('Frustrated'),
            'Bored': emotions.count('Bored')
        } if emotions else {}

        mastered = [(tid, d['mastery_score'])
                    for tid, d in self.metrics.topic_mastery.items()
                    if d['mastery_score'] >= 80]
        struggling = [(tid, d['mastery_score'])
                      for tid, d in self.metrics.topic_mastery.items()
                      if d['mastery_score'] < 50]

        return {
            'session_id': self.current_session.session_id,
            'subject': self.current_session.subject,
            'duration_seconds': round(elapsed, 1),
            'total_interactions': self.metrics.total_interactions,
            'correctness_rate': round(correctness_rate, 1),
            'emotion_distribution': emotion_counts,
            'distraction_events': self.metrics.distraction_events,
            'topic_mastery': self.metrics.topic_mastery,
            'mastered_topics': mastered,
            'struggling_topics': struggling,
            'recommendation': self._get_recommendation(correctness_rate, self.metrics.distraction_events),
            'question_history': self.adaptive_state.question_history if self.adaptive_state else []
        }

    def _get_recommendation(self, correctness_rate: float, distractions: list) -> str:
        if correctness_rate < 50:
            return "Review basics of this topic. Try again when you have fewer distractions."
        elif correctness_rate < 75:
            return "Good progress! Practice the weak areas in your next session."
        elif len(distractions) > 3:
            return "Great learning! Next time, minimize distractions for even better results."
        else:
            return "Excellent session! Ready for advanced topics."


# Global session manager
session_manager = SessionManager()
