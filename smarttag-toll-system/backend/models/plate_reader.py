from paddleocr import PaddleOCR
import cv2
import numpy as np
import re

class PlateReader:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
        self.plate_pattern = re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$|^[A-Z]{2}[0-9]{13}$')
        
    def read_plates(self, frame, vehicles):
        """Read license plates from detected vehicles"""
        plates = []
        
        for vehicle in vehicles:
            # Extract vehicle region
            x1, y1, x2, y2 = vehicle['bbox']
            vehicle_roi = frame[y1:y2, x1:x2]
            
            if vehicle_roi.size == 0:
                continue
            
            # Perform OCR on vehicle region
            result = self.ocr.ocr(vehicle_roi, cls=True)
            
            if result and result[0]:
                for line in result[0]:
                    text = line[1][0]
                    confidence = line[1][1]
                    
                    # Clean and validate plate text
                    cleaned_text = self.clean_plate_text(text)
                    
                    plates.append({
                        'text': cleaned_text,
                        'confidence': confidence,
                        'bbox': [x1, y1, x2-x1, y2-y1],
                        'vehicle_class': vehicle['class'],
                        'is_valid': self.validate_plate(cleaned_text)
                    })
        
        return plates
    
    def clean_plate_text(self, text):
        """Clean and format license plate text"""
        # Remove special characters and spaces
        cleaned = re.sub(r'[^A-Za-z0-9]', '', text)
        return cleaned.upper()
    
    def validate_plate(self, plate_text):
        """Validate license plate format"""
        if not plate_text:
            return False
        
        # Check if plate matches Indian format
        return bool(self.plate_pattern.match(plate_text))
    
    def preprocess_plate(self, plate_image):
        """Preprocess plate image for better OCR"""
        # Convert to grayscale
        gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(thresh)
        
        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        return enhanced