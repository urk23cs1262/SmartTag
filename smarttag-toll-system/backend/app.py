from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from models.vehicle_detector import VehicleDetector
from models.plate_reader import PlateReader
from models.fraud_detector import FraudDetector
from database.database import DatabaseManager
import os
import cv2
import numpy as np
import base64
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize components
vehicle_detector = VehicleDetector()
plate_reader = PlateReader()
fraud_detector = FraudDetector()
db_manager = DatabaseManager()

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        
        # Process frame
        # Detect vehicles
        vehicles = vehicle_detector.detect(frame)
        
        # Read license plates
        plates = plate_reader.read_plates(frame, vehicles)
        
        # Check fraud
        fraud_results = fraud_detector.check_fraud(plates, vehicles)
        
        # Save to database
        for result in fraud_results:
            db_manager.save_transaction(result)
        
        # Annotate frame
        annotated_frame = vehicle_detector.annotate_frame(frame, vehicles, plates, fraud_results)
        
        # Convert back to base64
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        annotated_image = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            "success": True,
            "annotated_image": f"data:image/jpeg;base64,{annotated_image}",
            "vehicles": vehicles,
            "plates": plates,
            "fraud_results": fraud_results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"success": False, "error": "No video file provided"}), 400
    
    video = request.files['video']
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{video.filename}"
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    video.save(video_path)
    
    return jsonify({
        "success": True,
        "video_path": video_path,
        "filename": filename
    })

@app.route('/api/process_video/<filename>', methods=['GET'])
def process_video(filename):
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(video_path):
        return jsonify({"success": False, "error": "Video not found"}), 404
    
    cap = cv2.VideoCapture(video_path)
    results = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process each frame
        vehicles = vehicle_detector.detect(frame)
        plates = plate_reader.read_plates(frame, vehicles)
        fraud_results = fraud_detector.check_fraud(plates, vehicles)
        
        results.append({
            "vehicles": vehicles,
            "plates": plates,
            "fraud_results": fraud_results
        })
    
    cap.release()
    
    # Generate summary
    summary = fraud_detector.generate_summary(results)
    
    return jsonify({
        "success": True,
        "summary": summary,
        "total_frames": len(results)
    })

@app.route('/api/get_statistics', methods=['GET'])
def get_statistics():
    stats = db_manager.get_statistics()
    return jsonify({"success": True, "statistics": stats})

@app.route('/api/get_transactions', methods=['GET'])
def get_transactions():
    limit = request.args.get('limit', 100, type=int)
    transactions = db_manager.get_recent_transactions(limit)
    return jsonify({"success": True, "transactions": transactions})

@app.route('/api/verify_vehicle', methods=['POST'])
def verify_vehicle():
    data = request.json
    plate_number = data.get('plate_number')
    vehicle_class = data.get('vehicle_class')
    
    result = fraud_detector.verify_vehicle(plate_number, vehicle_class)
    return jsonify({"success": True, "verification": result})

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'data': 'Connected to SmartTag server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('stream_frame')
def handle_stream_frame(data):
    # Process live stream frame
    image_data = data['image'].split(',')[1]
    image_bytes = base64.b64decode(image_data)
    
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Process frame
    vehicles = vehicle_detector.detect(frame)
    plates = plate_reader.read_plates(frame, vehicles)
    fraud_results = fraud_detector.check_fraud(plates, vehicles)
    
    # Annotate frame
    annotated_frame = vehicle_detector.annotate_frame(frame, vehicles, plates, fraud_results)
    
    _, buffer = cv2.imencode('.jpg', annotated_frame)
    annotated_image = base64.b64encode(buffer).decode('utf-8')
    
    emit('processed_frame', {
        'image': f"data:image/jpeg;base64,{annotated_image}",
        'vehicles': vehicles,
        'plates': plates,
        'fraud_results': fraud_results,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)