import cv2
import numpy as np
from ultralytics import YOLO
import torch

class VehicleDetector:
    def __init__(self, model_path='../ml_models/yolov8n.pt'):
        self.model = YOLO(model_path)
        self.vehicle_classes = ['car', 'motorcycle', 'bus', 'truck', 'bicycle']
        self.colors = {
            'car': (0, 255, 0),
            'motorcycle': (255, 0, 0),
            'bus': (0, 0, 255),
            'truck': (255, 255, 0),
            'bicycle': (255, 0, 255)
        }
        
    def detect(self, frame):
        """Detect vehicles in frame"""
        results = self.model(frame, stream=True)
        vehicles = []
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Get class name
                cls = int(box.cls[0])
                class_name = self.model.names[cls]
                
                # Check if detected object is a vehicle
                if class_name in self.vehicle_classes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    confidence = float(box.conf[0])
                    
                    vehicles.append({
                        'bbox': [x1, y1, x2, y2],
                        'class': class_name,
                        'confidence': confidence,
                        'center': [(x1 + x2) // 2, (y1 + y2) // 2]
                    })
        
        return vehicles
    
    def annotate_frame(self, frame, vehicles, plates, fraud_results):
        """Annotate frame with detections"""
        annotated = frame.copy()
        
        # Draw vehicle bounding boxes
        for vehicle in vehicles:
            x1, y1, x2, y2 = vehicle['bbox']
            class_name = vehicle['class']
            color = self.colors.get(class_name, (255, 255, 255))
            
            # Draw rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{class_name} ({vehicle['confidence']:.2f})"
            cv2.putText(annotated, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Draw license plates
        for plate in plates:
            x, y, w, h = plate['bbox']
            cv2.rectangle(annotated, (x, y), (x+w, y+h), (255, 255, 0), 2)
            cv2.putText(annotated, plate['text'], (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        
        # Draw fraud indicators
        for fraud in fraud_results:
            if fraud['is_fraud']:
                x, y = fraud['location']
                cv2.putText(annotated, f"FRAUD: {fraud['fraud_type']}", 
                           (x, y-30), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 0, 255), 2)
        
        return annotated
    
    def get_vehicle_count(self, vehicles):
        """Get count of different vehicle types"""
        counts = {}
        for v in vehicles:
            counts[v['class']] = counts.get(v['class'], 0) + 1
        return counts