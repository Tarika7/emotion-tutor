path = r'c:\Users\tarik\Desktop\emotion-tutor\backend\session_manager.py'
content = open(path, 'r', encoding='utf-8').read()
c = content.replace('\r\n', '\n')

# 1. Add consecutive_incorrect to SessionMetrics
c = c.replace(
    '    topic_mastery: dict = field(default_factory=dict)\n',
    '    topic_mastery: dict = field(default_factory=dict)\n'
    '    consecutive_incorrect: int = 0  # streak of wrong answers in a row\n',
    1
)

# 2. Add engine instance vars to SessionManager.__init__
c = c.replace(
    '        self.distraction_blocked_until = None\n'
    '        self.distraction_block_active = False\n',
    '        self.distraction_blocked_until = None\n'
    '        self.distraction_block_active = False\n'
    '        # AI Enhancement Layer (one instance per session)\n'
    '        self.emotion_engine      = None\n'
    '        self.learning_classifier = None\n'
    '        self.adaptation_engine   = None\n'
    '        self.engagement_tracker  = None\n',
    1
)

# 3. Initialize engines in create_session
c = c.replace(
    '        # Init adaptive state\n'
    '        self.adaptive_state = AdaptiveSessionState(topics)\n'
    '\n'
    '        # Init topic mastery',
    '        # Init adaptive state\n'
    '        self.adaptive_state = AdaptiveSessionState(topics)\n'
    '\n'
    '        # Init AI Enhancement Layer\n'
    '        from emotion_engine import EmotionFusionEngine\n'
    '        from learning_state import LearningStateClassifier\n'
    '        from adaptation_engine import AdaptationEngine\n'
    '        from engagement_tracker import EngagementTracker\n'
    '        self.emotion_engine      = EmotionFusionEngine()\n'
    '        self.learning_classifier = LearningStateClassifier()\n'
    '        self.adaptation_engine   = AdaptationEngine()\n'
    '        self.engagement_tracker  = EngagementTracker()\n'
    '        self.metrics.consecutive_incorrect = 0\n'
    '        print("[SESSION] AI Enhancement Layer initialised")\n'
    '\n'
    '        # Init topic mastery',
    1
)

# 4. Track consecutive_incorrect in record_answer
c = c.replace(
    '        # Clear the pending question BEFORE advancing (question was answered)\n'
    '        self.adaptive_state.clear_pending_question()\n'
    '\n'
    '        # Now advance the state for the NEXT question',
    '        # Clear the pending question BEFORE advancing (question was answered)\n'
    '        self.adaptive_state.clear_pending_question()\n'
    '\n'
    '        # Update consecutive incorrect streak\n'
    '        if is_correct:\n'
    '            self.metrics.consecutive_incorrect = 0\n'
    '        else:\n'
    '            self.metrics.consecutive_incorrect = getattr(self.metrics, "consecutive_incorrect", 0) + 1\n'
    '\n'
    '        # Now advance the state for the NEXT question',
    1
)

open(path, 'w', encoding='utf-8', newline='\r\n').write(c.replace('\n', '\r\n'))
print('SUCCESS')
