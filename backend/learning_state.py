"""
Learning State Classifier
=========================
Maps a detected emotion (optionally enriched with performance context)
to a structured pedagogical "Learning State" that drives all downstream
adaptation decisions.

States
------
Frustrated  → Needs Simplification
Confused    → Needs Guidance
Bored       → Needs Challenge
Engaged     → Optimal Learning
"""

from collections import deque

# ──────────────────────────────────────────────────────────────────────────────
# State descriptor table
# ──────────────────────────────────────────────────────────────────────────────
LEARNING_STATES: dict = {
    "Frustrated": {
        "state":            "Needs Simplification",
        "icon":             "😟",
        "color":            "#ef4444",   # red-500
        "description":      "Student is struggling — break content into tiny steps with encouragement",
        "action":           "simplify",
        "difficulty_delta": -1,
        "hint_level":       3,           # 0 = none, 3 = maximum hints
        "add_encouragement": True,
    },
    "Confused": {
        "state":            "Needs Guidance",
        "icon":             "🤔",
        "color":            "#f59e0b",   # amber-500
        "description":      "Student is lost — provide structured, step-by-step guidance",
        "action":           "guide",
        "difficulty_delta": 0,
        "hint_level":       2,
        "add_encouragement": False,
    },
    "Bored": {
        "state":            "Needs Challenge",
        "icon":             "😴",
        "color":            "#6366f1",   # indigo-500
        "description":      "Student is under-stimulated — raise difficulty and introduce challenge",
        "action":           "challenge",
        "difficulty_delta": +1,
        "hint_level":       0,
        "add_encouragement": False,
    },
    "Engaged": {
        "state":            "Optimal Learning",
        "icon":             "😊",
        "color":            "#22c55e",   # green-500
        "description":      "Student is in the flow — maintain pace and progressive complexity",
        "action":           "continue",
        "difficulty_delta": 0,
        "hint_level":       1,
        "add_encouragement": False,
    },
}

# Fallback for unknown emotions
_DEFAULT_STATE = LEARNING_STATES["Engaged"]


class LearningStateClassifier:
    """
    Stateful classifier that smooths the learning state over a history window
    and escalates to Frustrated if the student answers wrong repeatedly.
    """

    def __init__(self, history_window: int = 5):
        self.history: deque = deque(maxlen=history_window)

    # ------------------------------------------------------------------
    def classify(self, emotion: str, consecutive_incorrect: int = 0) -> dict:
        """
        Classify the current learning state.

        Parameters
        ----------
        emotion              : final fused emotion label
        consecutive_incorrect: how many wrong answers in a row

        Returns
        -------
        Full state dict (all keys from LEARNING_STATES plus extras)
        """

        # Performance escalation: ≥ 3 wrong in a row → force Frustrated
        if consecutive_incorrect >= 3 and emotion in ("Confused", "Engaged", "Bored"):
            emotion = "Frustrated"

        self.history.append(emotion)

        state_data = LEARNING_STATES.get(emotion, _DEFAULT_STATE)

        # Detect persistent negative state (≥ 60 % of recent window is negative)
        neg_count = sum(1 for e in self.history if e in ("Frustrated", "Confused"))
        persistent_negative = (
            len(self.history) >= 3
            and neg_count / len(self.history) >= 0.60
        )

        return {
            "emotion":           emotion,
            "learning_state":    state_data["state"],
            "state_icon":        state_data["icon"],
            "state_color":       state_data["color"],
            "state_description": state_data["description"],
            "adaptation_action": state_data["action"],
            "difficulty_delta":  state_data["difficulty_delta"],
            "hint_level":        state_data["hint_level"],
            "add_encouragement": state_data["add_encouragement"],
            "persistent_negative": persistent_negative,
        }

    # ------------------------------------------------------------------
    def current_state_label(self) -> str:
        """Quick accessor for the most recent learning_state string."""
        if not self.history:
            return "Optimal Learning"
        last = self.history[-1]
        return LEARNING_STATES.get(last, _DEFAULT_STATE)["state"]
