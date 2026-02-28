from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
import base64
from datetime import datetime
import easyocr
import pandas as pd
import random
import re
import os

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

print("Loading EasyOCR...")
reader = easyocr.Reader(['en'], gpu=False)
print("EasyOCR loaded successfully!")

class SmartTagSystem:
    def __init__(self):
        self.vehicle_classes = ['car', 'motorcycle', 'bus', 'truck']
        self.fraud_types = {
            'CLASS_MISMATCH': 'Vehicle Class Mismatch',
            'UNREGISTERED': 'Unregistered Vehicle',
            'INVALID_PLATE': 'Invalid License Plate'
        }
        self.registered_vehicles = self.create_sample_database()
        print(f"System initialized with {len(self.registered_vehicles)} registered vehicles")
        
    def create_sample_database(self):
        vehicles = []
        states = ['DL', 'MH', 'KA', 'TN', 'GJ', 'UP', 'WB', 'HR', 'RJ', 'MP']
        
        for i in range(100):
            state = random.choice(states)
            if random.random() > 0.5:
                plate = f"{state}{random.randint(10,99)}{random.choice('ABCDEFGH')}{random.randint(1000,9999)}"
            else:
                plate = f"{state}{random.randint(10,99)}{random.randint(1000,9999)}"
            
            vehicles.append({
                'plate_number': plate,
                'owner': f"Owner_{i}",
                'vehicle_class': random.choice(self.vehicle_classes),
                'balance': random.randint(100, 10000),
                'blacklisted': random.random() < 0.05
            })
        
        return pd.DataFrame(vehicles)
    
    def detect_vehicles_simple(self, frame):
        vehicles = []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 5000:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                
                if 1.2 < aspect_ratio < 3.0:
                    if area > 30000:
                        vehicle_class = 'truck' if random.random() > 0.5 else 'bus'
                    elif area > 15000:
                        vehicle_class = 'car'
                    else:
                        vehicle_class = 'motorcycle'
                    
                    vehicles.append({
                        'bbox': [x, y, x+w, y+h],
                        'class': vehicle_class,
                        'confidence': random.uniform(0.75, 0.98),
                        'center': [x + w//2, y + h//2]
                    })
        
        return vehicles[:3]
    
    def read_plate_easyocr(self, frame, bbox):
        x1, y1, x2, y2 = bbox
        
        vehicle_roi = frame[y1:y2, x1:x2]
        if vehicle_roi.size == 0:
            return None
        
        h, w = vehicle_roi.shape[:2]
        plate_region = vehicle_roi[h//2:h, :]
        
        if plate_region.size == 0:
            return None
        
        try:
            gray = cv2.cvtColor(plate_region, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            results = reader.readtext(thresh)
            
            if results:
                best_result = max(results, key=lambda x: x[2])
                text = best_result[1]
                confidence = best_result[2]
                
                text = re.sub(r'[^A-Za-z0-9]', '', text).upper()
                
                if len(text) >= 4:
                    return {
                        'text': text,
                        'confidence': confidence,
                        'bbox': [x1, y1 + h//2, w, h//2]
                    }
        except Exception as e:
            print(f"OCR Error: {e}")
        
        return None
    
    def check_fraud(self, vehicles, plates):
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
            
            if i < len(plates) and plates[i]:
                plate_text = plates[i]['text']
                registered = plate_text in self.registered_vehicles['plate_number'].values
                
                if not registered:
                    fraud_info['is_fraud'] = True
                    fraud_info['fraud_type'] = self.fraud_types['UNREGISTERED']
                    fraud_info['confidence'] = 0.95
                else:
                    vehicle_data = self.registered_vehicles[
                        self.registered_vehicles['plate_number'] == plate_text
                    ]
                    
                    if len(vehicle_data) > 0:
                        vehicle_data = vehicle_data.iloc[0]
                        
                        if vehicle_data['vehicle_class'] != vehicle['class']:
                            fraud_info['is_fraud'] = True
                            fraud_info['fraud_type'] = self.fraud_types['CLASS_MISMATCH']
                            fraud_info['confidence'] = 0.9
                        
                        if vehicle_data['blacklisted']:
                            fraud_info['is_fraud'] = True
                            fraud_info['fraud_type'] = 'Blacklisted Vehicle'
                            fraud_info['confidence'] = 1.0
            else:
                if random.random() < 0.3:
                    fraud_info['is_fraud'] = True
                    fraud_info['fraud_type'] = 'No License Plate'
                    fraud_info['confidence'] = 0.6
            
            fraud_results.append(fraud_info)
        
        return fraud_results
    
    def annotate_frame(self, frame, vehicles, plates, fraud_results):
        annotated = frame.copy()
        
        colors = {
            'car': (0, 255, 0),
            'motorcycle': (255, 0, 0),
            'bus': (0, 0, 255),
            'truck': (255, 255, 0)
        }
        
        for i, vehicle in enumerate(vehicles):
            x1, y1, x2, y2 = vehicle['bbox']
            color = colors.get(vehicle['class'], (255, 255, 255))
            
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{vehicle['class']} ({vehicle['confidence']:.2f})"
            cv2.putText(annotated, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            if i < len(plates) and plates[i]:
                px, py, pw, ph = plates[i]['bbox']
                cv2.rectangle(annotated, (px, py), (px+pw, py+ph), (255, 255, 0), 2)
                cv2.putText(annotated, plates[i]['text'], (px, py-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            if fraud_results[i]['is_fraud']:
                cv2.putText(annotated, f"FRAUD: {fraud_results[i]['fraud_type']}", 
                           (x1, y1-30), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.5, (0, 0, 255), 2)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated, timestamp, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return annotated

system = SmartTagSystem()

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "vehicles_registered": len(system.registered_vehicles)
    })

@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.json
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({"success": False, "error": "Invalid image"}), 400
        
        vehicles = system.detect_vehicles_simple(frame)
        
        plates = []
        for vehicle in vehicles:
            plate = system.read_plate_easyocr(frame, vehicle['bbox'])
            plates.append(plate)
        
        fraud_results = system.check_fraud(vehicles, plates)
        annotated_frame = system.annotate_frame(frame, vehicles, plates, fraud_results)
        
        _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
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
        print(f"Error processing frame: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/verify_vehicle', methods=['POST'])
def verify_vehicle():
    try:
        data = request.json
        plate_number = data.get('plate_number', '').upper()
        vehicle_class = data.get('vehicle_class', '')
        
        vehicle_data = system.registered_vehicles[
            system.registered_vehicles['plate_number'] == plate_number
        ]
        
        if len(vehicle_data) == 0:
            return jsonify({
                "success": True,
                "verified": False,
                "message": "Vehicle not registered in FASTag system",
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
            "balance": float(vehicle['balance'])
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
        
        if frame is None:
            return
        
        vehicles = system.detect_vehicles_simple(frame)
        plates = []
        for vehicle in vehicles:
            plate = system.read_plate_easyocr(frame, vehicle['bbox'])
            plates.append(plate)
        
        fraud_results = system.check_fraud(vehicles, plates)
        annotated_frame = system.annotate_frame(frame, vehicles, plates, fraud_results)
        
        _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
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
        print(f"Error processing stream frame: {e}")

if __name__ == '__main__':
    print("="*50)
    print("SmartTag Toll Verification System")
    print("="*50)
    print(f"Python Version: {os.sys.version}")
    print(f"Registered Vehicles: {len(system.registered_vehicles)}")
    print(f"Server starting on http://localhost:5000")
    print("="*50)
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)