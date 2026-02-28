from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
import base64
from datetime import datetime
import os
import easyocr
import pandas as pd
import random
import re

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize EasyOCR
reader = easyocr.Reader(['en'])

# Simulated database
class SmartTagSystem:
    def __init__(self):
        self.vehicle_classes = ['car', 'motorcycle', 'bus', 'truck', 'bicycle']
        self.fraud_types = {
            'CLASS_MISMATCH': 'Vehicle Class Mismatch',
            'UNREGISTERED': 'Unregistered Vehicle',
            'INVALID_PLATE': 'Invalid License Plate'
        }
        self.registered_vehicles = self.create_sample_database()
        
    def create_sample_database(self):
        """Create sample vehicle database"""
        vehicles = []
        states = ['DL', 'MH', 'KA', 'TN', 'GJ', 'UP', 'WB']
        
        for i in range(100):
            state = random.choice(states)
            # Generate random plate number
            plate = f"{state}{random.randint(10,99)}{random.choice('ABCDEFGH')}{random.randint(1000,9999)}"
            
            vehicles.append({
                'plate_number': plate,
                'owner': f"Owner_{i}",
                'vehicle_class': random.choice(self.vehicle_classes),
                'balance': random.randint(100, 10000),
                'blacklisted': random.random() < 0.05
            })
        
        return pd.DataFrame(vehicles)
    
    def detect_vehicles(self, frame):
        """Simple vehicle detection using color and contour detection"""
        vehicles = []
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 2000:  # Filter small contours
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                
                # Filter by aspect ratio (vehicles are usually wider than tall)
                if 1.0 < aspect_ratio < 3.0:
                    vehicle_class = random.choice(self.vehicle_classes)
                    vehicles.append({
                        'bbox': [x, y, x+w, y+h],
                        'class': vehicle_class,
                        'confidence': random.uniform(0.7, 0.98),
                        'center': [x + w//2, y + h//2]
                    })
        
        return vehicles[:5]  # Limit to 5 vehicles
    
    def read_plate(self, frame, bbox):
        """Read license plate from vehicle region"""
        x1, y1, x2, y2 = bbox
        
        # Extract plate region (assume plate is in lower part of vehicle)
        plate_roi = frame[y1 + (y2-y1)//2:y2, x1:x2]
        
        if plate_roi.size == 0:
            return None
        
        # Use EasyOCR to read text
        try:
            results = reader.readtext(plate_roi)
            if results:
                # Get the text with highest confidence
                best_result = max(results, key=lambda x: x[2])
                text = best_result[1]
                confidence = best_result[2]
                
                # Clean text
                text = re.sub(r'[^A-Za-z0-9]', '', text).upper()
                
                return {
                    'text': text,
                    'confidence': confidence,
                    'bbox': [x1, y1 + (y2-y1)//2, x2-x1, (y2-y1)//2]
                }
        except Exception as e:
            print(f"OCR Error: {e}")
        
        return None
    
    def check_fraud(self, vehicles, plates):
        """Check for fraudulent activities"""
        fraud_results = []
        
        for i, vehicle in enumerate(vehicles):
            fraud_info = {
                'vehicle_class': vehicle['class'],
                'bbox': vehicle['bbox'],
                'location': (vehicle['bbox'][0], vehicle['bbox'][1]),
                'is_fraud': False,
                'fraud_type': None,
                'confidence': 0,
                'timestamp': datetime.now().isoformat()
            }
            
            # Check if plate was detected
            plate_text = None
            if i < len(plates) and plates[i]:
                plate_text = plates[i]['text']
                
                # Check if vehicle is registered
                registered = plate_text in self.registered_vehicles['plate_number'].values
                
                if not registered:
                    fraud_info['is_fraud'] = True
                    fraud_info['fraud_type'] = self.fraud_types['UNREGISTERED']
                    fraud_info['confidence'] = 0.95
                else:
                    # Check class mismatch
                    vehicle_data = self.registered_vehicles[
                        self.registered_vehicles['plate_number'] == plate_text
                    ].iloc[0]
                    
                    if vehicle_data['vehicle_class'] != vehicle['class']:
                        fraud_info['is_fraud'] = True
                        fraud_info['fraud_type'] = self.fraud_types['CLASS_MISMATCH']
                        fraud_info['confidence'] = 0.9
                    
                    # Check blacklist
                    if vehicle_data['blacklisted']:
                        fraud_info['is_fraud'] = True
                        fraud_info['fraud_type'] = 'Blacklisted Vehicle'
                        fraud_info['confidence'] = 1.0
            
            fraud_results.append(fraud_info)
        
        return fraud_results
    
    def annotate_frame(self, frame, vehicles, plates, fraud_results):
        """Annotate frame with detections"""
        annotated = frame.copy()
        
        # Draw vehicle bounding boxes
        colors = {
            'car': (0, 255, 0),
            'motorcycle': (255, 0, 0),
            'bus': (0, 0, 255),
            'truck': (255, 255, 0),
            'bicycle': (255, 0, 255)
        }
        
        for i, vehicle in enumerate(vehicles):
            x1, y1, x2, y2 = vehicle['bbox']
            color = colors.get(vehicle['class'], (255, 255, 255))
            
            # Draw rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{vehicle['class']} ({vehicle['confidence']:.2f})"
            cv2.putText(annotated, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw plate if available
            if i < len(plates) and plates[i]:
                px, py, pw, ph = plates[i]['bbox']
                cv2.rectangle(annotated, (px, py), (px+pw, py+ph), (255, 255, 0), 2)
                cv2.putText(annotated, plates[i]['text'], (px, py-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            # Draw fraud indicator
            if fraud_results[i]['is_fraud']:
                cv2.putText(annotated, f"FRAUD: {fraud_results[i]['fraud_type']}", 
                           (x1, y1-30), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.6, (0, 0, 255), 2)
        
        return annotated

# Initialize system
system = SmartTagSystem()

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.json
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Detect vehicles
        vehicles = system.detect_vehicles(frame)
        
        # Read plates
        plates = []
        for vehicle in vehicles:
            plate = system.read_plate(frame, vehicle['bbox'])
            plates.append(plate)
        
        # Check fraud
        fraud_results = system.check_fraud(vehicles, plates)
        
        # Annotate frame
        annotated_frame = system.annotate_frame(frame, vehicles, plates, fraud_results)
        
        # Convert back to base64
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        annotated_image = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            "success": True,
            "annotated_image": f"data:image/jpeg;base64,{annotated_image}",
            "vehicles": vehicles,
            "plates": [p for p in plates if p],
            "fraud_results": fraud_results,
            "stats": {
                "vehicle_count": len(vehicles),
                "plate_count": len([p for p in plates if p]),
                "fraud_count": len([f for f in fraud_results if f['is_fraud']])
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/verify_vehicle', methods=['POST'])
def verify_vehicle():
    data = request.json
    plate_number = data.get('plate_number', '').upper()
    vehicle_class = data.get('vehicle_class', '')
    
    # Check if vehicle exists
    vehicle_data = system.registered_vehicles[
        system.registered_vehicles['plate_number'] == plate_number
    ]
    
    if len(vehicle_data) == 0:
        return jsonify({
            "success": True,
            "verified": False,
            "message": "Vehicle not registered",
            "status": "UNREGISTERED"
        })
    
    vehicle = vehicle_data.iloc[0]
    
    if vehicle['blacklisted']:
        return jsonify({
            "success": True,
            "verified": False,
            "message": "Vehicle is blacklisted",
            "status": "BLACKLISTED"
        })
    
    if vehicle['vehicle_class'] != vehicle_class:
        return jsonify({
            "success": True,
            "verified": False,
            "message": f"Class mismatch. Registered as {vehicle['vehicle_class']}",
            "status": "CLASS_MISMATCH"
        })
    
    return jsonify({
        "success": True,
        "verified": True,
        "message": "Vehicle verified successfully",
        "status": "VERIFIED",
        "owner": vehicle['owner'],
        "balance": vehicle['balance']
    })

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'data': 'Connected to SmartTag server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('stream_frame')
def handle_stream_frame(data):
    try:
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Process frame
        vehicles = system.detect_vehicles(frame)
        plates = []
        for vehicle in vehicles:
            plate = system.read_plate(frame, vehicle['bbox'])
            plates.append(plate)
        
        fraud_results = system.check_fraud(vehicles, plates)
        annotated_frame = system.annotate_frame(frame, vehicles, plates, fraud_results)
        
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        annotated_image = base64.b64encode(buffer).decode('utf-8')
        
        emit('processed_frame', {
            'annotated_image': f"data:image/jpeg;base64,{annotated_image}",
            'vehicles': vehicles,
            'plates': [p for p in plates if p],
            'fraud_results': fraud_results,
            'stats': {
                'vehicle_count': len(vehicles),
                'plate_count': len([p for p in plates if p]),
                'fraud_count': len([f for f in fraud_results if f['is_fraud']])
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error processing frame: {e}")

if __name__ == '__main__':
    print("SmartTag System Starting...")
    print(f"Registered vehicles: {len(system.registered_vehicles)}")
    socketio.run(app, debug=True, port=5000)