import cv2
import numpy as np
import config

class TeaDetector:
    def __init__(self):
        """
        Initializes the detector (no model loading needed as detection comes from ROS topic).
        """
        # The MobileNetSSD model loading is removed as it's no longer used for person detection.
        # This class now primarily serves the check_uniform_color functionality.
        pass

    def check_uniform_color(self, frame, bbox):
        """
        Checks if the person in the bounding box is wearing the target uniform.
        Focuses on the upper body (upper 50% of the bounding box).
        """
        (startX, startY, endX, endY) = bbox
        
        # Calculate height of the person
        height = endY - startY
        
        # Focus on the upper body (e.g., top 10% to 60% of the detection)
        upper_body_start_y = startY + int(height * 0.1)
        upper_body_end_y = startY + int(height * 0.6)
        
        # Crop the upper body region, ensuring coordinates are within frame bounds
        # Also ensure start <= end for valid slicing
        upper_body_start_y = max(0, min(upper_body_start_y, frame.shape[0]))
        upper_body_end_y = max(0, min(upper_body_end_y, frame.shape[0]))
        startX = max(0, min(startX, frame.shape[1]))
        endX = max(0, min(endX, frame.shape[1]))

        if upper_body_start_y >= upper_body_end_y or startX >= endX:
            # Invalid ROI, cannot process
            return False, 0.0, None

        roi = frame[upper_body_start_y:upper_body_end_y, startX:endX]
        
        if roi.size == 0:
            return False, 0.0, None

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
        
        return is_detected, percentage, mask
