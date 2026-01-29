#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>
#include <SPI.h>
#include <time.h>

// --- Configuration ---
const char* ssid = "SNORLAX";
const char* password = "Helloworld";

// Time Configuration (IST = UTC + 5:30)
const long  gmtOffset_sec = 19800;
const int   daylightOffset_sec = 0;
const char* ntpServer = "pool.ntp.org";

// Time Windows for Display (Static Text)
const char* timeWindow1 = "10:00 - 12:00";
const char* timeWindow2 = "14:30 - 16:00";

// --- Globals ---
WebServer server(80);
TFT_eSPI tft = TFT_eSPI(); 

bool alertActive = false;
String lastAlertTime = "";
unsigned long alertReceivedMillis = 0;
const unsigned long ALERT_DISPLAY_DURATION = 60000; // Keep alert on screen for 60s
int lastMinute = -1;

// --- Helper Functions ---

void getLocalTimeParts(String &hh, String &mm) {
  struct tm timeinfo;
  if(!getLocalTime(&timeinfo)){
    hh = "--";
    mm = "--";
    return;
  }
  char hBuff[3], mBuff[3];
  strftime(hBuff, sizeof(hBuff), "%H", &timeinfo);
  strftime(mBuff, sizeof(mBuff), "%M", &timeinfo);
  hh = String(hBuff);
  mm = String(mBuff);
}

// --- Display Functions ---

void drawIdleScreen() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(MC_DATUM); 
  
  // 1. Title (TeaTime)
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.drawString("TeaTime", tft.width() / 2, 20);
  
  // 2. Status
  tft.setTextSize(1);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.drawString("STATUS: ACTIVE", tft.width() / 2, 40);
  
  // 3. Vertical Clock (HH above MM)
  String hh, mm;
  getLocalTimeParts(hh, mm);
  
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.setTextSize(6); // Large font for HH
  tft.drawString(hh, tft.width() / 2, 80);
  
  tft.setTextColor(TFT_WHITE, TFT_BLACK); // Minute in white for contrast
  tft.drawString(mm, tft.width() / 2, 130);
  
  // 4. Monitoring Windows
  tft.setTextSize(1);
  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.drawString("Monitoring Windows:", tft.width() / 2, 170);
  
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.drawString(timeWindow1, tft.width() / 2, 185);
  tft.drawString(timeWindow2, tft.width() / 2, 200);
  
  // 5. IP Address
  tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
  tft.drawString(WiFi.localIP().toString(), tft.width() / 2, 225);
}

void drawAlertScreen(String timestamp) {
  tft.fillScreen(TFT_PURPLE); 
  
  tft.setTextColor(TFT_WHITE, TFT_PURPLE);
  tft.setTextDatum(MC_DATUM);
  
  tft.setTextSize(3);
  tft.drawString("TEA", tft.width() / 2, 60);
  tft.drawString("ARRIVED!", tft.width() / 2, 100);
  
  tft.setTextSize(2);
  String timePart = timestamp;
  int tIndex = timestamp.indexOf('T');
  if (tIndex > 0) {
      timePart = timestamp.substring(tIndex + 1, tIndex + 6); // HH:MM
  }
  
  tft.drawString(timePart, tft.width() / 2, 160);
  
  for(int i=0; i<3; i++) {
    tft.invertDisplay(true);
    delay(100);
    tft.invertDisplay(false);
    delay(100);
  }
}

// --- Server Handlers ---

void handleRoot() {
  server.send(200, "text/plain", "TeaTime IoT Node Online");
}

void handleAlert() {
  if (server.method() != HTTP_POST) {
    server.send(405, "text/plain", "Method Not Allowed");
    return;
  }

  String body = server.arg("plain");
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, body);

  if (error) {
    server.send(400, "text/plain", "Invalid JSON");
    return;
  }

  const char* event = doc["event"];
  const char* timestamp = doc["timestamp"];
  
  if (event && strcmp(event, "tea_service_detected") == 0) {
    alertActive = true;
    lastAlertTime = String(timestamp);
    alertReceivedMillis = millis();
    drawAlertScreen(lastAlertTime);
    server.send(200, "text/plain", "Alert Received");
  } else {
    server.send(400, "text/plain", "Unknown Event");
  }
}

// --- Setup & Loop ---

void setup() {
  Serial.begin(115200);
  tft.init();
  tft.setRotation(0); 
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextDatum(MC_DATUM);
  tft.drawString("Connecting...", tft.width()/2, tft.height()/2);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);

  server.on("/", handleRoot);
  server.on("/alert", handleAlert);
  server.begin();

  drawIdleScreen();
}

void loop() {
  server.handleClient();
  
  if (alertActive) {
    if (millis() - alertReceivedMillis > ALERT_DISPLAY_DURATION) {
      alertActive = false;
      lastMinute = -1; 
      drawIdleScreen();
    }
  } else {
    struct tm timeinfo;
    if(getLocalTime(&timeinfo)){
      if(timeinfo.tm_min != lastMinute) {
        lastMinute = timeinfo.tm_min;
        drawIdleScreen();
      }
    }
  }
}
