import json
import random
import os
from claude import generate_adaptive_explanation

# Get the directory of this file and navigate to data folder
current_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(current_dir, '..', 'data', 'questions.json')

with open(data_path, 'r') as f:
    data = json.load(f)

current_topic = "add_basic"
current_question_index = 0
current_answer = "5"
learner_history = []

def get_topic_by_emotion(emotion):
    topic_map = {
        "Frustrated": "add_basic",
        "Confused": "sub_basic",
        "Bored": "algebra_basic",
        "Engaged": "mult_tables"
    }
    return topic_map.get(emotion, "add_basic")

def get_next_question(emotion):
    global current_topic, current_question_index, current_answer, learner_history

    # Adapt topic based on emotion
    new_topic = get_topic_by_emotion(emotion)
    if new_topic != current_topic:
        current_topic = new_topic
        current_question_index = 0

    # Get questions for current topic
    questions = data["questions"].get(current_topic, [])
    if not questions:
        return "Adaptive explanation", "No questions available for this topic"

    # Cycle through questions
    if current_question_index >= len(questions):
        current_question_index = 0

    question_data = questions[current_question_index]
    current_answer = question_data["answer"]
    question_text = question_data["question"]

    # Get topic metadata
    topic_info = next((t for t in data["topics"] if t["id"] == current_topic), {})

    # Generate adaptive explanation using Claude
    explanation = generate_adaptive_explanation(emotion, question_text, topic_info, learner_history[-5:])

    current_question_index += 1

    return "Adaptive explanation", explanation

def get_current_answer():
    return current_answer

def update_learner_history(emotion, correct, time_taken):
    """Update learner history for adaptive tutoring"""
    global learner_history

    history_entry = {
        "emotion": emotion,
        "correct": correct,
        "time_taken": time_taken,
        "topic": current_topic
    }

    learner_history.append(history_entry)

    # Keep only recent history
    if len(learner_history) > 20:
        learner_history.pop(0)