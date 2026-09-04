# Multimodal Emotion-Aware Tutoring Agent

An AI-powered tutoring system that adapts content difficulty and explanation style in real-time based on learner emotional state detected from webcam facial expressions and typing patterns.

## Features

### 🎭 Real-time Emotion Detection
- **Trained Classifier**: SVM model trained on FER2013-like synthetic data using facial Action Units (AUs) extracted from MediaPipe landmarks
- **17 AU Features**: Comprehensive facial feature extraction for accurate emotion classification
- **4 Emotion States**: Engaged, Confused, Frustrated, Bored
- **<100ms Latency**: Optimized for real-time performance

### 🧠 Adaptive Content Generation
- **Claude AI Integration**: Uses Anthropic's Claude API for generating contextually appropriate explanations
- **Pedagogy Rules**: Emotion-specific prompting strategies (Socratic for bored, scaffolded for frustrated, etc.)
- **Topic Graph**: Directed acyclic graph with difficulty levels and prerequisites
- **Dynamic Adaptation**: Content difficulty and style adapt based on detected emotion

### 📊 Response Pattern Analysis
- **4 Cognitive Signals**:
  - Answer correctness
  - Edit distance from correct answer
  - Time-on-task metrics
  - Inter-keystroke intervals
- **Cognitive Load Scoring**: Weighted formula combining all signals
- **Behavior Fusion**: Combines facial emotion with cognitive analysis

### 📈 Analytics & Logging
- **Session Timeline**: Real-time emotion tracking with Chart.js visualization
- **Performance Metrics**: Correctness rates, response times, topic mastery
- **Educator Dashboard**: Comprehensive analytics for teaching insights
- **Tutor Quality Scoring**: Alignment between detected emotion and chosen adaptation

## Screenshots

![Upload Screen](assets/upload_screen.png)
*Upload your PDF course material*

![Learning Session](assets/learning_session.png)
*Real-time tutoring with emotion tracking and adaptive feedback*

![Analytics Dashboard](assets/analytics_dashboard.png)
*Comprehensive session summary and engagement metrics*

## Tech Stack

- **Backend**: Flask + Flask-CORS
- **Emotion Detection**: MediaPipe FaceMesh + Scikit-learn SVM + YOLOv8 (distraction)
- **AI Content Generation**: Anthropic Claude API (with Ollama fallback)
- **Frontend**: HTML5 + JavaScript + Chart.js
- **Data Processing**: NumPy, Joblib, pdfplumber

## Project Structure

```
emotion-tutor/
├── backend/
│   ├── app.py                   # Flask API server
│   ├── emotion.py               # Emotion detection using MediaPipe
│   ├── emotion_model.py         # Trained SVM classifier
│   ├── logic.py                 # Topic graph and question management
│   ├── claude.py                # Claude API / Ollama integration
│   ├── cognitive.py             # Response pattern analysis
│   ├── fusion_advanced.py       # Advanced emotion-behavior fusion
│   ├── session_manager.py       # State and metrics management
│   ├── pdf_processor.py         # PDF to course outline conversion
│   ├── learning_state.py        # Learning state classification
│   ├── engagement_tracker.py    # Session engagement tracking
│   ├── distraction_detector.py  # YOLOv8 distraction detection
│   ├── emotion_engine.py        # Emotion signal processing
│   ├── adaptation_engine.py     # Content adaptation rules
│   └── challenge_quiz.py        # Quiz generator
├── frontend/
│   ├── index.html               # Main tutoring interface
│   ├── script.js                # Frontend logic and webcam handling
│   └── style.css                # Modern UI styling
├── yolov8n.pt                   # YOLOv8 weights for distraction detection
├── emotion_model.pkl            # Pre-trained SVM emotion model
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Claude API Key** (Optional - falls back to local Ollama generation or deterministic text):
   ```bash
   # Windows (Command Prompt)
   set ANTHROPIC_API_KEY=your-api-key-here
   
   # Windows (PowerShell)
   $env:ANTHROPIC_API_KEY="your-api-key-here"
   
   # Mac/Linux
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```

3. **Run the Application**:
   ```bash
   python backend/app.py
   ```

4. **Open Browser**:
   Navigate to `http://127.0.0.1:5000`

## Demo Flow

1. **Upload PDF**: Upload study material which the AI will break down into a structured course.
2. **Camera Permission**: Grant webcam access for emotion and distraction detection.
3. **Real-time Monitoring**: System continuously analyzes facial expressions and attention.
4. **Adaptive Questions**: Content difficulty and style adjust based on emotional state.
5. **Response Analysis**: AI generates contextual feedback based on your answer and current emotion.
6. **Analytics Dashboard**: Comprehensive session performance metrics when the session ends.

## Push to GitHub Instructions

To push this project to GitHub, open your terminal/command prompt in the `emotion-tutor` directory and run the following commands:

```bash
# 1. Initialize a new git repository
git init

# 2. Add all files to staging
git add .

# 3. Commit your files
git commit -m "Initial commit: Multimodal Emotion-Aware Tutoring Agent"

# 4. Create a new repository on GitHub (via web interface), then link it:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git

# 5. Push to the main branch
git branch -M main
git push -u origin main
```
*Note: Make sure to create an `assets` folder and place the screenshots (`upload_screen.png`, `learning_session.png`, `analytics_dashboard.png`) in it before committing.*

## Evaluation Metrics

- **Emotion Classification Accuracy**: SVM model performance on FER2013-like benchmark patterns
- **Content Adaptation Appropriateness**: Alignment of emotion with chosen teaching strategy
- **Learner Engagement Improvement**: Time-on-task increase and distraction reduction
- **Inference Latency**: Target <100ms per frame for real-time performance

## Key Differentiators

1. **Closed-Loop System**: Complete emotion → decision → content → logging cycle
2. **Multi-Modal Fusion**: Combines facial analysis, behavioral patterns, and distraction detection
3. **AI-Generated Content**: Claude API / Ollama enables sophisticated pedagogical adaptation
4. **Real-Time Performance**: Optimized for live tutoring scenarios
5. **Measurable Outcomes**: Comprehensive analytics for validation

## Future Enhancements

- Integration with actual FER2013 dataset for improved accuracy
- Voice emotion analysis using Web Audio API
- Multi-language support for global accessibility
- Integration with learning management systems
- Advanced topic recommendation algorithms