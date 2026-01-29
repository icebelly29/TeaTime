import cv2
import numpy as np
import config
import time

try:
    from hobot_dnn import pyeasy_dnn
    RDK_AVAILABLE = True
except ImportError:
    RDK_AVAILABLE = False

# Import the post-processor helper
try:
    from fcos_lib import FcosPostProcessor
except ImportError:
    print("[WARN] fcos_lib not found. RDK post-processing will not work.")
    FcosPostProcessor = None

class RDKDetector:
    def __init__(self, model_path=config.RDK_MODEL_PATH):
        if not RDK_AVAILABLE:
            raise ImportError("hobot_dnn library not found. Are you running on RDK X5?")
        
        print(f"[RDK] Loading BPU model from {model_path}...")
        self.models = pyeasy_dnn.load(model_path)
        self.h = config.RDK_MODEL_HEIGHT
        self.w = config.RDK_MODEL_WIDTH
        
        # Initialize post-processor
        if FcosPostProcessor:
            # We assume model 0 is the detector
            # Note: We initialize with default/config sizes.
            # Ideally, these should match the camera resolution for correct scaling,
            # but FcosPostProcessor handles scaling internally via "ori_w/h" in its struct.
            # We'll pass 1920x1080 as a default "original" size, or update it per frame if needed.
            # For now, let's assume a standard 640x480 capture from main.py, 
            # but FCOS usually expects 1920x1080 context for its "ori" params if coming from HDMI sample.
            # We will act as if the "original" frame is what we get in detect_person.
            self.postprocessor = FcosPostProcessor(
                self.models[0].outputs, 
                input_w=self.w, 
                input_h=self.h,
                ori_w=640, # Default, will be updated/ignored by drawing logic if we handled it there
                ori_h=480
            )
        else:
            self.postprocessor = None

    def bgr2nv12_opencv(self, image):
        height, width = image.shape[0], image.shape[1]
        area = height * width
        yuv420p = cv2.cvtColor(image, cv2.COLOR_BGR2YUV_I420).reshape((area * 3 // 2,))
        y = yuv420p[:area]
        uv_planar = yuv420p[area:].reshape((2, area // 4))
        uv_packed = uv_planar.transpose((1, 0)).reshape((area // 2,))
        nv12 = np.zeros_like(yuv420p)
        nv12[:area] = y
        nv12[area:] = uv_packed
        return nv12

    def preprocess(self, img):
        resized = cv2.resize(img, (self.w, self.h))
        nv12_data = self.bgr2nv12_opencv(resized)
        return nv12_data

    def detect_person(self, frame):
        """
        Detects persons in the frame using RDK BPU.
        Returns: list of ((x1, y1, x2, y2), confidence)
        """
        if not self.postprocessor:
            return []

        h, w = frame.shape[:2]
        
        # Update original dimensions in post-processor info struct for correct scaling
        self.postprocessor.info.ori_height = h
        self.postprocessor.info.ori_width = w
        
        nv12_data = self.preprocess(frame)
        
        t0 = time.time()
        outputs = self.models[0].forward(nv12_data)
        # print(f"[RDK] Inference: {(time.time()-t0)*1000:.1f}ms")
        
        results = self.postprocessor.process(outputs)
        
        parsed_detections = []
        for det in results:
            # det is {'bbox': [x1, y1, x2, y2], 'score': float, 'id': int, 'name': str}
            # Class 'person' is usually 'person' or id 0
            if det.get('name') == 'person':
                bbox = det['bbox']
                score = det['score']
                
                # Scale bbox to original frame size
                # The FCOS post-process lib might return coords relative to model input or original?
                # Based on 'draw_bboxs' in the sample, it returns coords that need scaling.
                # "coor[0] = int(coor[0] * scale_x)" where scale_x = target_w / ori_w
                # Wait, the sample code sets 'ori_width' in the struct to display res.
                # If we set ori_width in struct to 'w' (frame width), maybe it returns scaled coords?
                # Let's check logic:
                # The sample code passes 1920x1080 as ori.
                # The sample code MANUALY scales the output bbox by (target_w / ori_w).
                # This implies the library returns coordinates in the range of [0, ori_w].
                # So if we set info.ori_width = w, the output should be [0, w].
                
                # However, to be safe, we will just take the raw output and clamp/round.
                # Let's assume the library respects the 'ori' dimensions we set.
                
                x1, y1, x2, y2 = bbox
                
                # Ensure they are integers
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Clamp
                x1 = max(0, min(w, x1))
                y1 = max(0, min(h, y1))
                x2 = max(0, min(w, x2))
                y2 = max(0, min(h, y2))
                
                parsed_detections.append(((x1, y1, x2, y2), score))
                
        return parsed_detections

    def check_uniform_color(self, frame, bbox):
        (startX, startY, endX, endY) = bbox
        height = endY - startY
        upper_body_start_y = startY + int(height * 0.1)
        upper_body_end_y = startY + int(height * 0.6)
        
        roi = frame[upper_body_start_y:upper_body_end_y, startX:endX]
        if roi.size == 0: return False, 0.0

        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lower_bound = np.array(config.UNIFORM_HSV_LOWER, dtype="uint8")
        upper_bound = np.array(config.UNIFORM_HSV_UPPER, dtype="uint8")
        mask = cv2.inRange(hsv_roi, lower_bound, upper_bound)
        
        percentage = (cv2.countNonZero(mask) / (roi.shape[0] * roi.shape[1])) * 100
        return percentage >= config.UNIFORM_PIXEL_PERCENTAGE_THRESHOLD, percentage