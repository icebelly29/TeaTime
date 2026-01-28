import cv2
import numpy as np
import config
import time

# Try importing RDK-specific libraries
try:
    from hobot_dnn import pyeasy_dnn
    RDK_AVAILABLE = True
except ImportError:
    RDK_AVAILABLE = False

class RDKDetector:
    def __init__(self, model_path=config.RDK_MODEL_PATH):
        if not RDK_AVAILABLE:
            raise ImportError("hobot_dnn library not found. Are you running on RDK X5?")
        
        print(f"[RDK] Loading BPU model from {model_path}...")
        self.models = pyeasy_dnn.load(model_path)
        self.h = config.RDK_MODEL_HEIGHT
        self.w = config.RDK_MODEL_WIDTH

    def bgr2nv12_opencv(self, image):
        """
        Converts BGR image to NV12 (YUV420 semi-planar) using OpenCV.
        Required for RDK X5 BPU input.
        """
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
        """
        Resize and convert to NV12.
        """
        # Resize to model input size
        resized = cv2.resize(img, (self.w, self.h))
        # Convert to NV12
        nv12_data = self.bgr2nv12_opencv(resized)
        return nv12_data

    def postprocess(self, outputs, src_h, src_w):
        """
        Parse FCOS/YOLO output from BPU.
        This is a SIMPLIFIED parser assuming standard FCOS 3-output structure.
        Real implementations might need adjustment based on specific model version.
        
        Returns: list of ((x1, y1, x2, y2), confidence)
        """
        # NOTE: This part often requires specific logic per model version.
        # Typically outputs[0] = box regression, outputs[1] = classification, etc.
        # For this demo, we assume the outputs are iterable and contain accessible tensors.
        
        preds = []
        
        # Accessing the output tensors (assuming numpy-like interface from pyeasy_dnn)
        # If this fails, the user needs to check the 'postprocess' example in RDK Model Zoo
        try:
            # Example logic: just taking the first valid output for demonstration
            # In reality, you need to decode strides and anchors here.
            # Since that code is 100+ lines, we will implement a basic "Pass-through"
            # or ask the user to provide the parsed boxes if using a complex model.
            
            # Placeholder for actual decoding logic
            pass 
        except Exception as e:
            print(f"[RDK] Post-processing error: {e}")

        # --- MOCK IMPLEMENTATION FOR DEMO IF REAL PARSING IS MISSING ---
        # Since we can't blindly decode unknown binary model outputs without the 
        # specific post-process script usually found in /app/py_dev/ params:
        # We will return an empty list and print a warning if this method is called 
        # without the specific decoding logic being pasted in.
        
        # To make this useful, we assume the user might replace this method
        # with the one from `fcos_post_process.py` in their RDK examples.
        return preds

    def detect_person(self, frame):
        """
        Main detection interface compatible with TeaDetector.
        """
        h, w = frame.shape[:2]
        nv12_data = self.preprocess(frame)
        
        t0 = time.time()
        outputs = self.models[0].forward(nv12_data)
        # print(f"[RDK] Inference time: {(time.time()-t0)*1000:.2f}ms")
        
        # ---------------------------------------------------------
        # CRITICAL: RDK X5 "Boxs" SDK usually provides a C++ post-process
        # or a Python utility. If you are using the standard 'mono2d_body' model,
        # you need the corresponding 'postprocess' function.
        # ---------------------------------------------------------
        
        # For the purpose of this script, we assume a `postprocess` utility 
        # is available or we return a placeholder. 
        # IF YOU HAVE THE "fcos_post_process.py" from RDK Model Zoo, import it here.
        
        # detections = custom_fcos_decoder(outputs, ... params ...)
        
        # FALLBACK: If we can't decode, we warn.
        # In a real deployment, you would paste the 'postprocess' code here.
        
        print("[RDK] Warning: Raw BPU output received. Post-processing logic required.")
        return [] # Returning empty to prevent crash, user needs to add decoder.
    
    def check_uniform_color(self, frame, bbox):
        # Reuse the logic from the original detector (it's pure OpenCV/NumPy)
        # We can implement it here or import it.
        # Simple copy-paste of logic for standalone nature:
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
