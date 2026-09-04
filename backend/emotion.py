import mediapipe as mp
import cv2
from emotion_model import classifier

mp_face = mp.solutions.face_mesh

face_mesh = mp_face.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True
)

def get_emotion(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if not results.multi_face_landmarks:
        return "No Face"

    landmarks = results.multi_face_landmarks[0].landmark

    # Direct geometry heuristics for responsive demo (replaces dummy SVM)
    nose = landmarks[1]
    left_eye = landmarks[159]
    right_eye = landmarks[386]
    left_mouth = landmarks[61]
    right_mouth = landmarks[291]
    left_eyebrow = landmarks[70]
    right_eyebrow = landmarks[300]
    upper_lip = landmarks[13]
    lower_lip = landmarks[14]

    # Calculate distances
    mouth_width = abs(right_mouth.x - left_mouth.x)
    eye_distance = abs(right_eye.x - left_eye.x)
    mouth_height = abs(upper_lip.y - lower_lip.y)
    
    left_brow_height = abs(left_eyebrow.y - left_eye.y)
    right_brow_height = abs(right_eyebrow.y - right_eye.y)
    avg_brow_height = (left_brow_height + right_brow_height) / 2.0

    # Heuristics
    if mouth_width > eye_distance * 1.15:
        return "Engaged"  # Smiling
    elif avg_brow_height < 0.05:
        return "Frustrated" # Brows furrowed
    elif mouth_height > 0.05 and avg_brow_height < 0.07:
         return "Confused" # Mouth slightly open, brows slightly down
    elif avg_brow_height > 0.10:
         return "Bored" # Brows high, passive face
    
    return "Engaged" # Neutral defaults to engaged