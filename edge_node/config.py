# config.py

# Time Windows (IST)
# Format: (Start Hour, Start Minute, End Hour, End Minute)
# 10:00 AM to 12:00 PM
# 2:30 PM to 4:00 PM (14:30 to 16:00)
TIME_WINDOWS = [
    (10, 0, 12, 0),
    (14, 30, 16, 0)
]

# HSV Color Ranges for Purple/Violet Uniform
# Initial suggested range: Hue 125-155, Saturation 50-255, Value 50-255
# OpenCV HSV ranges: H: 0-179, S: 0-255, V: 0-255
# Mapping 360 degree hue to 180: 125/2 ~ 62 (This seems low for purple, usually purple is around 270-300 degrees)
# Let's re-evaluate standard purple HSV in OpenCV.
# Purple is around 270-300 degrees on a 360 circle.
# In OpenCV, pinks/magentas are in the 160-175 hue range, and purples are 130-150.
# This new range is narrowed and shifted to target reddish-purples and deep pinks.
# The minimum Saturation and Value are also increased to filter out dull/dark colors.
UNIFORM_HSV_LOWER = (135, 80, 70)
UNIFORM_HSV_UPPER = (165, 255, 255)

# Thresholds
UNIFORM_PIXEL_PERCENTAGE_THRESHOLD = 25.0  # Percentage (25-30%)
CONFIDENCE_THRESHOLD = 0.6 # Person detection confidence

# Cooldown
COOLDOWN_SECONDS = 15 * 60  # 15 minutes

# Network
IOT_NODE_IP = "192.168.137.251" # Placeholder IP, to be configured
IOT_NODE_PORT = 80
ALERT_ENDPOINT = "/alert"

# RDK X5 Specific Config
USE_RDK_BPU = True  # Set to True to attempt using hardware acceleration
RDK_MODEL_PATH = "/opt/hobot/model/x5/basic/fcos_512x512_nv12.bin" # Standard path example
RDK_MODEL_WIDTH = 512
RDK_MODEL_HEIGHT = 512

# Video source: integer for camera index (e.g., 0) or string for video file path
VIDEO_SOURCE = 0

# ROS2 Topics
ROS_IMAGE_TOPIC = "/image"
ROS_DETECTION_TOPIC = "/hobot_mono2d_body_detection"

