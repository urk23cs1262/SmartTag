import sqlite3
import pandas as pd
from datetime import datetime
import json

class DatabaseManager:
    def __init__(self, db_path='smarttag.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                plate_number TEXT,
                vehicle_class TEXT,
                fraud_type TEXT,
                is_fraud BOOLEAN,
                confidence REAL,
                image_path TEXT,
                verified BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Create vehicles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                plate_number TEXT PRIMARY KEY,
                owner_name TEXT,
                vehicle_class TEXT,
                registration_date DATE,
                balance REAL,
                toll_pass TEXT,
                blacklisted BOOLEAN DEFAULT FALSE,
                last_seen DATETIME
            )
        ''')
        
        # Create fraud_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fraud_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                plate_number TEXT,
                fraud_type TEXT,
                confidence REAL,
                action_taken TEXT,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_transaction(self, fraud_result):
        """Save transaction to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transactions (timestamp, vehicle_class, fraud_type, is_fraud, confidence)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            fraud_result['timestamp'],
            fraud_result['vehicle_class'],
            fraud_result['fraud_type'],
            fraud_result['is_fraud'],
            fraud_result['confidence']
        ))
        
        conn.commit()
        conn.close()
    
    def save_vehicle(self, vehicle_data):
        """Save vehicle information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO vehicles 
            (plate_number, owner_name, vehicle_class, registration_date, balance, toll_pass, blacklisted, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vehicle_data['plate_number'],
            vehicle_data['owner_name'],
            vehicle_data['vehicle_class'],
            vehicle_data['registration_date'],
            vehicle_data['balance'],
            vehicle_data['toll_pass'],
            vehicle_data.get('blacklisted', False),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self):
        """Get system statistics"""
        conn = sqlite3.connect(self.db_path)
        
        # Total transactions
        total = pd.read_sql("SELECT COUNT(*) as count FROM transactions", conn).iloc[0]['count']
        
        # Fraud transactions
        fraud = pd.read_sql("SELECT COUNT(*) as count FROM transactions WHERE is_fraud = 1", conn).iloc[0]['count']
        
        # Fraud by type
        fraud_by_type = pd.read_sql("""
            SELECT fraud_type, COUNT(*) as count 
            FROM transactions 
            WHERE is_fraud = 1 
            GROUP BY fraud_type
        """, conn)
        
        # Hourly distribution
        hourly = pd.read_sql("""
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count 
            FROM transactions 
            GROUP BY hour 
            ORDER BY hour
        """, conn)
        
        # Vehicle distribution
        vehicles = pd.read_sql("""
            SELECT vehicle_class, COUNT(*) as count 
            FROM transactions 
            GROUP BY vehicle_class
        """, conn)
        
        conn.close()
        
        return {
            'total_transactions': int(total),
            'fraud_transactions': int(fraud),
            'fraud_rate': (fraud / total * 100) if total > 0 else 0,
            'fraud_by_type': fraud_by_type.to_dict('records') if not fraud_by_type.empty else [],
            'hourly_distribution': hourly.to_dict('records') if not hourly.empty else [],
            'vehicle_distribution': vehicles.to_dict('records') if not vehicles.empty else []
        }
    
    def get_recent_transactions(self, limit=100):
        """Get recent transactions"""
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
            SELECT * FROM transactions 
            ORDER BY timestamp DESC 
            LIMIT {limit}
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        return df.to_dict('records')
    
    def log_fraud(self, plate_number, fraud_type, confidence, action_taken=None):
        """Log fraud detection"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO fraud_logs (timestamp, plate_number, fraud_type, confidence, action_taken)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            plate_number,
            fraud_type,
            confidence,
            action_taken
        ))
        
        conn.commit()
        conn.close()
    
    def resolve_fraud(self, log_id):
        """Mark fraud as resolved"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE fraud_logs SET resolved = 1 WHERE id = ?', (log_id,))
        
        conn.commit()
        conn.close()