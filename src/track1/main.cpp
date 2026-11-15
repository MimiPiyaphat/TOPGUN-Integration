#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h> // สำหรับแพ็กข้อมูล JSON

const char *ssid = "Nonolee";
const char *password = "pwqi5723";
const char *mqtt_server = "broker.hivemq.com";
const char *topic = "hotcoffee/sensor/moisture";

WiFiClient espClient;

PubSubClient client(espClient);

void setup()
{
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
  }
  client.setServer(mqtt_server, 1883);
}

// ==========================================
// ส่วนของการสร้างและส่ง PAYLOAD
// ==========================================

void sendMoisturePayload()
{
  // 1. อ่านค่าจากเซนเซอร์จริง (ตัวอย่างเช่น อ่านได้ 12.50%)
  float sensor_moisture = 12.50;

  // 2. สร้างโครงสร้าง JSON
  StaticJsonDocument<200> doc;
  doc["device_id"] = "esp32_sensor_01";
  doc["moisture"] = sensor_moisture;
  doc["status"] = "OK";

  // 3. แปลง JSON Document ให้เป็น String Payload
  char payloadBuffer[200];
  serializeJson(doc, payloadBuffer);

  // 4. สั่ง Publish Payload ออกไป
  client.publish(topic, payloadBuffer);
  Serial.print("Sent ESP32 Payload: ");
  Serial.println(payloadBuffer);
}

void loop()
{
  if (!client.connected())
  {
    while (!client.connected())
    {
      if (client.connect("ESP32_Client"))
      {
        Serial.println("MQTT Connected!");
      }
      else
      {
        delay(2000);
      }
    }
  }

  client.loop();
  // เรียกฟังก์ชันส่ง Payload ทุกๆ 5 วินาที
  sendMoisturePayload();
  delay(5000);
}
