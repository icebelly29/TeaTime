import cv2
import time
import datetime
import requests
import config
from detector import TeaDetector
import sys

def is_time_in_window():
    """
    Checks if current IST time is within the configured windows.
    """
    # Get current time in local timezone (assuming system is set to IST or handled correctly)
    # Ideally, we should explicitly handle timezone if system time isn't IST.
    # For this demo, we assume the system clock is correct (IST).
    now = datetime.datetime.now()
    current_minutes = now.hour * 60 + now.minute
    
    for (start_h, start_m, end_h, end_m) in config.TIME_WINDOWS:
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        
        if start_minutes <= current_minutes <= end_minutes:
            return True
            
    return False

def send_alert(confidence):
    """
    Sends an HTTP POST alert to the IoT Node.
    """
    url = f"http://{config.IOT_NODE_IP}:{config.IOT_NODE_PORT}{config.ALERT_ENDPOINT}"
    payload = {
        "event": "tea_service_detected",
        "confidence": confidence,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    try:
        print(f"[INFO] Sending alert to {url}...")
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print("[INFO] Alert sent successfully.")
        else:
            print(f"[WARN] Alert sent but server returned {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to send alert: {e}")

def main():
    print("[INFO] Starting TeaTime Edge Node...")
    
    # Initialize Detector
    detector = None
    
    # Try RDK BPU First
    if config.USE_RDK_BPU:
        try:
            from rdk_adapter import RDKDetector
            print("[INFO] Attempting to load RDK BPU Detector...")
            detector = RDKDetector()
            print("[INFO] RDK BPU Detector loaded successfully.")
        except ImportError:
            print("[WARN] RDK libraries not found. Falling back to OpenCV CPU.")
        except Exception as e:
            print(f"[WARN] Failed to load RDK BPU: {e}. Falling back to OpenCV CPU.")

    # Fallback to OpenCV
    if detector is None:
        try:
            # Note: Provide actual paths to model files if they exist, or rely on defaults
            detector = TeaDetector()
            print("[INFO] MobileNetSSD (CPU) loaded successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            print("[TIP] Ensure 'MobileNetSSD_deploy.prototxt' and 'MobileNetSSD_deploy.caffemodel' are in the directory.")
            sys.exit(1)

    # Initialize Camera
    # On RDK X5 (Linux), this might be /dev/video0 or a specific MIPI camera index.
    cap = cv2.VideoCapture(0) 
    if not cap.isOpened():
        print("[ERROR] Could not open video device.")
        sys.exit(1)

    last_alert_time = 0
    
    try:
        while True:
            # 1. Time Check
            if not is_time_in_window():
                # print("[STATUS] Outside active hours. Monitoring paused.", end='\r')
                time.sleep(60) # Sleep for a minute to save resources
                continue

            # 2. Cooldown Check
            if time.time() - last_alert_time < config.COOLDOWN_SECONDS:
                remaining = int(config.COOLDOWN_SECONDS - (time.time() - last_alert_time))
                print(f"[STATUS] Cooldown active. {remaining}s remaining.", end='\r')
                time.sleep(1)
                continue

            # 3. Capture Frame
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Failed to read frame.")
                break

            # 4. Detect Person
            detections = detector.detect_person(frame)
            
            detected_tea_staff = False
            best_confidence = 0.0
            
            for (bbox, confidence) in detections:
                # 5. Check Uniform
                is_uniform, percent = detector.check_uniform_color(frame, bbox)
                
                if is_uniform:
                    print(f"\n[DETECT] Potential Tea Staff detected! Confidence: {confidence:.2f}, Purple %: {percent:.2f}%")
                    detected_tea_staff = True
                    best_confidence = confidence
                    
                    # Draw for debug (optional, can be removed for headless)
                    (startX, startY, endX, endY) = bbox
                    cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
                    cv2.putText(frame, f"Staff: {percent:.1f}%", (startX, startY - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    break # Trigger on first valid detection

            # 6. Trigger Alert
            if detected_tea_staff:
                send_alert(float(best_confidence))
                last_alert_time = time.time()
                print(f"[INFO] Cooldown started for {config.COOLDOWN_SECONDS} seconds.")

            # Optional: Display frame (for debugging on connected monitor)
            # cv2.imshow("TeaTime Monitor", frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #    break
            
            # Rate limit main loop slightly
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[INFO] Stopping...")
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
