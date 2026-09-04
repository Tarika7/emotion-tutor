import pdfplumber
import json
import re
from claude import call_ollama

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract clean text from PDF file, removing headers and footers"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Analyze page geometry to identify probable header/footer zones
            # Use middle page for analysis as first page often has unique layout
            analysis_page = pdf.pages[len(pdf.pages)//2] if len(pdf.pages) > 1 else pdf.pages[0]
            height = analysis_page.height
            
            # Margins: Skip top 10% and bottom 10% for headers/footers
            top_margin = height * 0.1
            bottom_margin = height * 0.9
            
            for page in pdf.pages:
                # Crop to body area to avoid page numbers/headers/footers
                body = page.crop((0, top_margin, page.width, bottom_margin))
                page_text = body.extract_text()
                if page_text:
                    # Remove multiple empty lines and page numbers if they slipped through
                    clean_page = re.sub(r'\n\s*\n+', '\n', page_text)
                    text += clean_page + "\n"
                    
    except Exception as e:
        print(f"⚠️ PDF extraction error: {str(e)}")
        # Simple fallback if cropping fails
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
        except:
            raise Exception(f"PDF extraction total failure: {str(e)}")
    
    return text.strip()

def generate_fallback_topics(content: str, subject: str = "mathematics") -> dict:
    """Generate synthetic topics without Claude API - works offline"""
    # Extract potential topic keywords from content
    lines = content.split('\n')
    
    # Simple keyword extraction
    potential_topics = []
    for line in lines[:50]:  # Look at first 50 lines
        if len(line.strip()) > 20 and any(keyword in line.lower() for keyword in ['chapter', 'section', 'topic', 'introduction', 'lesson', 'unit']):
            potential_topics.append(line.strip()[:60])
    
    # Create standard math topics as fallback
    default_topics = [
        {
            "id": "topic_1",
            "name": "Foundations & Basics",
            "difficulty": 1,
            "prerequisites": [],
            "key_concepts": ["definitions", "fundamentals", "core concepts"],
            "lessons": []
        },
        {
            "id": "topic_2",
            "name": "Core Principles",
            "difficulty": 2,
            "prerequisites": ["topic_1"],
            "key_concepts": ["rules", "properties", "theorems"],
            "lessons": []
        },
        {
            "id": "topic_3",
            "name": "Problem Solving",
            "difficulty": 3,
            "prerequisites": ["topic_1", "topic_2"],
            "key_concepts": ["application", "techniques", "strategies"],
            "lessons": []
        },
        {
            "id": "topic_4",
            "name": "Advanced Concepts",
            "difficulty": 4,
            "prerequisites": ["topic_2", "topic_3"],
            "key_concepts": ["extensions", "advanced thinking", "deeper understanding"],
            "lessons": []
        },
        {
            "id": "topic_5",
            "name": "Real-World Applications",
            "difficulty": 3,
            "prerequisites": ["topic_2"],
            "key_concepts": ["practice", "real-world", "applications"],
            "lessons": []
        }
    ]
    
    course_data = {
        "main_topic": "Study Material",
        "description": "Adaptive learning content from your uploaded document",
        "topics": default_topics,
        "learning_objectives": [
            "Master foundational concepts",
            "Apply knowledge to solve problems",
            "Understand advanced applications"
        ],
        "estimated_duration_minutes": 60
    }
    
    return {
        "course_data": course_data,
        "full_text": content[:15000] if content else ""
    }

def generate_topics_from_content(content: str, subject: str = "mathematics") -> dict:
    """Use Claude to generate topic graph from extracted content, with fallback"""
    
    prompt = f"""
You are an expert educator. Analyze the following {subject} study material and create a structured learning path.

MATERIAL:
{content[:4000]}

Generate a JSON response with this exact structure:
{{
  "main_topic": "extracted main topic name",
  "description": "brief description of the material",
  "topics": [
    {{
      "id": "topic_id",
      "title": "Topic Title",
      "difficulty": 1,
      "prerequisites": [],
      "key_concepts": ["concept1", "concept2"],
      "explanation": "Detailed explanation of this topic"
    }}
  ],
  "learning_objectives": ["objective1", "objective2"],
  "estimated_duration_minutes": 45
}}

Create 4-5 topics in logical progression. Start with basics and move to advanced.
Return ONLY valid JSON, no other text.
"""

    try:
        print("Attempting to generate topics with Ollama...")
        response_text = call_ollama(prompt)
        
        if response_text is None:
            raise Exception("Ollama did not return a response")
        
        # Parse JSON response
        try:
            topic_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON if response has extra text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                topic_data = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse Ollama response")
        
        print(f"Topics generated successfully from Ollama")
        return topic_data
        
    except Exception as e:
        print(f"Ollama unavailable or error: {str(e)}")
        print(f"Using fallback topic generation (system will still work)...")
        return generate_fallback_topics(content, subject)

def generate_fallback_questions(topic_id: str, title: str, concepts: list, difficulty: int) -> list:
    """Generate synthetic questions without Claude API"""
    questions = []
    
    # Create question templates based on difficulty
    if difficulty <= 2:
        questions.append({
            "question": f"What is {concepts[0] if concepts else 'this concept'}?",
            "answer": f"A fundamental concept in {title}",
            "type": "short_answer",
            "hint": "Review the definition in your material"
        })
        questions.append({
            "question": f"Which of these is an example of {concepts[0] if concepts else 'this topic'}?",
            "answer": "Check the examples in your material",
            "type": "multiple_choice",
            "hint": "Look for worked examples"
        })
    elif difficulty <= 3:
        questions.append({
            "question": f"How would you apply {title} to solve a problem?",
            "answer": "Use the principles: " + ", ".join(concepts[:2]) if len(concepts) >= 2 else concepts[0],
            "type": "short_answer",
            "hint": "Think about the steps and strategies"
        })
    else:
        questions.append({
            "question": f"Why is {concepts[0] if concepts else 'this concept'} important in {title}?",
            "answer": "It provides the foundation for more advanced topics",
            "type": "short_answer",
            "hint": "Consider deeper connections and applications"
        })
    
    # Add a second question
    questions.append({
        "question": f"Practice: Can you explain {concepts[1] if len(concepts) > 1 else concepts[0]}?",
        "answer": "Yes, and here's how: [your explanation]",
        "type": "short_answer",
        "hint": "Use your own words to explain the concept"
    })
    
    # Add a third question
    questions.append({
        "question": f"What would happen if you changed a key aspect of {title}?",
        "answer": "The outcome would be different, showing the importance of this principle",
        "type": "short_answer",
        "hint": "Think about dependencies and relationships"
    })
    
    return questions

def generate_questions_for_topics(topics: list, subject: str = "mathematics") -> dict:
    """Generate questions for each topic, with fallback"""
    
    questions_dict = {}
    use_fallback = False
    
    for topic in topics:
        topic_id = topic.get("id", "unknown")
        title = topic.get("title", "")
        concepts = topic.get("key_concepts", [])
        difficulty = topic.get("difficulty", 1)
        
        prompt = f"""
Generate 3 questions for a {subject} topic about '{title}'.
Key concepts: {', '.join(concepts)}
Difficulty level: {difficulty}/5

Return as JSON array with this structure:
[
  {{
    "question": "The question text",
    "answer": "The correct answer",
    "type": "multiple_choice OR short_answer",
    "hint": "A helpful hint if stuck"
  }}
]

Return ONLY valid JSON array, no other text.
"""
        
        try:
            if not use_fallback:
                print(f"Generating questions for {topic_id}...")
                response_text = call_ollama(prompt)
                
                if response_text:
                    try:
                        questions = json.loads(response_text)
                    except json.JSONDecodeError:
                        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                        if json_match:
                            questions = json.loads(json_match.group())
                        else:
                            questions = []
                else:
                    questions = []
                
                if questions:
                    questions_dict[topic_id] = questions
                else:
                    print(f"No valid questions from Ollama, using fallback for {topic_id}...")
                    use_fallback = True
                    questions_dict[topic_id] = generate_fallback_questions(topic_id, title, concepts, difficulty)
            else:
                # Use fallback
                questions_dict[topic_id] = generate_fallback_questions(topic_id, title, concepts, difficulty)
            
        except Exception as e:
            print(f"Ollama failed for questions: {e}")
            print(f"Using fallback questions for {topic_id}...")
            use_fallback = True
            questions_dict[topic_id] = generate_fallback_questions(topic_id, title, concepts, difficulty)
    
    return questions_dict


def process_pdf_to_full_course(pdf_path: str, subject: str = "general") -> dict:
    """Complete pipeline: PDF → Clean Text → Course Outline → Detailed Lessons"""
    
    # Step 1: Extract text
    print("Phase 1: Extracting text from PDF...")
    content = extract_text_from_pdf(pdf_path)
    
    if not content or len(content) < 100:
        return generate_fallback_topics(content or "General study material", subject)
    
    # Step 2: Generate Structure (Topics & Lesson Titles)
    print("Phase 2: Identifying topics and building course outline...")
    outline = generate_course_outline(content, subject)
    
    if not outline or 'topics' not in outline:
        print("⚠️ Failed to generate AI outline, using fallback")
        return generate_fallback_topics(content, subject)
    
    # Step 3: Populate Topic Titles (LAZY LOAD - Content generated on-the-fly)
    print(f"🗺️ Phase 3: Finalizing structure for {len(outline['topics'])} topics...")
    course = {
        "main_topic": outline.get("main_topic", "Generated Course"),
        "topics": []
    }
    
    for i, t_info in enumerate(outline['topics']):
        topic_name = t_info.get("name", f"Topic {i+1}")
        
        # We only save the structure here. 
        # Detailed content in 'lessons' will be empty and filled during the session.
        topic_node = {
            "id": f"topic_{i+1}",
            "name": topic_name,
            "difficulty": t_info.get("difficulty", 1),
            "lessons": [
                {"name": l_title, "explanation": "", "breakdown": [], "questions": []}
                for l_title in t_info.get("lesson_titles", [])[:3]
            ]
        }
        course["topics"].append(topic_node)
            
    # Final safety check
    if not course["topics"]:
        return generate_fallback_topics(content, subject)
        
    print("Fast Course outline complete!")
    return {
        "course_data": course,
        "full_text": content[:15000] # Pass context for later (limited to stay within memory)
    }

def process_pdf_to_topic_graph(pdf_path: str, subject: str = "mathematics") -> dict:
    """Legacy wrapper for backward compatibility - redirects to full course"""
    return process_pdf_to_full_course(pdf_path, subject)
