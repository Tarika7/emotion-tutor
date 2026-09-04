"""
Emotion Fusion Engine
=====================
Combines facial emotion (SVM/MediaPipe), behavioral performance signals
(accuracy, response time), and interaction delay into a single weighted
final emotion.

Weights:  behavioral  = 0.65 (more reliable — based on observable actions)
          facial      = 0.35 (noisy — lighting, angle, model accuracy)

If the two signals conflict, behavioral signal wins.
If no face is detected for > 45 s, the learner is marked disengaged.
"""

from collections import Counter, deque
import time

# Numeric weight per emotion (higher = more positive / engaged)
EMOTION_SCORE = {
    "Engaged":    4,
    "Bored":      3,
    "Confused":   2,
    "Frustrated": 1,
}
SCORE_TO_EMOTION = {4: "Engaged", 3: "Bored", 2: "Confused", 1: "Frustrated"}

FACE_WEIGHT      = 0.35
BEHAVIOR_WEIGHT  = 0.65
INACTIVITY_SECS  = 45   # seconds before "no face" triggers disengaged


class EmotionFusionEngine:
    """
    Stateful engine that fuses facial + behavioral emotion signals
    over a sliding window for stability.
    """

    def __init__(self, window_size: int = 7):
        self.face_window     = deque(maxlen=window_size)
        self.behavior_window = deque(maxlen=window_size)
        self.last_face_time  = time.time()

    # ------------------------------------------------------------------
    def update(
        self,
        face_emotion: str,
        accuracy: float = None,
        response_time: float = None,
        is_correct: bool = None,
    ) -> dict:
        """
        Fuse all signals and return a rich result dict.

        Parameters
        ----------
        face_emotion   : raw label from emotion.py  ("Engaged" / "No Face" / …)
        accuracy       : rolling session accuracy 0-1 (None if no answers yet)
        response_time  : seconds taken for last answer (None between questions)
        is_correct     : outcome of last answer (None if no answer yet)

        Returns
        -------
        dict with keys:
            final_emotion, face_emotion, behavior_emotion,
            conflict_detected, confidence, attention_state, dominant_signal
        """
        now = time.time()

        # ----- Attention state -----
        if face_emotion != "No Face":
            self.last_face_time = now
            attention_state = "active"
        else:
            idle = now - self.last_face_time
            attention_state = "disengaged" if idle > INACTIVITY_SECS else "no_face"

        # ----- Facial signal (sliding-window majority vote) -----
        if face_emotion != "No Face":
            self.face_window.append(face_emotion)
        face_vote = self._majority_vote(self.face_window) or "Engaged"

        # ----- Behavioral signal -----
        behavior_signal = self._behavioral_emotion(accuracy, response_time, is_correct)
        self.behavior_window.append(behavior_signal)
        behavior_vote = self._majority_vote(self.behavior_window) or "Engaged"

        # ----- Weighted fusion & Conflict handling -----
        if not behavior_vote:
            # If no behavior history exists yet, trust face entirely
            final_emotion = face_vote
            conflict = False
        else:
            f_score = EMOTION_SCORE.get(face_vote,     4)
            b_score = EMOTION_SCORE.get(behavior_vote, 4)
            
            # Simple weighted fusion
            weighted = f_score * FACE_WEIGHT + b_score * BEHAVIOR_WEIGHT
            fused_score = max(1, min(4, round(weighted)))
            fused_emotion = SCORE_TO_EMOTION[fused_score]
            
            conflict = (face_vote != behavior_vote)
            # Only let behavior hard-override if the conflict is extreme (e.g. 3 levels apart)
            # Otherwise, trust the numerical fusion.
            if conflict and abs(f_score - b_score) >= 2:
                final_emotion = behavior_vote
            else:
                final_emotion = fused_emotion

        # ----- Inactivity override -----
        if attention_state == "disengaged":
            final_emotion = "Frustrated"

        # ----- Confidence -----
        agreement   = 1.0 if not conflict else 0.5
        window_fill = min(1.0, len(self.face_window) / 5)
        confidence  = round(agreement * window_fill, 2)

        return {
            "final_emotion":    final_emotion,
            "face_emotion":     face_vote,
            "behavior_emotion": behavior_vote,
            "conflict_detected": conflict,
            "confidence":       confidence,
            "attention_state":  attention_state,
            "dominant_signal":  "behavior" if conflict else "fused",
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _majority_vote(self, window: deque) -> str:
        """Majority vote over the window, ignoring 'No Face'."""
        counts = Counter(e for e in window if e != "No Face")
        return counts.most_common(1)[0][0] if counts else ""

    def _behavioral_emotion(
        self,
        accuracy: float,
        response_time: float,
        is_correct: bool,
    ) -> str:
        """
        Derive an emotion label purely from performance metrics.

        Rules (in priority order):
          1. Very low accuracy  → Frustrated
          2. Medium accuracy + slow response → Frustrated
          3. Medium accuracy → Confused
          4. High accuracy + very fast (breezing) → Bored
          5. High accuracy → Engaged
        """
        if accuracy is None:
            return ""   # no data yet, return empty to let face govern

        if accuracy < 0.30:
            return "Frustrated"

        if accuracy < 0.55:
            if response_time is not None and response_time > 20:
                return "Frustrated"
            return "Confused"

        if accuracy >= 0.80 and response_time is not None and response_time < 5:
            return "Bored"

        if accuracy >= 0.65:
            return "Engaged"

        return "Confused"
