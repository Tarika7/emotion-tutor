// Global state
let currentState = {
    uploaded_topic_data: null,
    uploaded_questions: null,
    session_duration: 15,
    session_active: false,
    current_emotion: 'Engaged',
    interaction_count: 0,
    correct_count: 0,
    distraction_count: 0,
    current_topic_id: null,
    question_start_time: null,
    chart: null,
    emotion_history: [],
    session_id: null
};

// ============================================================================
// PAGE MANAGEMENT
// ============================================================================

function showPage(pageName) {
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.getElementById(pageName).classList.add('active');
}

function goToUpload() {
    showPage('uploadPage');
    resetUploadUI();
}

function goToSessionConfig() {
    if (!currentState.uploaded_topic_data || !currentState.uploaded_topic_data.topics) {
        alert("Wait! Course data hasn't loaded yet. Please try uploading your PDF again.");
        return;
    }
    showPage('sessionPage');
    document.getElementById('topicCount').textContent = currentState.uploaded_topic_data.topics.length;
    initCameraPreview();
}

function goToLearning() {
    showPage('learningPage');
    initChart();
    initWebcam();
    startLearningLoop();
}

function goToSummary() {
    showPage('summaryPage');
    displaySessionSummary();
}

// ============================================================================
// FILE UPLOAD & PDF PROCESSING
// ============================================================================

function resetUploadUI() {
    document.getElementById('uploadStatus').classList.add('hidden');
    document.getElementById('uploadError').classList.add('hidden');
    document.getElementById('uploadSuccess').classList.add('hidden');
    document.getElementById('dropZone').style.display = 'block';
}

const dropZone = document.getElementById('dropZone');

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.background = '#f0f0f0';
});

dropZone.addEventListener('dragleave', () => {
    dropZone.style.background = '';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.background = '';
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        uploadPDF(files[0]);
    }
});

document.getElementById('pdfInput').addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        uploadPDF(e.target.files[0]);
    }
});

async function uploadPDF(file) {
    // Check file extension (more reliable than file.type)
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showError('Please upload a PDF file');
        return;
    }

    console.log('📤 Uploading file:', file.name, file.size, 'bytes');
    showStateLoading('uploadStatus', 'Uploading and processing PDF...');

    const formData = new FormData();
    formData.append('file', file);

    try {
        console.log('Sending fetch request to /upload_pdf');
        const response = await fetch('/upload_pdf', {
            method: 'POST',
            body: formData
        });

        console.log('Response received:', response.status, response.statusText);

        if (!response.ok) {
            let errorMsg = 'Upload failed';
            try {
                const error = await response.json();
                errorMsg = error.error || errorMsg;
            } catch (e) {
                errorMsg = `Server error: ${response.status}`;
            }
            throw new Error(errorMsg);
        }

        const data = await response.json();
        console.log('✅ PDF processed successfully. Course:', data.main_topic);

        currentState.uploaded_topic_data = data.course_data;
        currentState.uploaded_questions = null; // No longer needed as they are nested

        const topics = data.course_data.topics || [];
        const topicsCount = data.topic_count || topics.length;
        
        const topicsHtml = topics.map(t => `
            <div class="topic-item">
                <strong>📌 ${t.name || t.title}</strong>
                <ul style="margin-top:5px; margin-bottom:10px; color:#94a3b8; font-size:0.9rem;">
                    ${(t.lessons || []).map(l => `<li>${l.name || l.title}</li>`).join('')}
                </ul>
            </div>
        `).join('');

        showStateSuccess('uploadSuccess', `
            <h3>✅ Course Structure Generated!</h3>
            <div class="topic-details">
                <p><strong>Course:</strong> ${data.main_topic}</p>
                <p><strong>Topics Discovered:</strong> ${topicsCount}</p>
                <div class="curriculum-preview" style="background: rgba(15, 23, 42, 0.5); padding: 15px; border-radius: 8px; margin-top: 15px; max-height: 300px; overflow-y: auto; text-align: left;">
                    <h4>📚 Curriculum Overview:</h4>
                    ${topicsHtml}
                </div>
            </div>
        `);

        document.getElementById('dropZone').style.display = 'none';

    } catch (error) {
        console.error('❌ Upload error:', error);
        showError(error.message || 'Failed to process PDF');
    }
}

function showStateLoading(elementId, message) {
    document.getElementById('uploadStatus').classList.remove('hidden');
    document.getElementById('uploadError').classList.add('hidden');
    document.getElementById('uploadSuccess').classList.add('hidden');
    document.getElementById('statusText').textContent = message;
}

function showStateSuccess(elementId, html) {
    document.getElementById('uploadStatus').classList.add('hidden');
    document.getElementById('uploadError').classList.add('hidden');
    document.getElementById(elementId).classList.remove('hidden');
    document.getElementById('topicDetails').innerHTML = html;
}

function showError(message) {
    document.getElementById('uploadStatus').classList.add('hidden');
    document.getElementById('uploadSuccess').classList.add('hidden');
    document.getElementById('uploadError').classList.remove('hidden');
    document.getElementById('errorText').textContent = '❌ ' + message;
}

// ============================================================================
// SESSION CONFIGURATION
// ============================================================================

function updateDuration(minutes) {
    currentState.session_duration = minutes;
    document.getElementById('durationDisplay').textContent = minutes + ' min';
}

let cameraStream;

async function initCameraPreview() {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
        const video = document.getElementById('cameraPreview');
        video.srcObject = cameraStream;
        document.getElementById('cameraStatus').textContent = '✅ Camera ready';
    } catch (error) {
        document.getElementById('cameraStatus').textContent = '❌ Camera access denied';
    }
}

async function startLearning() {
    if (!currentState.uploaded_topic_data || !currentState.uploaded_topic_data.topics) {
        alert('Please upload a PDF first and wait for it to process.');
        return;
    }

    // Create session
    try {
        const response = await fetch('/create_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic_data: currentState.uploaded_topic_data,
                questions: currentState.uploaded_questions,
                time_minutes: currentState.session_duration
            })
        });

        if (!response.ok) throw new Error('Failed to create session');

        const data = await response.json();
        currentState.session_id = data.session_id;
        currentState.session_active = true;

        // Get first topic name/id for start
        const topics = currentState.uploaded_topic_data.topics;
        if (topics.length > 0) {
            // Use the topic 'id' field (e.g. 'topic_1'), NOT the display name
            currentState.current_topic_id = topics[0].id || topics[0].name;
        }

        goToLearning();
        fetchNextLesson();

    } catch (error) {
        alert('Failed to start session: ' + error.message);
    }
}

// ============================================================================
// LEARNING SESSION
// ============================================================================

let webcamStream;
let learningInterval;
let timerInterval;

async function initWebcam() {
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });
        document.getElementById('webcam').srcObject = webcamStream;
        document.getElementById('webcamStatus').textContent = 'Camera active ✅';
    } catch (error) {
        document.getElementById('webcamStatus').textContent = 'Camera failed ❌';
    }
}

function initChart() {
    const ctx = document.getElementById('emotionChart').getContext('2d');
    currentState.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Emotion Level',
                data: [],
                fill: true,
                borderColor: 'rgba(102, 126, 234, 1)',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 4,
                    ticks: {
                        callback: (value) => {
                            const emotions = ['', 'Bored', 'Frustrated', 'Confused', 'Engaged'];
                            return emotions[value] || '';
                        }
                    }
                }
            }
        }
    });
}

function emotionToNumber(emotion) {
    const map = { 'Bored': 1, 'Frustrated': 2, 'Confused': 3, 'Engaged': 4 };
    return map[emotion] || 2;
}

function startLearningLoop() {
    startSessionTimer();

    learningInterval = setInterval(async () => {
        if (!currentState.session_active) {
            clearInterval(learningInterval);
            return;
        }

        try {
            // Grab frame from the browser webcam feed to send to backend (solves Windows lock issue)
            const videoElement = document.getElementById('webcam');
            let frameData = null;
            if (videoElement && videoElement.readyState === videoElement.HAVE_ENOUGH_DATA) {
                const canvas = document.createElement('canvas');
                canvas.width = videoElement.videoWidth;
                canvas.height = videoElement.videoHeight;
                canvas.getContext('2d').drawImage(videoElement, 0, 0, canvas.width, canvas.height);
                frameData = canvas.toDataURL('image/jpeg', 0.8);
            }

            const response = await fetch('/get_state_advanced', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic_id: currentState.current_topic_id,
                    frame: frameData
                })
            });

            const data = await response.json();

            // Handle distraction block
            if (data.blocked) {
                showDistractionBlock(data);
                return;
            }

            currentState.current_emotion = data.emotion;
            
            // Update UI
            updateEmotionDisplay(data.emotion);
            document.getElementById('strategyText').textContent = 
                (data.teaching_strategy && data.teaching_strategy.name ? data.teaching_strategy.name : data.strategy || 'Normal') + ': ' + 
                (data.teaching_strategy && data.teaching_strategy.description ? data.teaching_strategy.description : data.explanation || 'Continuing');
            document.getElementById('latencyValue').textContent = data.latency_ms + 'ms';
            
            // Update AI Enhancement Engine DOM elements
            if (data.learning_state) {
                const tag = document.getElementById('learningStateTag');
                tag.innerHTML = `${data.state_icon || '🤷'} ${data.learning_state}`;
                tag.style.color = data.state_color || '#94a3b8';
            }
            if (data.engagement_score !== undefined) {
                document.getElementById('engagementScoreDisplay').textContent = data.engagement_score;
                document.getElementById('engagementTrendDisplay').textContent = data.engagement_trend;
            }

            // Removed UI Question manipulation here to stop overlapping state loop resets

            // Update chart
            currentState.emotion_history.push(data.emotion);
            if (currentState.chart) {
                currentState.chart.data.labels = currentState.emotion_history.map((_, i) => i);
                currentState.chart.data.datasets[0].data = currentState.emotion_history.map(emotionToNumber);
                currentState.chart.update();
            }

            // Handle distraction warning
            if (data.has_distractions) {
                currentState.distraction_count++;
                updateDistractionCounter();
            }

        } catch (error) {
            console.error('Error:', error);
        }

    }, 3000); // Update every 3 seconds
}

function showDistractionBlock(data) {
    document.getElementById('blockingOverlay').style.display = 'flex';
    document.getElementById('blockingMessage').textContent = data.message;

    const timeRemaining = Math.ceil(data.time_remaining || 5);
    let countdown = timeRemaining;

    const countdownInterval = setInterval(() => {
        document.getElementById('blockingTimer').textContent = countdown;
        countdown--;

        if (countdown < 0) {
            clearInterval(countdownInterval);
            document.getElementById('blockingOverlay').style.display = 'none';
        }
    }, 1000);
}

function updateEmotionDisplay(emotion) {
    const emotionMap = {
        'Engaged': '😊',
        'Confused': '🤔',
        'Frustrated': '😞',
        'Bored': '😴',
        'Distracted': '📱'
    };

    document.getElementById('emotionCircle').textContent = emotionMap[emotion] || '😐';
    document.getElementById('emotionName').textContent = emotion;
}

function updateDistractionCounter() {
    document.getElementById('distractionCount').textContent = currentState.distraction_count;
}

function handleKeyDown(event) {
    if (event.key === 'Enter') {
        submitAnswer();
    }
}

async function submitAnswer() {
    const answerInput = document.getElementById('answer');
    const answer = answerInput.value.trim();
    if (!answer) return;

    const time_taken = (Date.now() - currentState.question_start_time) / 1000;
    const feedback = document.getElementById('feedback');
    const nextLessonBtn = document.getElementById('nextLessonBtn') || document.createElement('button');
    
    // Setup Next Lesson Button if it doesn't exist
    if (!document.getElementById('nextLessonBtn')) {
        nextLessonBtn.id = 'nextLessonBtn';
        nextLessonBtn.className = 'btn-primary';
        nextLessonBtn.style.marginTop = '15px';
        nextLessonBtn.textContent = 'Next Lesson ➡️';
        nextLessonBtn.onclick = () => {
            document.getElementById('questionBox').style.display = 'none';
            fetchNextLesson();
        };
        feedback.parentNode.appendChild(nextLessonBtn);
    }
    nextLessonBtn.style.display = 'none';

    try {
        const response = await fetch('/submit_answer_advanced', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                answer: answer,
                topic_id: currentState.current_topic_id,
                emotion: currentState.current_emotion,
                time_taken: time_taken,
                has_distraction: currentState.distraction_count > 0
            })
        });

        const data = await response.json();

        currentState.interaction_count++;
        if (data.is_correct) {
            currentState.correct_count++;
            feedback.innerHTML = `
                <div class="feedback-success">
                    <span style="color:#4ade80; font-size: 1.2rem; font-weight: bold;">✅ Correct!</span>
                    <p style="margin-top: 10px; line-height: 1.5;">${data.explanation}</p>
                    <div class="strategy-badge" style="background: rgba(74, 222, 128, 0.1); color: #4ade80; padding: 5px 10px; border-radius: 4px; font-size: 0.8rem; display: inline-block; margin-top: 10px;">
                        Tutor Mode: ${data.strategy}
                    </div>
                </div>
            `;
        } else {
            feedback.innerHTML = `
                <div class="feedback-error">
                    <span style="color:#f87171; font-size: 1.2rem; font-weight: bold;">❌ Not quite.</span>
                    <p style="margin-top: 10px; line-height: 1.5;">${data.explanation}</p>
                    <div class="strategy-badge" style="background: rgba(248, 113, 113, 0.1); color: #f87171; padding: 5px 10px; border-radius: 4px; font-size: 0.8rem; display: inline-block; margin-top: 10px;">
                        Tutor Mode: ${data.strategy}
                    </div>
                </div>
            `;
        }
        
        // Show the button to move forward
        nextLessonBtn.style.display = 'block';

        // Update stats
        document.getElementById('interactionCount').textContent = currentState.interaction_count;
        const rate = Math.round((currentState.correct_count / currentState.interaction_count) * 100);
        document.getElementById('correctnessRate').textContent = rate + '%';
        
        // Update AI metadata
        if (data.learning_state) {
            const tag = document.getElementById('learningStateTag');
            tag.innerHTML = `${data.state_icon || '🤷'} ${data.learning_state}`;
            tag.style.color = data.state_color || '#94a3b8';
        }
        if (data.engagement_score !== undefined) {
            document.getElementById('engagementScoreDisplay').textContent = data.engagement_score;
            document.getElementById('engagementTrendDisplay').textContent = data.engagement_trend;
        }

    } catch (error) {
        console.error('Error:', error);
        feedback.innerHTML = '<span style="color: #f87171;">⚠️ Error submitting answer. Please try again.</span>';
    }
}

function showChallenge(challenge) {
    document.getElementById('challengeSection').style.display = 'block';
    document.getElementById('challengeText').textContent = challenge.question;
}

async function submitChallenge() {
    // Similar to submitAnswer but for challenge
    const answer = document.getElementById('challengeAnswer').value.trim();
    if (!answer) return;

    try {
        const response = await fetch('/submit_answer_advanced', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                answer: answer,
                topic_id: currentState.current_topic_id + '_challenge',
                emotion: 'Engaged',
                time_taken: 60,
                has_distraction: false
            })
        });

        document.getElementById('challengeSection').style.display = 'none';

    } catch (error) {
        console.error('Error:', error);
    }
}

function startSessionTimer() {
    let remaining = currentState.session_duration * 60;

    timerInterval = setInterval(() => {
        remaining--;

        const minutes = Math.floor(remaining / 60);
        const seconds = remaining % 60;
        document.getElementById('timerDisplay').textContent = 
            `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;

        const progress = ((currentState.session_duration * 60 - remaining) / (currentState.session_duration * 60)) * 100;
        document.getElementById('progressFill').style.width = progress + '%';
        document.getElementById('progressText').textContent = Math.round(progress) + '% complete';

        if (remaining <= 0) {
            clearInterval(timerInterval);
            currentState.session_active = false;
            endSession();
        }
    }, 1000);
}

// ============================================================================
// SESSION SUMMARY
// ============================================================================

async function endSession() {
    if (learningInterval) clearInterval(learningInterval);
    if (timerInterval) clearInterval(timerInterval);

    try {
        const response = await fetch('/end_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        currentState.summary = data.summary;
        goToSummary();

    } catch (error) {
        alert('Error ending session: ' + error.message);
    }
}

function displaySessionSummary() {
    const summary = currentState.summary;

    document.getElementById('summaryDuration').textContent = 
        Math.floor(summary.duration_seconds / 60) + ':' + 
        String(summary.duration_seconds % 60).padStart(2, '0');

    document.getElementById('summaryAccuracy').textContent = summary.correctness_rate + '%';
    document.getElementById('summaryInteractions').textContent = summary.total_interactions;
    document.getElementById('summaryDistractions').textContent = summary.distraction_events.length;

    // Emotion distribution
    const emotionDist = summary.emotion_distribution;
    let emotionHTML = '<div class="emotion-grid">';
    for (const [emotion, count] of Object.entries(emotionDist)) {
        const percent = Math.round((count / summary.total_interactions) * 100);
        emotionHTML += `
            <div class="emotion-stat">
                <p>${emotion}: ${percent}%</p>
                <div class="bar" style="width: ${percent}%"></div>
            </div>
        `;
    }
    emotionHTML += '</div>';
    document.getElementById('emotionSummary').innerHTML = emotionHTML;

    // Topic mastery
    let topicHTML = '<div class="topic-list">';
    for (const [topic, data] of Object.entries(summary.topic_mastery)) {
        const mastery = data.mastery_score;
        const color = mastery >= 80 ? 'green' : mastery >= 50 ? 'yellow' : 'red';
        topicHTML += `
            <div class="topic-stat">
                <p>${topic}<span class="mastery-${color}">${Math.round(mastery)}%</span></p>
                <div class="progress" style="background: var(--color-${color});" 
                     style="width: ${mastery}%"></div>
            </div>
        `;
    }
    topicHTML += '</div>';
    document.getElementById('topicMastery').innerHTML = topicHTML;

    document.getElementById('recommendation').textContent = summary.recommendation;
}

function newSession() {
    currentState = {
        uploaded_topic_data: null,
        uploaded_questions: null,
        session_duration: 15,
        session_active: false,
        current_emotion: 'Engaged',
        interaction_count: 0,
        correct_count: 0,
        distraction_count: 0,
        current_topic_id: null,
        question_start_time: null,
        chart: null,
        emotion_history: [],
        session_id: null
    };
    goToUpload();
}

function downloadReport() {
    console.log('Report download initiated');
    // Implement PDF generation here
}

// Initialize on page load
window.addEventListener('load', () => {
    showPage('uploadPage');
});

async function fetchNextLesson() {
    console.log("🔄 Fetching next lesson block...");
    const teachingBox = document.getElementById('teachingBox');
    const teachingText = document.getElementById('teachingText');
    const readyButton = document.getElementById('readyButton');
    const questionBox = document.getElementById('questionBox');
    const feedback = document.getElementById('feedback');

    teachingBox.style.display = 'block';
    teachingText.innerHTML = 
        '<span style="color: #60a5fa; font-style: italic;">⚙️ AI is preparing your next lesson from the PDF... 🧠</span>';
    readyButton.style.display = 'none';
    questionBox.style.display = 'none';
    feedback.innerHTML = '';

    try {
        const response = await fetch('/get_next_lesson', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic_id: currentState.current_topic_id,
                emotion: currentState.current_emotion || 'Engaged'
            })
        });

        const data = await response.json();

        if (data.teaching) {
            teachingText.textContent = data.teaching;
            readyButton.style.display = 'block'; // Show "Ready for question"
            
            // Auto-scroll to show content
            teachingBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        if (data.question) {
            // Cache the question but don't show it yet
            document.getElementById('questionText').textContent = data.question;
            document.getElementById('answer').value = '';
        }

        if (data.error) {
             teachingText.innerHTML = `<span style="color: #f87171;">⚠️ Oops! ${data.error}</span>`;
             // Backend sends 'Topic complete' when the whole curriculum is finished
             if (data.error === "Topic complete") {
                 teachingText.innerHTML = "🏁 You've completed all lessons for this material! Great job!";
                 readyButton.style.display = 'none';
             }
        }

    } catch (error) {
        console.error('Error fetching lesson:', error);
        teachingText.innerHTML = `
            <div style="color: #f87171;">
                <p>⚠️ Connection error or AI took too long.</p>
                <button class="btn-primary" onclick="fetchNextLesson()">Try Again</button>
            </div>
        `;
    }
}

function showQuestion() {
    console.log("✍️ Transitioning to practice question...");
    const questionBox = document.getElementById('questionBox');
    const readyButton = document.getElementById('readyButton');
    
    questionBox.style.display = 'block';
    readyButton.style.display = 'none'; // Hide ready button once clicked
    
    currentState.question_start_time = Date.now();
    
    // Smooth scroll to question
    questionBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
