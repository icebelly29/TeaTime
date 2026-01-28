# TeaTime: AIoT Tea Service Detection System

A context-aware AIoT system designed to detect the arrival of tea or coffee service staff in an office environment and send real-time alerts to a local display.

## System Architecture

The system operates entirely on the local network (no cloud) and consists of two main nodes:

1.  **Edge AI Node (RDK X5 / PC):** 
    *   **Hardware:** RDK X5 (Horizon Robotics) or any Linux-based edge device/PC with a camera.
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
*   Pre-trained MobileNet SSD model files (see setup).

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

1.  Navigate to `edge_node/`.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Download Model Files:**
    Download the standard MobileNet SSD pre-trained model files and place them in the `edge_node/` directory:
    *   `MobileNetSSD_deploy.prototxt`
    *   `MobileNetSSD_deploy.caffemodel`
    *(These are widely available open-source models).*
4.  Update Configuration:
    Open `config.py` and update `IOT_NODE_IP` with the IP address of your TTGO T-Display obtained in step 1.
5.  Run the detector:
    ```bash
    python main.py
    ```

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
