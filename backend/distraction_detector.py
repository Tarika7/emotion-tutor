import cv2
import numpy as np
from ultralytics import YOLO
import os

class DistractionDetector:
    def __init__(self):
        """Initialize YOLOv8 model for object detection"""
        self.model = None
        self.is_loaded = False
        self.distraction_classes = {
            'cell phone': 'phone',
            'phone': 'phone',
            'laptop': 'laptop',
            'tablet': 'tablet',
            'computer': 'screen',
            'teddy bear': 'toy',
            'dog': 'pet',
            'cat': 'pet',
            'book': 'book',
            'cup': 'beverage',
            'sports ball': 'ball',
            'keyboard': 'keyboard',
            'mouse': 'mouse',
            'tv': 'tv',
            'monitor': 'monitor'
        }
        
        self.critical_distractions = ['phone']  # Only phone explicitly blocks learning; laptops and TVs are common environmental background
        
        try:
            print("Loading YOLOv8 model...")
            self.model = YOLO('yolov8n.pt')  # nano model for speed
            self.is_loaded = True
            print("YOLOv8 model loaded successfully")
        except Exception as e:
            print(f"Failed to load YOLOv8: {e}")
            self.is_loaded = False
    
    def detect_distractions(self, frame):
        """
        Detect distractions in frame
        Returns: {
            'has_distractions': bool,
            'critical_distraction': bool,
            'distractions': [{'type': str, 'confidence': float}],
            'annotated_frame': frame
        }
        """
        
        if not self.is_loaded or self.model is None:
            return {
                'has_distractions': False,
                'critical_distraction': False,
                'distractions': [],
                'annotated_frame': frame
            }
        
        results = self.model(frame, verbose=False)
        
        distractions = []
        critical_distraction = False
        annotated_frame = frame.copy()
        
        if results and len(results) > 0:
            detections = results[0]
            
            if detections.boxes is not None:
                for box in detections.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    # Only process high-confidence detections
                    if conf < 0.25:
                        continue
                    
                    class_name = detections.names[cls_id].lower()
                    distraction_type = self.distraction_classes.get(class_name, class_name)
                    
                    # Check if this is a distraction we care about
                    if distraction_type in self.critical_distractions and conf >= 0.3:
                        critical_distraction = True
                    
                    distractions.append({
                        'type': distraction_type,
                        'confidence': round(conf, 2),
                        'class': class_name,
                        'box': box.xyxy[0].tolist()
                    })
                    
                    # Draw bounding box on frame
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    color = (0, 0, 255) if distraction_type in self.critical_distractions else (0, 255, 0)
                    
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(annotated_frame, f"{distraction_type} ({conf:.2f})", 
                               (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        has_distractions = len(distractions) > 0
        
        return {
            'has_distractions': has_distractions,
            'critical_distraction': critical_distraction,
            'distractions': distractions,
            'annotated_frame': annotated_frame
        }
    
    def get_distraction_message(self, distractions):
        """Generate user-friendly message about detected distractions"""
        if not distractions:
            return "Keep focusing! 👍"
        
        types = [d['type'] for d in distractions if d['type'] in self.critical_distractions]
        
        if 'phone' in types:
            return "📱 PHONE DETECTED! Put it away to continue learning."
        elif 'laptop' in types:
            return "💻 Another screen detected! Focus on this lesson."
        elif 'pet' in types:
            return "🐕 Pet or animal detected nearby. Minimize distractions!"
        elif 'tv' in types:
            return "📺 TV detected! Turn it off to improve focus."
        
        return "Distraction detected! Focus on the lesson."

# Global detector instance
detector = DistractionDetector()
