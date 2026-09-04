"""
Engagement Tracking System
===========================
Logs every emotion sample and Q&A interaction during a session.
Computes a live engagement score (0-100) with trend detection.
Monitors for inactivity / attention loss.
"""

import time
from collections import deque
from typing import Optional

# Engagement value per emotion (used for score weighting)
EMOTION_WEIGHT: dict = {
    "Engaged":    1.0,
    "Bored":      0.35,
    "Confused":   0.55,
    "Frustrated": 0.40,
    "No Face":    0.0,
    "Distracted": 0.0,
}

PAUSE_AFTER_SECS = 60   # pause session if no face for this long


class EngagementTracker:
    """
    Tracks learner engagement throughout a session.

    Maintains two parallel logs:
      emotion_history     — sampled at every /get_state_advanced call
      performance_history — one entry per Q&A interaction

    Computes engagement_score from:
      50 % emotion quality
      35 % answer accuracy
      15 % response-time consistency
    """

    def __init__(self, recent_window: int = 20):
        # Full session logs
        self.emotion_history:     list = []
        self.performance_history: list = []

        # Sliding window for live score
        self.recent_emotions:     deque = deque(maxlen=recent_window)
        self.recent_performance:  deque = deque(maxlen=recent_window)

        self._session_start      = time.time()
        self.total_interactions  = 0
        self.correct_count       = 0

        # Inactivity tracking
        self._inactivity_start: Optional[float] = None
        self._last_activity     = time.time()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_emotion(self, emotion: str, attention_state: str = "active") -> None:
        """Record a detected emotion sample."""
        ts    = time.time()
        entry = {
            "ts":              ts,
            "elapsed":         round(ts - self._session_start, 1),
            "emotion":         emotion,
            "attention_state": attention_state,
        }
        self.emotion_history.append(entry)
        self.recent_emotions.append(emotion)

        # Track inactivity
        if attention_state in ("no_face", "disengaged"):
            if self._inactivity_start is None:
                self._inactivity_start = ts
        else:
            self._inactivity_start = None
            self._last_activity    = ts

    def log_interaction(
        self,
        emotion: str,
        is_correct: bool,
        response_time: float,
        difficulty: int,
    ) -> None:
        """Record one complete Q&A interaction."""
        ts = time.time()
        self.total_interactions += 1
        if is_correct:
            self.correct_count += 1

        entry = {
            "ts":            ts,
            "elapsed":       round(ts - self._session_start, 1),
            "emotion":       emotion,
            "is_correct":    is_correct,
            "response_time": response_time,
            "difficulty":    difficulty,
        }
        self.performance_history.append(entry)
        self.recent_performance.append(entry)
        self._last_activity    = ts
        self._inactivity_start = None

    # ------------------------------------------------------------------
    # Score computation
    # ------------------------------------------------------------------

    def compute_engagement_score(self) -> dict:
        """
        Returns:
            score          : 0-100 integer
            trend          : "improving" | "stable" | "declining"
            label          : human-readable label
            total_interactions
            accuracy       : % correct so far
        """
        # ── Emotion score (50 %) ──────────────────────────────────────
        emotion_avg = 0.5
        if self.recent_emotions:
            weights    = [EMOTION_WEIGHT.get(e, 0.5) for e in self.recent_emotions]
            emotion_avg = sum(weights) / len(weights)

        # ── Accuracy score (35 %) ─────────────────────────────────────
        accuracy_score = 0.5
        if self.total_interactions > 0:
            accuracy_score = self.correct_count / self.total_interactions

        # ── Response-time consistency (15 %) ──────────────────────────
        time_score = 0.7
        if self.recent_performance:
            times = [p["response_time"] for p in self.recent_performance
                     if p["response_time"] is not None and p["response_time"] < 180]
            if times:
                avg_t = sum(times) / len(times)
                if 5 <= avg_t <= 35:
                    time_score = 1.0
                elif avg_t < 5:
                    time_score = 0.5   # suspiciously fast
                else:
                    time_score = max(0.3, 1.0 - (avg_t - 35) / 90)

        raw   = emotion_avg * 0.50 + accuracy_score * 0.35 + time_score * 0.15
        score = round(raw * 100)

        # ── Inactivity penalty ────────────────────────────────────────
        label = self._score_label(score)
        if self._inactivity_start:
            idle = time.time() - self._inactivity_start
            if idle > 20:
                score = max(0, score - int(idle / 3))
                label = "Attention Lost"

        score = max(0, min(100, score))
        trend = self._compute_trend()

        accuracy_pct = (
            round(self.correct_count / self.total_interactions * 100, 1)
            if self.total_interactions > 0 else 0
        )

        return {
            "score":              score,
            "trend":              trend,
            "label":              label,
            "total_interactions": self.total_interactions,
            "accuracy":           accuracy_pct,
        }

    # ------------------------------------------------------------------

    def should_pause_session(self) -> dict:
        """Return pause recommendation if learner has been absent too long."""
        if not self._inactivity_start:
            return {"pause": False}
        idle = time.time() - self._inactivity_start
        if idle >= PAUSE_AFTER_SECS:
            return {
                "pause":              True,
                "reason":             f"No activity detected for {round(idle)}s — please check if you're still there.",
                "inactivity_seconds": round(idle),
            }
        return {"pause": False}

    def get_timeline(self, n: int = 15) -> list:
        """Last n emotion timeline entries for the frontend chart."""
        return self.emotion_history[-n:]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _score_label(self, score: int) -> str:
        if score >= 80: return "Highly Engaged"
        if score >= 60: return "Engaged"
        if score >= 40: return "Partially Engaged"
        return "Disengaged"

    def _compute_trend(self) -> str:
        """Compare first vs second half of recent emotion window."""
        if len(self.recent_emotions) < 4:
            return "stable"
        mid   = len(self.recent_emotions) // 2
        lst   = list(self.recent_emotions)
        first = sum(EMOTION_WEIGHT.get(e, 0.5) for e in lst[:mid]) / mid
        secon = sum(EMOTION_WEIGHT.get(e, 0.5) for e in lst[mid:]) / (len(lst) - mid)
        diff  = secon - first
        if diff >  0.15: return "improving"
        if diff < -0.15: return "declining"
        return "stable"
