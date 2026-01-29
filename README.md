# TeaTime: AIoT Tea Service Detection System

A context-aware AIoT system designed to detect the arrival of tea or coffee service staff in an office environment and send real-time alerts to a local display.

<img src="https://github.com/user-attachments/assets/106e16a0-7f0e-4d40-ba3b-7dba7ee0bef5" alt="Sample Image" style="width:35%; height:auto;">

## System Architecture

The system operates entirely on the local network (no cloud) and consists of two main nodes:

1.  **Edge AI Node (RDK X5):** 
    *   **Hardware:** RDK X5 (D Robotics) or any Linux-based edge device with a camera.
    *   **Software:** Python, OpenCV (DNN module).
    *   **Logic:** Detects persons -> Checks for purple uniform (HSV Color Space) -> Checks Time Window (IST) -> Sends HTTP Alert.
2.  **IoT Alert Node (TTGO T-Display):**
    *   **Hardware:** TTGO T-Display (ESP32).
    *   **Software:** C++, PlatformIO, Arduino framework.
    *   **Logic:** Connects to WiFi -> Runs HTTP Server -> Receives Alert -> Displays Notification.

## Prerequisites

### Edge Node
*   Python 3.6+
*   A USB Camera or MIPI Camera.

### IoT Node
*   PlatformIO (VSCode Extension or CLI).
*   TTGO T-Display hardware.

## Setup Instructions

### 1. IoT Node (Display)

1.  Navigate to `iot_node/`.
2.  Open `src/main.cpp` and update `ssid` and `password` with your local WiFi credentials.
3.  Connect the TTGO T-Display via USB.
4.  Build and upload the firmware:
    ```bash
    pio run -t upload
    ```
5.  Open the serial monitor (`pio device monitor`) to note the **IP Address** assigned to the device (e.g., `192.168.1.100`).

### 2. Edge Node (AI Camera)

This section describes how to set up the Edge Node for object detection using ROS2. The process involves launching a ROS2 publisher in one terminal and running a Python subscriber script (`main.py`) in another.

1.  Navigate to `edge_node/`.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  **ROS2 Publisher Setup (Terminal 1):**
    First, you need to set up the ROS2 environment and launch the `mono2d_body_detection` publisher.
    ```bash
    source /opt/tros/humble/setup.bash
    cp -r /opt/tros/humble/lib/mono2d_body_detection/config/ .
    export CAM_TYPE=mipi
    ros2 launch mono2d_body_detection mono2d_body_detection.launch.py
    ```
    *Note: Ensure `/opt/tros/humble/setup.bash` and the `mono2d_body_detection` package are correctly installed and sourced.*

4.  **ROS2 Subscriber (Terminal 2):**
    After the publisher is running, open a new terminal in the `edge_node/` directory and run the `main.py` script, which acts as the subscriber to the detected body information.
    ```bash
    python main.py
    ```
5.  Update Configuration:
    Open `config.py` and update `IOT_NODE_IP` with the IP address of your TTGO T-Display obtained in step 1 of the IoT Node setup.

### RDK X5 Hardware Acceleration (Optional)

If you are running on the **RDK X5**, the system can use the BPU for faster inference.
1.  Ensure `hobot_dnn` is available (standard on RDK images).
2.  Update `edge_node/config.py`:
    *   Set `USE_RDK_BPU = True`.
    *   Set `RDK_MODEL_PATH` to the path of your `.bin` model (e.g., `/app/model/fcos_512x512_nv12.bin`).
3.  **Note:** You may need to provide the specific FCOS post-processing logic in `rdk_adapter.py` depending on your model version.

## Logic Details

*   **Time Windows:** 10:00-12:00 and 14:30-16:00 (IST). Detections outside these times are ignored.
*   **Uniform Detection:** Extracts the upper body of a detected person and calculates the percentage of purple pixels (HSV range defined in `config.py`).
*   **Cooldown:** After a valid alert, the system ignores further detections for 15 minutes.

## Troubleshooting

*   **No Alerts?** Check if the current time is within the defined windows in `config.py`.
*   **False Negatives?** Adjust `UNIFORM_HSV_LOWER` and `UNIFORM_HSV_UPPER` in `config.py` to match the specific shade of the uniform under your lighting conditions.
*   **Connection Error?** Ensure both devices are on the same WiFi network and the IP in `config.py` matches the IoT Node's IP.
