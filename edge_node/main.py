import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage # Import the correct message type
from ai_msgs.msg import PerceptionTargets
from cv_bridge import CvBridge
import cv2
import time
import datetime
import requests
import config
from detector import TeaDetector
import sys

class TeaTimeNode(Node):
    def __init__(self):
        super().__init__('tea_time_node')
        self.get_logger().info("[INFO] Starting TeaTime Edge Node (ROS2)...")

        # Initialize Detector (we only need it for check_uniform_color)
        self.detector = TeaDetector()
        self.get_logger().info("[INFO] Loaded color checker from TeaDetector.")

        # Initialize CV Bridge and state
        self.bridge = CvBridge()
        self.latest_frame = None
        self.last_alert_time = 0

        # Subscriber for the Image stream
        self.image_subscription = self.create_subscription(
            CompressedImage,
            config.ROS_IMAGE_TOPIC,
            self.frame_callback,
            10) # QoS profile depth
        self.get_logger().info(f"[INFO] Subscribed to Image stream on topic: {config.ROS_IMAGE_TOPIC}")

        # Subscriber for the Detection results
        self.detection_subscription = self.create_subscription(
            PerceptionTargets,
            config.ROS_DETECTION_TOPIC,
            self.detection_callback,
            10)
        self.get_logger().info(f"[INFO] Subscribed to PerceptionTargets on topic: {config.ROS_DETECTION_TOPIC}")


    def is_time_in_window(self):
        """Checks if current time is within the configured windows."""
        now = datetime.datetime.now()
        current_minutes = now.hour * 60 + now.minute
        for (start_h, start_m, end_h, end_m) in config.TIME_WINDOWS:
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            if start_minutes <= current_minutes <= end_minutes:
                return True
        return False

    def send_alert(self, confidence):
        """Sends an HTTP POST alert to the IoT Node."""
        url = f"http://{config.IOT_NODE_IP}:{config.IOT_NODE_PORT}{config.ALERT_ENDPOINT}"
        payload = {
            "event": "tea_service_detected",
            "confidence": confidence,
            "timestamp": datetime.datetime.now().isoformat()
        }
        try:
            self.get_logger().info(f"[INFO] Sending alert to {url}...")
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                self.get_logger().info("[INFO] Alert sent successfully.")
            else:
                self.get_logger().warn(f"[WARN] Alert sent but server returned {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.get_logger().error(f"[ERROR] Failed to send alert: {e}")

    def frame_callback(self, msg):
        """Callback to store the latest image frame."""
        try:
            self.latest_frame = self.bridge.compressed_imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f"Failed to convert image: {e}")

    def detection_callback(self, msg):
        """Callback function for processing detection results."""
        # 1. Ensure we have a frame to process
        if self.latest_frame is None:
            self.get_logger().info("[STATUS] Waiting for image frame...")
            return
            
        # Create a copy of the frame to draw on
        frame_with_boxes = self.latest_frame.copy()

        # 2. Time Check
        if not self.is_time_in_window():
            cv2.imshow("Live Feed", frame_with_boxes)
            cv2.waitKey(1)
            return

        # 3. Cooldown Check
        if time.time() - self.last_alert_time < config.COOLDOWN_SECONDS:
            cv2.imshow("Live Feed", frame_with_boxes)
            cv2.waitKey(1)
            return

        detected_tea_staff = False
        
        # 4. Process Detections from the message
        for target in msg.targets:
            if target.type == 'person':
                # Find the bounding box for the body
                for roi in target.rois:
                    if roi.type == 'body':
                        # Extract bounding box
                        r = roi.rect
                        # Convert from (x_offset, y_offset, width, height) to (startX, startY, endX, endY)
                        bbox = (r.x_offset, r.y_offset, r.x_offset + r.width, r.y_offset + r.height)
                        
                        # Draw bounding box on the frame
                        cv2.rectangle(frame_with_boxes, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)

                        # We have a person, now check their uniform color
                        is_uniform, percent, mask = self.detector.check_uniform_color(self.latest_frame, bbox)
                        
                        # Show the color mask for debugging
                        if mask is not None:
                            cv2.imshow("Color Mask", mask)

                        if is_uniform:
                            # Bypassing confidence from message as it's 0.0
                            best_confidence = 1.0 
                            self.get_logger().info(f"\n[DETECT] Potential Tea Staff detected! Purple %: {percent:.2f}%")
                            detected_tea_staff = True
                            break # Trigger on first valid detection
                
                if detected_tea_staff:
                    break
        
        # Show the live feed with boxes
        cv2.imshow("Live Feed", frame_with_boxes)
        cv2.waitKey(1)

        # 5. Trigger Alert
        if detected_tea_staff:
            self.send_alert(float(best_confidence))
            self.last_alert_time = time.time()
            self.get_logger().info(f"[INFO] Cooldown started for {config.COOLDOWN_SECONDS} seconds.")


def main(args=None):
    rclpy.init(args=args)
    tea_time_node = TeaTimeNode()
    try:
        rclpy.spin(tea_time_node)
    except KeyboardInterrupt:
        print("\n[INFO] Stopping...")
    finally:
        cv2.destroyAllWindows()
        tea_time_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()