#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>
#include <SPI.h>

// --- Configuration ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

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

// --- Display Functions ---

void drawIdleScreen() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  
  // Title
  tft.setTextDatum(MC_DATUM); // Middle Center
  tft.setTextSize(2);
  tft.drawString("TeaTime Monitor", tft.width() / 2, 30);
  
  // Status
  tft.setTextSize(1);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.drawString("STATUS: ACTIVE", tft.width() / 2, 60);
  
  // Windows
  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.drawString("Monitoring Windows:", tft.width() / 2, 100);
  
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.drawString(timeWindow1, tft.width() / 2, 120);
  tft.drawString(timeWindow2, tft.width() / 2, 140);
  
  // IP Address
  tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
  tft.drawString(WiFi.localIP().toString(), tft.width() / 2, 220);
}

void drawAlertScreen(String timestamp) {
  tft.fillScreen(TFT_PURPLE); // Background color for alert
  
  tft.setTextColor(TFT_WHITE, TFT_PURPLE);
  tft.setTextDatum(MC_DATUM);
  
  tft.setTextSize(3);
  tft.drawString("TEA / COFFEE", tft.width() / 2, 60);
  tft.drawString("ARRIVED!", tft.width() / 2, 100);
  
  tft.setTextSize(2);
  // Parse timestamp to just HH:MM if possible, otherwise show raw
  // Expected ISO: YYYY-MM-DDTHH:MM:SS.mmmm
  String timePart = timestamp;
  int tIndex = timestamp.indexOf('T');
  if (tIndex > 0) {
      timePart = timestamp.substring(tIndex + 1, tIndex + 6); // HH:MM
  }
  
  tft.drawString(timePart, tft.width() / 2, 160);
  
  // Flash effect
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
    Serial.print("deserializeJson() failed: ");
    Serial.println(error.c_str());
    server.send(400, "text/plain", "Invalid JSON");
    return;
  }

  const char* event = doc["event"];
  const char* timestamp = doc["timestamp"];
  
  if (event && strcmp(event, "tea_service_detected") == 0) {
    Serial.println("Alert Received!");
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
  
  // Display Init
  tft.init();
  tft.setRotation(0); // Portrait
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextDatum(MC_DATUM);
  tft.drawString("Connecting...", tft.width()/2, tft.height()/2);

  // WiFi Init
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected.");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  // Server Init
  server.on("/", handleRoot);
  server.on("/alert", handleAlert);
  server.begin();
  Serial.println("HTTP server started");

  drawIdleScreen();
}

void loop() {
  server.handleClient();
  
  // Check if we should revert to idle screen after alert duration
  if (alertActive && (millis() - alertReceivedMillis > ALERT_DISPLAY_DURATION)) {
    alertActive = false;
    drawIdleScreen();
  }
}
