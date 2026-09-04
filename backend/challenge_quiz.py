from claude import call_ollama
import json

class ChallengeQuizGenerator:
    """Generate challenge quizzes for advanced/engaged learners"""
    
    @staticmethod
    def generate_challenge_question(topic_data: dict, current_difficulty: int = 3) -> dict:
        """Generate a challenge question for an advanced learner"""
        
        title = topic_data.get('title', 'Unknown Topic')
        concepts = topic_data.get('key_concepts', [])
        difficulty = min(5, current_difficulty + 1)  # One level above current
        
        prompt = f"""
Generate a challenging but fair {title} question for an advanced learner.
Key concepts: {', '.join(concepts)}
Challenge level: {difficulty}/5

This should be significantly harder than standard questions - require:
- Multi-step reasoning
- Application of concepts
- Or proof-based thinking

Return as JSON:
{{
  "question": "Detailed question text",
  "answer": "Complete answer",
  "explanation": "Why this is correct and what misconceptions to avoid",
  "difficulty": {difficulty},
  "type": "challenge",
  "time_estimate": 120,
  "hint_1": "First hint if stuck",
  "hint_2": "Second hint if still stuck"
}}

Return ONLY valid JSON.
"""
        
        try:
            response_text = call_ollama(prompt)
            
            if response_text is None:
                raise Exception("Ollama did not return a response")
            
            try:
                challenge_q = json.loads(response_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    challenge_q = json.loads(json_match.group())
                else:
                    challenge_q = {
                        "question": "Solve this advanced problem yourself!",
                        "answer": "Check your work against the textbook",
                        "difficulty": difficulty,
                        "type": "challenge"
                    }
            
            return challenge_q
            
        except Exception as e:
            print(f"Error generating challenge question: {e}")
            return {
                "question": f"Advanced challenge for {title}",
                "answer": "Review mastery content",
                "difficulty": difficulty,
                "type": "challenge",
                "error": str(e)
            }
    
    @staticmethod
    def generate_quiz_set(topics: list, num_questions: int = 5) -> list:
        """Generate a challenge quiz set across multiple topics"""
        
        quiz_questions = []
        
        for i, topic in enumerate(topics[:num_questions]):
            challenge_q = ChallengeQuizGenerator.generate_challenge_question(topic)
            challenge_q['topic_id'] = topic.get('id', f'topic_{i}')
            challenge_q['order'] = i + 1
            quiz_questions.append(challenge_q)
        
        return quiz_questions
    
    @staticmethod
    def evaluate_challenge_answer(user_answer: str, correct_answer: str, 
                                  explanation: str = "") -> dict:
        """Evaluate a challenge answer with detailed feedback"""
        
        prompt = f"""
Evaluate this advanced answer:

QUESTION: [Generic challenge question]
USER ANSWER: {user_answer}
EXPECTED ANSWER: {correct_answer}

Is the user's answer correct or partially correct?
Provide detailed feedback for an advanced learner.

Return JSON:
{{
  "is_correct": true/false,
  "partial_credit": 0-100,
  "feedback": "Detailed feedback",
  "misconceptions": ["List of misconceptions if any"],
  "next_level_suggestion": "Suggestion for further learning"
}}

Return ONLY valid JSON.
"""
        
        try:
            response_text = call_ollama(prompt)
            
            if response_text is None:
                raise Exception("Ollama did not return a response")
            
            try:
                evaluation = json.loads(response_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    evaluation = json.loads(json_match.group())
                else:
                    evaluation = {
                        "is_correct": user_answer.lower() == correct_answer.lower(),
                        "partial_credit": 50,
                        "feedback": "Review your work against the expected answer"
                    }
            
            return evaluation
            
        except Exception as e:
            print(f"Error evaluating answer: {e}")
            return {
                "is_correct": False,
                "feedback": "Unable to evaluate at this time",
                "error": str(e)
            }
