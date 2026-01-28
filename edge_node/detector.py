import cv2
import numpy as np
import config

class TeaDetector:
    def __init__(self, prototxt_path="MobileNetSSD_deploy.prototxt", model_path="MobileNetSSD_deploy.caffemodel"):
        """
        Initializes the detector with a pre-trained MobileNet SSD model.
        """
        self.net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
        
        # Class index for 'person' in MobileNet SSD is 15
        self.PERSON_CLASS_ID = 15

    def detect_person(self, frame):
        """
        Detects persons in the frame.
        Returns a list of bounding boxes (startX, startY, endX, endY) and confidence scores.
        """
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843,
            (300, 300), 127.5)

        self.net.setInput(blob)
        detections = self.net.forward()

        results = []

        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]

            # Filter out weak detections
            if confidence > config.CONFIDENCE_THRESHOLD:
                idx = int(detections[0, 0, i, 1])

                # Check if the detected object is a person
                if idx == self.PERSON_CLASS_ID:
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")
                    
                    # Ensure bounding box is within frame dimensions
                    startX = max(0, startX)
                    startY = max(0, startY)
                    endX = min(w, endX)
                    endY = min(h, endY)

                    results.append(((startX, startY, endX, endY), confidence))

        return results

    def check_uniform_color(self, frame, bbox):
        """
        Checks if the person in the bounding box is wearing the target uniform.
        Focuses on the upper body (upper 50% of the bounding box).
        """
        (startX, startY, endX, endY) = bbox
        
        # Calculate height of the person
        height = endY - startY
        
        # Focus on the upper body (e.g., top 50% of the detection)
        # We start slightly below the top to avoid head/hair, say top 10% to 60%
        upper_body_start_y = startY + int(height * 0.1)
        upper_body_end_y = startY + int(height * 0.6)
        
        # Crop the upper body region
        roi = frame[upper_body_start_y:upper_body_end_y, startX:endX]
        
        if roi.size == 0:
            return False, 0.0

        # Convert to HSV
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Create mask for the uniform color
        lower_bound = np.array(config.UNIFORM_HSV_LOWER, dtype="uint8")
        upper_bound = np.array(config.UNIFORM_HSV_UPPER, dtype="uint8")
        
        mask = cv2.inRange(hsv_roi, lower_bound, upper_bound)
        
        # Calculate percentage of matching pixels
        total_pixels = roi.shape[0] * roi.shape[1]
        matching_pixels = cv2.countNonZero(mask)
        
        percentage = (matching_pixels / total_pixels) * 100
        
        is_detected = percentage >= config.UNIFORM_PIXEL_PERCENTAGE_THRESHOLD
        
        return is_detected, percentage
