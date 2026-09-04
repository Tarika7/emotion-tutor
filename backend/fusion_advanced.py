"""
Fusion Engine: Combines facial emotion, behavioral signals, and environmental factors
to determine final learner state and appropriate teaching strategy
"""

def fuse_emotions(face_emotion: str, behavior_emotion: str, 
                 has_distraction: bool = False, critical_distraction: bool = False) -> tuple:
    """
    Fuse multiple emotion signals to determine final state
    
    Returns: (final_emotion, teaching_strategy, intervention_needed)
    """
    
    # Hard block: Critical distraction overrides everything
    if critical_distraction:
        return ("Distracted", "block_learning", True)
    
    # Priority: Face > Behavior, letting face acting drive the demo
    if face_emotion in ["Frustrated", "Bored", "Confused"]:
        final_emotion = face_emotion
    elif behavior_emotion in ["Frustrated", "Confused", "Bored"] and face_emotion in ["Engaged", "Neutral"]:
        final_emotion = behavior_emotion
    else:
        final_emotion = face_emotion
    
    # Adjust strategy based on distraction
    teaching_strategy = get_teaching_strategy(final_emotion)
    
    if has_distraction and final_emotion not in ["Distracted"]:
        intervention_needed = True
    else:
        intervention_needed = False
    
    return final_emotion, teaching_strategy, intervention_needed

def get_teaching_strategy(emotion: str) -> dict:
    """Determine teaching strategy based on emotional state"""
    
    strategies = {
        "Engaged": {
            "name": "Challenge Mode",
            "difficulty_adjustment": +1,
            "explanation_style": "extended",
            "question_type": "challenge",
            "timeout": 30,
            "hint_threshold": 3,
            "description": "Student is engaged - deliver challenge questions to maintain interest"
        },
        "Confused": {
            "name": "Guided Learning",
            "difficulty_adjustment": 0,
            "explanation_style": "detailed",
            "question_type": "guided",
            "timeout": 60,
            "hint_threshold": 2,
            "description": "Student is confused - provide step-by-step guidance with hints"
        },
        "Frustrated": {
            "name": "Scaffolded Support",
            "difficulty_adjustment": -1,
            "explanation_style": "simplified",
            "question_type": "simplified",
            "timeout": 90,
            "hint_threshold": 1,
            "description": "Student is frustrated - simplify content and provide immediate support"
        },
        "Bored": {
            "name": "Challenge & Interest",
            "difficulty_adjustment": +1,
            "explanation_style": "application_focused",
            "question_type": "real_world",
            "timeout": 20,
            "hint_threshold": 4,
            "description": "Student is bored - introduce challenge and real-world applications"
        },
        "Distracted": {
            "name": "Block & Redirect",
            "difficulty_adjustment": 0,
            "explanation_style": "none",
            "question_type": "none",
            "timeout": 3,
            "hint_threshold": 0,
            "description": "Distraction detected - pause learning and request focus"
        }
    }
    
    return strategies.get(emotion, strategies["Engaged"])

def score_adaptation_quality(emotion: str, strategy_used: str, 
                            answer_correct: bool, time_taken: float) -> float:
    """
    Score how well the adaptation worked
    
    Returns: 0-100 quality score
    """
    
    score = 50  # Base score
    
    # Did the student get it right?
    if answer_correct:
        score += 25
    
    # Was timing reasonable for the emotion?
    expected_times = {
        "Engaged": (5, 30),      # Fast thinking
        "Confused": (10, 90),     # Careful, slow thinking
        "Frustrated": (15, 120),  # Very careful, patient
        "Bored": (3, 20),         # Quick, energized
    }
    
    if emotion in expected_times:
        min_time, max_time = expected_times[emotion]
        if min_time <= time_taken <= max_time:
            score += 15
        elif time_taken < min_time:
            score -= 5  # Too fast, maybe guessing
    
    # Did emotion-strategy match?
    emotion_strategy_match = {
        "Engaged": ["challenge", "extended"],
        "Confused": ["guided", "detailed"],
        "Frustrated": ["simplified", "scaffolded"],
        "Bored": ["challenge", "real_world"]
    }
    
    if emotion in emotion_strategy_match:
        matches = emotion_strategy_match[emotion]
        if any(m in strategy_used.lower() for m in matches):
            score += 10
    
    return min(100, max(0, score))

def tutor_score(face_emotion: str, final_emotion: str, 
               answer_correct: bool = None) -> float:
    """
    Score how well tutor's adaptation aligns with student's state
    
    Returns: 0-1.0 alignment score
    """
    
    # Base score: Did we correctly identify emotion?
    if face_emotion == final_emotion:
        base_score = 1.0
    elif face_emotion in ["Confused", "Frustrated"] and final_emotion == "Engaged":
        base_score = 0.3  # Missed negative state
    elif face_emotion == "Bored" and final_emotion == "Engaged":
        base_score = 0.4  # Partially missed
    else:
        base_score = 0.6  # Mixed signals
    
    # If we know the answer was correct, boost the score
    if answer_correct is True:
        base_score = min(1.0, base_score + 0.2)
    elif answer_correct is False and final_emotion in ["Engaged", "Bored"]:
        base_score = max(0, base_score - 0.2)  # Maybe we were too aggressive
    
    return round(base_score, 2)

def get_intervention_message(emotion: str, has_distraction: bool, 
                            distraction_types: list = None) -> str:
    """Get appropriate intervention message based on state"""
    
    if has_distraction and distraction_types:
        if any(d['type'] == 'phone' for d in distraction_types):
            return "📱 PHONE DETECTED!\n\nPut your phone away to focus on learning. I'll wait. 🕐"
        elif any(d['type'] in ['laptop', 'tablet'] for d in distraction_types):
            return "💻 SCREEN DISTRACTION DETECTED!\n\nFocus only on this lesson. 👀"
        else:
            return "⚠️ DISTRACTION DETECTED!\n\nRemove it and we'll continue. 👍"
    
    emotion_messages = {
        "Frustrated": "I see you're struggling 😟. Let me break this down into simpler steps...",
        "Confused": "I notice some confusion 🤔. Let me explain this more carefully...",
        "Bored": "You seem ready for something harder! 💪 Let's try a challenge...",
        "Engaged": "Great focus! Let's continue with the next concept ⭐",
        "Distracted": "Focus time! Let's keep distractions away 🚫"
    }
    
    return emotion_messages.get(emotion, "Ready to continue? Let's go! 💪")
