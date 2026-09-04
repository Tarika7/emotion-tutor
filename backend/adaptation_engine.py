"""
Real-Time Adaptation Engine
============================
Decides HOW to modify teaching behaviour based on the current learning state.
Returns a complete adaptation parameter set consumed by the lesson generator
and the Ollama prompt builder.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Teaching-style descriptors (keyed by adaptation_action)
# ──────────────────────────────────────────────────────────────────────────────
EXPLANATION_STYLES: dict = {
    "simplify": {
        "tone":             "Very simple, step-by-step, highly encouraging",
        "length":           "short",
        "use_analogies":    True,
        "use_examples":     True,
        "show_hints":       True,
        "encouragement_prefix": "You're doing great — let's slow down and try together. ",
        "directives": [
            "Break the concept into the absolute smallest steps possible.",
            "Use very simple language and a relatable everyday analogy.",
            "Start with a warm, encouraging sentence.",
            "End with a simple check-in question ('Does that make sense?').",
        ],
    },
    "guide": {
        "tone":             "Structured, methodical, patient",
        "length":           "medium",
        "use_analogies":    True,
        "use_examples":     True,
        "show_hints":       True,
        "encouragement_prefix": "",
        "directives": [
            "Provide a numbered, step-by-step explanation.",
            "Use a concrete real-world example.",
            "Highlight the key rule or principle in bold terms.",
            "Offer a 2-level hint if the student gets stuck.",
        ],
    },
    "challenge": {
        "tone":             "Advanced, exploratory, high-energy",
        "length":           "concise",
        "use_analogies":    False,
        "use_examples":     False,
        "show_hints":       False,
        "encouragement_prefix": "",
        "directives": [
            "Skip basics — present an advanced 'what if' or application challenge.",
            "Require the student to synthesise two or more concepts.",
            "Add a competitive or puzzle framing to boost engagement.",
        ],
    },
    "continue": {
        "tone":             "Enthusiastic, progressive, connecting",
        "length":           "normal",
        "use_analogies":    False,
        "use_examples":     True,
        "show_hints":       False,
        "encouragement_prefix": "",
        "directives": [
            "Maintain momentum — connect this lesson to the previous one.",
            "Include one interesting extension or 'did you know?' fact.",
            "Keep the explanation confident and forward-moving.",
        ],
    },
}


class AdaptationEngine:
    """
    Stateless engine: given a learning-state result and current session metrics,
    returns a full adaptation parameter dict for the lesson generator.
    """

    def adapt(
        self,
        learning_state_result: dict,
        current_difficulty: int,
        correctness_rate: float,
        consecutive_incorrect: int,
    ) -> dict:
        """
        Compute adaptation decisions.

        Parameters
        ----------
        learning_state_result  : output of LearningStateClassifier.classify()
        current_difficulty     : current topic difficulty 1-5
        correctness_rate       : session accuracy 0-1
        consecutive_incorrect  : streak of wrong answers

        Returns
        -------
        dict with teaching parameters consumed by claude.py
        """
        action               = learning_state_result.get("adaptation_action", "continue")
        difficulty_delta     = learning_state_result.get("difficulty_delta",  0)
        hint_level           = learning_state_result.get("hint_level",        1)
        add_encouragement    = learning_state_result.get("add_encouragement", False)
        persistent_negative  = learning_state_result.get("persistent_negative", False)

        # Force difficulty reduction on persistent struggle
        if persistent_negative:
            difficulty_delta = min(difficulty_delta, -1)

        new_difficulty = max(1, min(5, current_difficulty + difficulty_delta))

        style = EXPLANATION_STYLES.get(action, EXPLANATION_STYLES["continue"])

        # Slow question progression when student is repeatedly wrong
        slow_progression = (action == "simplify" and consecutive_incorrect >= 2)

        # Build the system-prompt injection for Ollama
        system_directives = list(style["directives"])
        if add_encouragement and style["encouragement_prefix"]:
            system_directives.insert(0, f'Begin with: "{style["encouragement_prefix"].strip()}"')

        return {
            "adaptation_action":   action,
            "explanation_style":   style["tone"],
            "explanation_length":  style["length"],
            "new_difficulty":      new_difficulty,
            "difficulty_delta":    difficulty_delta,
            "hint_level":          hint_level,
            "hints_enabled":       hint_level > 0,
            "add_encouragement":   add_encouragement,
            "slow_progression":    slow_progression,
            "use_analogies":       style["use_analogies"],
            "use_examples":        style["use_examples"],
            "prompt_prefix":       style["encouragement_prefix"],
            "teaching_directives": system_directives,
        }
