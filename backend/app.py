from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import cv2
import time
import sys
import os
import uuid
import base64
import numpy as np
import hashlib
from werkzeug.utils import secure_filename
import io

# Force UTF-8 encoding for Windows console output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from emotion import get_emotion
from cognitive import cognitive_score
from claude import generate_dynamic_lesson
from session_manager import session_manager
from fusion_advanced import get_teaching_strategy, get_intervention_message
from challenge_quiz import ChallengeQuizGenerator
from distraction_detector import detector

app = Flask(__name__, static_folder="../frontend")
CORS(app)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Lightweight globals (fallback only — real state lives in session_manager engines)
timeline: list = []


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# NAVIGATION & STATIC FILES
# ============================================================================

@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)


# ============================================================================
# PDF & COURSE GENERATION
# ============================================================================

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    """Handle PDF upload and generate a structured course outline (fast path)."""
    try:
        file = request.files.get('pdf') or request.files.get('file')
        if not file or file.filename == '':
            return jsonify({"error": "No PDF file provided"}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        print(f"Processing PDF: {filename}")
        from pdf_processor import process_pdf_to_full_course
        processed  = process_pdf_to_full_course(filepath)
        course_data = processed.get('course_data')
        full_text   = processed.get('full_text', '')

        if not course_data or 'topics' not in course_data:
            return jsonify({"error": "Failed to generate course structure"}), 500

        course_data['full_text'] = full_text
        topics = course_data.get('topics', [])
        print(f"Course outline: {len(topics)} topics")

        return jsonify({
            "status":             "success",
            "course_data":        course_data,
            "topic_count":        len(topics),
            "main_topic":         course_data.get('main_topic', 'Study Material'),
            "learning_objectives": course_data.get("learning_objectives", []),
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

@app.route("/create_session", methods=["POST"])
def create_session():
    """Start a learning session with the given course structure."""
    try:
        data        = request.json
        topic_data  = data.get("topic_data")
        time_minutes = int(data.get("time_minutes", 15))

        if not topic_data:
            return jsonify({"error": "Missing course content"}), 400

        session_id = str(uuid.uuid4())[:8]
        result = session_manager.create_session(
            session_id=session_id,
            topic_data=topic_data,
            questions={},
            subject="General",
            time_minutes=time_minutes,
        )
        return jsonify({**result, "message": f"Session {session_id} started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/session_info", methods=["GET"])
def get_sess_info():
    return jsonify(session_manager.get_session_info())


# ============================================================================
# EMOTION & STATE  —  AI ENHANCEMENT LAYER
# ============================================================================

@app.route("/get_state_advanced", methods=["POST"])
def get_state_advanced():
    """
    Real-time emotion detection with full AI Enhancement Layer:
      Facial emotion → EmotionFusionEngine → LearningStateClassifier
      → EngagementTracker → enriched response
    """
    try:
        data      = request.json
        frame_b64 = data.get("frame")
        start     = time.time()

        # ── Decode frame ──────────────────────────────────────────────
        ret, frame = False, None
        if frame_b64:
            try:
                raw   = frame_b64.split(',')[1] if ',' in frame_b64 else frame_b64
                nparr = np.frombuffer(base64.b64decode(raw), np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                ret   = frame is not None
            except Exception:
                pass

        # ── Raw face emotion ──────────────────────────────────────────
        face_emotion = get_emotion(frame) if ret else "No Face"

        # ── Distraction detection (YOLO) ──────────────────────────────
        has_distractions, critical_distraction, distractions = False, False, []
        if ret and frame is not None:
            try:
                dr               = detector.detect_distractions(frame)
                has_distractions = dr.get('has_distractions', False)
                critical_distraction = dr.get('critical_distraction', False)
                distractions     = dr.get('distractions', [])
            except Exception as det_err:
                print(f"[DETECT] {det_err}")

        # ── Hard blocks ───────────────────────────────────────────────
        if critical_distraction:
            return jsonify(session_manager.block_distraction(duration_seconds=5))
        block = session_manager.check_distraction_block()
        if block.get('blocked'):
            return jsonify(block)

        # ── Session performance metrics (for behavioral signal) ───────
        total       = session_manager.metrics.total_interactions
        correct     = session_manager.metrics.correct_answers
        accuracy    = correct / total if total > 0 else None
        consec_wrong = getattr(session_manager.metrics, 'consecutive_incorrect', 0)

        # ── 1. EMOTION FUSION ENGINE ─────────────────────────────────
        fusion = {
            "final_emotion":    face_emotion if face_emotion != "No Face" else "Engaged",
            "face_emotion":     face_emotion,
            "behavior_emotion": "Engaged",
            "conflict_detected": False,
            "confidence":       0.5,
            "attention_state":  "active",
            "dominant_signal":  "face",
        }
        if session_manager.emotion_engine:
            fusion = session_manager.emotion_engine.update(
                face_emotion=face_emotion,
                accuracy=accuracy,
                response_time=None,
                is_correct=None,
            )

        final_emotion   = fusion["final_emotion"]
        attention_state = fusion["attention_state"]

        # ── 2. LEARNING STATE CLASSIFICATION ─────────────────────────
        ls = {
            "learning_state":    "Optimal Learning",
            "state_icon":        "😊",
            "state_color":       "#22c55e",
            "state_description": "Maintaining good progress.",
            "adaptation_action": "continue",
        }
        if session_manager.learning_classifier:
            ls = session_manager.learning_classifier.classify(final_emotion, consec_wrong)

        # ── 3. ENGAGEMENT TRACKING ────────────────────────────────────
        eng = {"score": 50, "trend": "stable", "label": "Loading...", "accuracy": 0}
        if session_manager.engagement_tracker:
            session_manager.engagement_tracker.log_emotion(final_emotion, attention_state)
            eng = session_manager.engagement_tracker.compute_engagement_score()

            pause = session_manager.engagement_tracker.should_pause_session()
            if pause.get("pause"):
                return jsonify({
                    "status":          "paused",
                    "paused":          True,
                    "reason":          pause["reason"],
                    "emotion":         final_emotion,
                    "engagement_score": eng["score"],
                })

        # ── Teaching strategy ─────────────────────────────────────────
        teaching_strategy   = get_teaching_strategy(final_emotion)
        intervention_needed = has_distractions or attention_state in ("no_face", "disengaged")

        # ── Timeline ─────────────────────────────────────────────────
        session_info = session_manager.get_session_info()
        timeline.append({"timestamp": time.time(), "emotion": final_emotion})
        if len(timeline) > 50:
            timeline.pop(0)

        return jsonify({
            "status": "success",
            # — Emotion signals —
            "emotion":            final_emotion,
            "face_emotion":       face_emotion,
            "behavior_emotion":   fusion.get("behavior_emotion", final_emotion),
            "conflict_detected":  fusion.get("conflict_detected", False),
            "emotion_confidence": fusion.get("confidence", 0.5),
            "attention_state":    attention_state,
            # — Learning state —
            "learning_state":     ls.get("learning_state",    "Optimal Learning"),
            "state_icon":         ls.get("state_icon",        "😊"),
            "state_color":        ls.get("state_color",       "#22c55e"),
            "state_description":  ls.get("state_description", ""),
            "adaptation_action":  ls.get("adaptation_action", "continue"),
            # — Engagement —
            "engagement_score":   eng.get("score",  50),
            "engagement_label":   eng.get("label",  "Loading..."),
            "engagement_trend":   eng.get("trend",  "stable"),
            # — Teaching —
            "teaching_strategy":   teaching_strategy,
            "intervention_needed": intervention_needed,
            # — Distractions —
            "has_distractions":   has_distractions,
            "distractions":       distractions,
            # — Meta —
            "latency_ms":        round((time.time() - start) * 1000, 2),
            "session_info":      session_info,
            "timeline":          timeline[-10:],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# LESSON DELIVERY  —  ADAPTIVE CONTENT
# ============================================================================

@app.route("/get_next_lesson", methods=["POST"])
def get_next_lesson():
    """
    Fetch next lesson block. Adapts content via AdaptationEngine based on
    the current LearningState and session performance.
    """
    try:
        data     = request.json
        topic_id = data.get("topic_id")
        emotion  = data.get("emotion", "Engaged")

        if not session_manager.current_session:
            return jsonify({"error": "No session active"}), 400

        # 1. Return pending question if student hasn't answered yet
        pending = session_manager.adaptive_state.get_pending_question()
        if pending:
            return jsonify(pending)

        # 2. Get curriculum position context
        ctx = session_manager.get_next_question_context(topic_id, emotion)
        if not ctx:
            return jsonify({"error": "Topic complete"}), 200

        # 3. Compute adaptation parameters via AI Enhancement Layer ─────
        total           = session_manager.metrics.total_interactions
        correct         = session_manager.metrics.correct_answers
        correctness_rate = correct / total if total > 0 else 0.5
        consec_wrong    = getattr(session_manager.metrics, 'consecutive_incorrect', 0)
        current_diff    = ctx.get('difficulty', 1)

        ls = {
            "learning_state":    "Optimal Learning",
            "state_icon":        "😊",
            "state_color":       "#22c55e",
            "adaptation_action": "continue",
        }
        adap = {
            "adaptation_action":  "continue",
            "new_difficulty":     current_diff,
            "hints_enabled":      False,
            "teaching_directives": [],
            "prompt_prefix":      "",
        }

        if session_manager.learning_classifier:
            ls = session_manager.learning_classifier.classify(emotion, consec_wrong)
        if session_manager.adaptation_engine:
            adap = session_manager.adaptation_engine.adapt(
                learning_state_result=ls,
                current_difficulty=current_diff,
                correctness_rate=correctness_rate,
                consecutive_incorrect=consec_wrong,
            )

        # 4. Lazy-load lesson content if needed ──────────────────────────
        lesson_data  = ctx.get('lesson', {})
        pre_question = ctx.get('pregenerated_question', {})

        if not lesson_data.get('explanation'):
            pass # BYPASSED the 3-minute heavy generation to allow fast fallback!

        # 5. Generate adapted lesson ──────────────────────────────────────
        lesson = generate_dynamic_lesson(
            topic_data=ctx['topic'],
            emotion=emotion,
            question_index=ctx['question_index'],
            pre_generated_lesson=lesson_data,
            pre_generated_question=pre_question,
            adaptation_params=adap,
        )

        # 6. State management ─────────────────────────────────────────────
        q_id = hashlib.md5(
            f"{topic_id}_{ctx['lesson_index']}_{ctx['question_index']}".encode()
        ).hexdigest()[:8]

        # Resolve name-based topic_id → id-based key
        resolved_id = topic_id
        if session_manager.current_session:
            for t in session_manager.current_session.topic_data.get('topics', []):
                if t.get('name') == topic_id or t.get('title') == topic_id:
                    resolved_id = t.get('id', topic_id)
                    break
            if resolved_id == topic_id and session_manager.adaptive_state:
                ct = session_manager.adaptive_state.current_topic
                if ct:
                    resolved_id = ct.get('id', topic_id)

        session_manager.store_expected_answer(
            topic_id=resolved_id,
            question_text=lesson.get('question', ''),
            answer_text=lesson.get('answer', ''),
            hint=lesson.get('hint', ''),
        )
        session_manager.adaptive_state.set_pending_question(q_id, lesson)

        # 7. Enrich response with AI layer metadata ───────────────────────
        eng = {"score": 50, "trend": "stable", "label": "Loading..."}
        if session_manager.engagement_tracker:
            eng = session_manager.engagement_tracker.compute_engagement_score()

        lesson["learning_state"]    = ls.get("learning_state",    "Optimal Learning")
        lesson["state_icon"]        = ls.get("state_icon",        "😊")
        lesson["state_color"]       = ls.get("state_color",       "#22c55e")
        lesson["adaptation_action"] = adap.get("adaptation_action", "continue")
        lesson["difficulty"]        = adap.get("new_difficulty",   current_diff)
        lesson["hints_enabled"]     = adap.get("hints_enabled",    False)
        lesson["engagement_score"]  = eng.get("score", 50)
        lesson["_debug"] = {
            "q_id": q_id,
            "pos":  f"T{ctx['topic_index']}:L{ctx['lesson_index']}:Q{ctx['question_index']}",
        }

        return jsonify(lesson)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ANSWER EVALUATION  —  ADAPTIVE EXPLANATION
# ============================================================================

@app.route("/submit_answer_advanced", methods=["POST"])
def submit_answer_advanced():
    """
    Evaluate student answer, generate emotion-adapted AI explanation,
    log the interaction to EngagementTracker, and advance curriculum state.
    """
    try:
        data        = request.json
        user_answer = (data.get("answer") or "").strip()
        topic_id    = data.get("topic_id", "unknown")
        emotion     = data.get("emotion", "Engaged")
        time_taken  = float(data.get("time_taken", 5))

        pending = session_manager.adaptive_state.get_pending_question()
        if not pending:
            return jsonify({"error": "No pending question"}), 400

        # ── Resolve topic_id (name → id) ─────────────────────────────
        resolved_id = topic_id
        if topic_id not in session_manager.metrics.topic_mastery:
            for t in (session_manager.current_session.topic_data.get('topics', [])
                      if session_manager.current_session else []):
                if t.get('name') == topic_id or t.get('title') == topic_id:
                    resolved_id = t.get('id', topic_id)
                    break
            if resolved_id not in session_manager.metrics.topic_mastery:
                ct = session_manager.adaptive_state.current_topic if session_manager.adaptive_state else None
                if ct:
                    resolved_id = ct.get('id', topic_id)

        mastery       = session_manager.metrics.topic_mastery.get(resolved_id, {})
        expected      = mastery.get('expected_answer', '')
        question_text = mastery.get('current_question_text', '')

        # ── 1. Evaluate correctness ───────────────────────────────────
        is_correct = False
        if expected:
            keywords = [w.lower() for w in expected.split() if len(w) > 3]
            if not keywords:
                keywords = [expected.lower()]
            matches    = [k for k in keywords if k in user_answer.lower()]
            is_correct = bool(matches) or user_answer.lower() == expected.lower()

        # ── 2. Update session state ───────────────────────────────────
        session_manager.record_answer(resolved_id, user_answer, is_correct, emotion, time_taken, False)

        # ── 3. Log interaction to Engagement Tracker ──────────────────
        current_diff = 1
        if session_manager.adaptive_state and session_manager.adaptive_state.current_topic:
            current_diff = session_manager.adaptive_state.current_topic.get('difficulty', 1)

        if session_manager.engagement_tracker:
            session_manager.engagement_tracker.log_interaction(
                emotion=emotion,
                is_correct=is_correct,
                response_time=time_taken,
                difficulty=current_diff,
            )

        # ── 4. Get updated learning state for adaptive explanation ────
        consec_wrong = getattr(session_manager.metrics, 'consecutive_incorrect', 0)
        ls = {"learning_state": "Optimal Learning", "adaptation_action": "continue"}
        adap = {"explanation_style": "standard", "prompt_prefix": "", "teaching_directives": []}

        if session_manager.learning_classifier:
            ls = session_manager.learning_classifier.classify(emotion, consec_wrong)
        if session_manager.adaptation_engine:
            total   = session_manager.metrics.total_interactions
            correct = session_manager.metrics.correct_answers
            adap = session_manager.adaptation_engine.adapt(
                learning_state_result=ls,
                current_difficulty=current_diff,
                correctness_rate=correct / total if total > 0 else 0.5,
                consecutive_incorrect=consec_wrong,
            )

        # ── 5. Generate AI-adapted explanation (Ollama) ───────────────
        from claude import call_ollama, PEDAGOGY_RULES
        rules = PEDAGOGY_RULES.get(emotion, PEDAGOGY_RULES["Engaged"])

        directives_text = ""
        if adap.get("teaching_directives"):
            directives_text = "\n".join(f"- {d}" for d in adap["teaching_directives"])

        encourage = adap.get("prompt_prefix", "")

        prompt = f"""You are a {adap.get('explanation_style', 'friendly')} tutor.
Student answered a question.
QUESTION: {question_text}
STUDENT ANSWER: {user_answer}
CORRECT ANSWER: {expected}
RESULT: {'Correct!' if is_correct else 'Incorrect'}
STUDENT STATE: {ls.get('learning_state', 'Engaged')} ({emotion})
{f'TEACHING DIRECTIVES:{chr(10)}{directives_text}' if directives_text else ''}

{encourage}Provide a tutoring response:
- If correct: celebrate briefly and explain WHY it is correct.
- If incorrect: gently correct, explain the right answer clearly.
- Adapt your explanation to the student state above.
- Keep it under 3 short paragraphs.
"""
        explanation = call_ollama(prompt, rules['system_prompt'])
        if not explanation:
            if is_correct:
                explanation = f"Correct! The answer is '{expected}'. Well done!"
            else:
                explanation = f"Not quite. The correct answer is '{expected}'. {rules.get('style', 'Keep trying!')}."

        # ── 6. Engagement score ───────────────────────────────────────
        eng = {"score": 50, "trend": "stable", "label": "Loading..."}
        if session_manager.engagement_tracker:
            eng = session_manager.engagement_tracker.compute_engagement_score()

        # ── 7. Behavioral tag ─────────────────────────────────────────
        behavior_emotion = cognitive_score(user_answer, expected, emotion)

        return jsonify({
            "status":          "success",
            "is_correct":      is_correct,
            "explanation":     explanation,
            "strategy":        adap.get("explanation_style", rules['style']),
            # — AI Enhancement Layer fields —
            "learning_state":     ls.get("learning_state", "Optimal Learning"),
            "adaptation_action":  adap.get("adaptation_action", "continue"),
            "engagement_score":   eng.get("score", 50),
            "engagement_trend":   eng.get("trend", "stable"),
            "engagement_label":   eng.get("label", ""),
            "behavior_emotion":   behavior_emotion,
            "next_step":          "Click 'Next Lesson' to proceed.",
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/end_session", methods=["POST"])
def end_session():
    """End session and return full summary with engagement analytics."""
    summary = session_manager.get_session_summary()

    # Attach engagement history if available
    if session_manager.engagement_tracker:
        eng = session_manager.engagement_tracker.compute_engagement_score()
        summary["final_engagement"]      = eng.get("score", 50)
        summary["engagement_label"]       = eng.get("label", "")
        summary["emotion_timeline_count"] = len(
            session_manager.engagement_tracker.emotion_history
        )
    return jsonify({"status": "success", "summary": summary})


if __name__ == "__main__":
    app.run(debug=True, use_reloader=True, host='0.0.0.0', port=5000)
