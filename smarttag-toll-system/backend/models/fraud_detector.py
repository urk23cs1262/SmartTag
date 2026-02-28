import pandas as pd
import numpy as np
from datetime import datetime
import random

class FraudDetector:
    def __init__(self):
        self.fraud_types = {
            'CLASS_MISMATCH': 'Vehicle Class Mismatch',
            'UNREGISTERED': 'Unregistered Vehicle',
            'INVALID_PLATE': 'Invalid License Plate',
            'DUPLICATE': 'Duplicate Entry',
            'SPEEDING': 'Speeding Violation',
            'LANE_VIOLATION': 'Lane Violation'
        }
        
        # Simulated FASTag database
        self.registered_vehicles = self.create_sample_database()
        
    def create_sample_database(self):
        """Create sample FASTag database"""
        vehicles = []
        
        # Sample vehicle data
        vehicle_classes = ['car', 'motorcycle', 'bus', 'truck']
        states = ['DL', 'MH', 'KA', 'TN', 'GJ', 'UP', 'WB']
        
        for i in range(100):
            state = random.choice(states)
            if random.random() > 0.5:
                # Format: DL01AB1234
                plate = f"{state}{random.randint(10,99)}{random.choice('ABCDEFGH')}{random.choice('ABCDEFGH')}{random.randint(1000,9999)}"
            else:
                # Format: DL01A1234
                plate = f"{state}{random.randint(10,99)}{random.choice('ABCDEFGH')}{random.randint(1000,9999)}"
            
            vehicles.append({
                'plate_number': plate,
                'owner_name': f"Owner_{i}",
                'vehicle_class': random.choice(vehicle_classes),
                'registration_date': f"202{random.randint(0,3)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                'balance': random.randint(100, 10000),
                'toll_pass': f"TAG{random.randint(10000,99999)}",
                'blacklisted': random.random() < 0.05  # 5% blacklisted
            })
        
        return pd.DataFrame(vehicles)
    
    def check_fraud(self, plates, vehicles):
        """Check for fraudulent activities"""
        fraud_results = []
        timestamp = datetime.now()
        
        for i, vehicle in enumerate(vehicles):
            fraud_info = {
                'vehicle_class': vehicle['class'],
                'bbox': vehicle['bbox'],
                'location': (vehicle['bbox'][0], vehicle['bbox'][1]),
                'is_fraud': False,
                'fraud_type': None,
                'confidence': 0,
                'timestamp': timestamp.isoformat()
            }
            
            # Check if plate was detected for this vehicle
            plate_found = False
            plate_text = None
            
            if i < len(plates):
                plate_found = True
                plate_text = plates[i]['text']
            
            # Check for different fraud scenarios
            if plate_found and plate_text:
                # Check if vehicle is registered
                registered = self.check_registration(plate_text)
                
                if not registered:
                    fraud_info['is_fraud'] = True
                    fraud_info['fraud_type'] = self.fraud_types['UNREGISTERED']
                    fraud_info['confidence'] = 0.95
                
                else:
                    # Check class mismatch
                    mismatch = self.check_class_mismatch(plate_text, vehicle['class'])
                    if mismatch:
                        fraud_info['is_fraud'] = True
                        fraud_info['fraud_type'] = self.fraud_types['CLASS_MISMATCH']
                        fraud_info['confidence'] = 0.9
                    
                    # Check blacklist
                    blacklisted = self.check_blacklist(plate_text)
                    if blacklisted:
                        fraud_info['is_fraud'] = True
                        fraud_info['fraud_type'] = 'Blacklisted Vehicle'
                        fraud_info['confidence'] = 1.0
                    
                    # Check low balance
                    low_balance = self.check_balance(plate_text)
                    if low_balance:
                        fraud_info['is_fraud'] = True
                        fraud_info['fraud_type'] = 'Insufficient Balance'
                        fraud_info['confidence'] = 1.0
            
            elif plate_found and not plates[i]['is_valid']:
                # Invalid plate format
                fraud_info['is_fraud'] = True
                fraud_info['fraud_type'] = self.fraud_types['INVALID_PLATE']
                fraud_info['confidence'] = 0.8
            
            else:
                # No plate detected
                fraud_info['is_fraud'] = True
                fraud_info['fraud_type'] = 'No License Plate Detected'
                fraud_info['confidence'] = 0.7
            
            fraud_results.append(fraud_info)
        
        return fraud_results
    
    def check_registration(self, plate_number):
        """Check if vehicle is registered"""
        return plate_number in self.registered_vehicles['plate_number'].values
    
    def check_class_mismatch(self, plate_number, detected_class):
        """Check if detected class matches registered class"""
        vehicle_data = self.registered_vehicles[
            self.registered_vehicles['plate_number'] == plate_number
        ]
        
        if len(vehicle_data) > 0:
            registered_class = vehicle_data.iloc[0]['vehicle_class']
            return registered_class != detected_class
        
        return False
    
    def check_blacklist(self, plate_number):
        """Check if vehicle is blacklisted"""
        vehicle_data = self.registered_vehicles[
            self.registered_vehicles['plate_number'] == plate_number
        ]
        
        if len(vehicle_data) > 0:
            return vehicle_data.iloc[0]['blacklisted']
        
        return False
    
    def check_balance(self, plate_number):
        """Check if account has sufficient balance"""
        vehicle_data = self.registered_vehicles[
            self.registered_vehicles['plate_number'] == plate_number
        ]
        
        if len(vehicle_data) > 0:
            return vehicle_data.iloc[0]['balance'] < 200  # Minimum toll amount
        
        return False
    
    def verify_vehicle(self, plate_number, detected_class):
        """Verify vehicle details"""
        vehicle_data = self.registered_vehicles[
            self.registered_vehicles['plate_number'] == plate_number
        ]
        
        if len(vehicle_data) == 0:
            return {
                'verified': False,
                'message': 'Vehicle not registered in FASTag system',
                'status': 'UNREGISTERED'
            }
        
        vehicle = vehicle_data.iloc[0]
        
        if vehicle['blacklisted']:
            return {
                'verified': False,
                'message': 'Vehicle is blacklisted',
                'status': 'BLACKLISTED'
            }
        
        if vehicle['balance'] < 200:
            return {
                'verified': False,
                'message': f'Insufficient balance: ₹{vehicle["balance"]}',
                'status': 'LOW_BALANCE'
            }
        
        if vehicle['vehicle_class'] != detected_class:
            return {
                'verified': False,
                'message': f'Class mismatch: Registered as {vehicle["vehicle_class"]}',
                'status': 'CLASS_MISMATCH'
            }
        
        return {
            'verified': True,
            'message': 'Vehicle verified successfully',
            'status': 'VERIFIED',
            'owner': vehicle['owner_name'],
            'balance': vehicle['balance']
        }
    
    def generate_summary(self, results):
        """Generate summary of processing results"""
        total_frames = len(results)
        total_vehicles = sum(len(r['vehicles']) for r in results)
        total_plates = sum(len(r['plates']) for r in results)
        total_frauds = sum(sum(1 for f in r['fraud_results'] if f['is_fraud']) for r in results)
        
        fraud_types = {}
        for r in results:
            for f in r['fraud_results']:
                if f['is_fraud']:
                    fraud_types[f['fraud_type']] = fraud_types.get(f['fraud_type'], 0) + 1
        
        return {
            'total_frames': total_frames,
            'total_vehicles': total_vehicles,
            'total_plates': total_plates,
            'total_frauds': total_frauds,
            'fraud_rate': (total_frauds / total_vehicles * 100) if total_vehicles > 0 else 0,
            'fraud_types': fraud_types,
            'timestamp': datetime.now().isoformat()
        }