import os
import json
import re
import requests
import anthropic

# Ollama API endpoint (runs locally on port 11434)
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "orca-mini"  # Ultra-lightweight model (requires ~1.3 GB)

def call_ollama(prompt: str, system_prompt: str = "") -> str:
    """Call Anthropic API if key is set, else fallback to Ollama local API"""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            client = anthropic.Anthropic(api_key=anthropic_key)
            messages = [{"role": "user", "content": prompt}]
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                system=system_prompt,
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            print(f"[ANTHROPIC] Error: {e}")
            return None

    try:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
            },
            timeout=300  # 5 minute timeout, local CPU generation of large JSON can be extremely slow
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
        else:
            print(f"[OLLAMA] Error {response.status_code}: {response.text[:200]}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"[OLLAMA] Timeout - response took too long")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[OLLAMA] Connection failed - is Ollama running on {OLLAMA_API_URL}?")
        return None
    except Exception as e:
        print(f"[OLLAMA] Error: {e}")
        return None

# ---------------------------------------------------------------------------
# Pedagogy rules: how each emotion changes the teaching style
# ---------------------------------------------------------------------------
PEDAGOGY_RULES = {
    "Frustrated": {
        "system_prompt": (
            "You are a patient, encouraging tutor. The student is frustrated. "
            "Provide step-by-step explanations with lots of encouragement. "
            "Break complex problems into very small, simple steps. "
            "Use simple language and positive reinforcement. Build confidence."
        ),
        "style": "step-by-step, simplified, encouraging"
    },
    "Confused": {
        "system_prompt": (
            "You are a clear, methodical tutor. The student is confused. "
            "Use structured explanations with visual analogies and concrete examples. "
            "Break abstract concepts into tangible, relatable scenarios. "
            "Be patient and thorough."
        ),
        "style": "structured, concrete, methodical"
    },
    "Bored": {
        "system_prompt": (
            "You are an engaging, challenging tutor. The student is bored. "
            "Make explanations interesting with real-world applications and "
            "thought-provoking questions. Present problems as puzzles or challenges. "
            "Encourage deeper thinking and exploration."
        ),
        "style": "engaging, challenging, exploratory"
    },
    "Engaged": {
        "system_prompt": (
            "You are an enthusiastic tutor. The student is engaged and learning well. "
            "Build on momentum with interesting extensions and connections to other topics. "
            "Encourage the student to explain their thinking and explore related concepts."
        ),
        "style": "enthusiastic, extending, connecting"
    }
}

# ---------------------------------------------------------------------------
# NEW: HIERARCHICAL COURSE GENERATOR
# ---------------------------------------------------------------------------

def generate_course_outline(content: str, subject: str = "general") -> dict:
    """Pass 1: Identify Topics and Lesson titles from raw text"""
    prompt = f"""
Analyze this {subject} study material. Break it into 3-5 major Topics.
For each Topic, identify 2-3 specific Lessons.

MATERIAL:
{content[:5000]}

Return exactly this JSON structure:
{{
  "main_topic": "Course Title",
  "topics": [
    {{
      "name": "Topic Name",
      "difficulty": 1,
      "lesson_titles": ["Lesson 1 Title", "Lesson 2 Title"]
    }}
  ]
}}
Return ONLY valid JSON.
"""
    try:
        response = call_ollama(prompt, "You are a curriculum architect.")
        if not response: return None
        
        # Parse JSON
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        print(f"Course outline error: {e}")
        return None

def generate_lesson_content(lesson_title: str, topic_context: str, emotion: str = "Engaged") -> dict:
    """Pass 2: Generate detailed explanation and questions for ONE lesson"""
    rules = PEDAGOGY_RULES.get(emotion, PEDAGOGY_RULES["Engaged"])
    
    prompt = f"""
Create a comprehensive lesson for: '{lesson_title}'
Context: {topic_context}
Style: {rules['style']}

Requirements:
1. 'explanation': A clear tutoring explanation (2-3 paragraphs). Use beginner-friendly tone.
2. 'breakdown': A step-by-step breakdown of the concept.
3. 'questions': Exactly 2 short-answer questions based ONLY on this content.

Return JSON:
{{
  "explanation": "text...",
  "breakdown": ["step 1", "step 2"],
  "questions": [
    {{ "q": "Question text", "answer": "Answer keyword" }}
  ]
}}
"""
    try:
        response = call_ollama(prompt, rules['system_prompt'])
        if not response: return None
        
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        print(f"Lesson content error: {e}")
        return None


# ---------------------------------------------------------------------------
# Core dynamic lesson generator (Adapts or Generates content)
# ---------------------------------------------------------------------------

def generate_dynamic_lesson(topic_data, emotion, question_index, pre_generated_lesson=None, pre_generated_question=None, adaptation_params=None):
    """
    Generate or adapt a lesson for a specific topic and emotion.
    Returns dict: {teaching, question, answer, type, hint, difficulty}
    """
    
    # CASE 1: ADAPT PRE-GENERATED CONTENT (High Performance)
    if pre_generated_lesson and pre_generated_question:
        style_rules = PEDAGOGY_RULES.get(emotion, PEDAGOGY_RULES["Engaged"])
        
        directives = ""
        if adaptation_params and adaptation_params.get("teaching_directives"):
            directives = "\n".join("- " + d for d in adaptation_params["teaching_directives"])
            
        prompt = f"""
Tone: {adaptation_params.get('explanation_style', style_rules['style']) if adaptation_params else style_rules['style']}
Student Mood: {emotion}
{f'DIRECTIVES:{chr(10)}{directives}' if directives else ''}

ADAPT THIS CONTENT:
LESSON: {pre_generated_lesson.get('explanation', '')}
QUESTION: {pre_generated_question.get('q', '')}
EXPECTED ANSWER: {pre_generated_question.get('answer', '')}

Return JSON with these fields:
{{
  "teaching": "Adapted tutoring explanation (beginner friendly, 3 paragraphs)",
  "question": "Adapted question text",
  "expected_answer": "The answer",
  "explanation": "Brief reasoning for why this answer is correct"
}}
"""
        try:
            response = call_ollama(prompt, style_rules['system_prompt'])
            if response:
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    res = json.loads(match.group())
                    return {
                        "teaching": res.get("teaching", pre_generated_lesson.get('explanation')),
                        "question": res.get("question", pre_generated_question.get('q')),
                        "answer": res.get("expected_answer", pre_generated_question.get('answer')),
                        "explanation": res.get("explanation", "Good luck!"),
                        "strategy": style_rules['style']
                    }
        except Exception as e:
            print(f"Adaptation error, using raw content: {e}")
            return {
                "teaching": pre_generated_lesson.get('explanation'),
                "question": pre_generated_question.get('q'),
                "answer": pre_generated_question.get('answer'),
                "explanation": "Based on the content.",
                "strategy": "Direct fallback"
            }

    # CASE 2: DYNAMIC GENERATION (If no pre-generated content exists)
    rules = PEDAGOGY_RULES.get(emotion, PEDAGOGY_RULES["Engaged"])
    title = topic_data.get('title', 'Study Topic')
    concepts = topic_data.get('key_concepts', [])
    difficulty = topic_data.get('difficulty', 1)

    prompt = f"""
Topic: {title}
Concepts: {', '.join(concepts)}
Emotion: {emotion}

Generate a tutoring paragraph and one question.
Return JSON:
{{
  "teaching": "Tutoring text...",
  "question": "Question text",
  "answer": "answer keyword",
  "type": "short_answer",
  "hint": "hint text"
}}
"""
    try:
        response_text = call_ollama(prompt, rules['system_prompt'])
        if response_text:
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                lesson = json.loads(match.group())
                return lesson
    except Exception as e:
        print(f"Dynamic gen error: {e}")

    # FINAL FALLBACK (Offline)
    fallback = _fallback_lesson(topic_data, emotion, question_index, concepts, difficulty)
    if fallback:
        return fallback
        
    # ABSOLUTE GUARANTEED RETURN IF EVERYTHING FAILS
    return {
        "teaching": pre_generated_lesson.get('explanation', "We are having trouble generating the lesson right now.") if pre_generated_lesson else "Please try again later.",
        "question": pre_generated_question.get('q', "Check your internet connection.") if pre_generated_question else "What did you learn?",
        "answer": pre_generated_question.get('answer', "connection") if pre_generated_question else "learned",
        "explanation": "System error occurred.",
        "strategy": "Fallback"
    }


def _fallback_lesson(topic_data, emotion, question_index, key_concepts, difficulty):
    """Generate a deterministic offline lesson."""
    title = topic_data.get('title', 'This Topic')
    explanation = topic_data.get('explanation', f'Study {title} carefully.')
    concept = key_concepts[question_index % len(key_concepts)] if key_concepts else title

    if emotion == "Frustrated":
        teaching = (f"Let's slow down and tackle {concept} step by step. {explanation}")
        q = f"In your own words, what is {concept}?"
    elif emotion == "Confused":
        teaching = (f"Let me explain {concept} more clearly. {explanation}")
        q = f"Can you give one example of {concept}?"
    elif emotion == "Bored":
        teaching = (f"Challenge about {concept}! {explanation}")
        q = f"How would you apply {concept} in a real-world scenario?"
    else:
        teaching = (f"Let's explore {concept}. {explanation}")
        q = f"What is the key principle behind {concept}?"

    return {
        "teaching": teaching,
        "question": q,
        "answer": concept,
        "type": "short_answer",
        "hint": f"Think about {concept}",
        "difficulty": difficulty
    }

# ---------------------------------------------------------------------------
# Legacy helpers (kept for backward compat)
# ---------------------------------------------------------------------------

def generate_adaptive_explanation(emotion, question, topic_data, learner_history=None):
    """Generate adaptive explanation using Ollama"""
    rules = PEDAGOGY_RULES.get(emotion, PEDAGOGY_RULES["Engaged"])
    user_prompt = f"Explain this: {topic_data.get('title')} - {question}"
    try:
        response = call_ollama(user_prompt, rules['system_prompt'])
        return response if response else "Review the content carefully."
    except:
        return "Review the content carefully."