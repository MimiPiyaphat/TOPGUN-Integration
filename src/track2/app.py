import time
import json
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "hotcoffee/vision/defects"

# ตั้งค่า MQTT Client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(BROKER, PORT, 60)

# ==========================================
# ส่วนของการสร้างและส่ง PAYLOAD
# ==========================================
def send_vision_payload():
    # 1. ข้อมูลผลลัพธ์ที่ได้จากการรัน Inference โมเดล AI (ตัวอย่าง 7 คลาส)
    # Good, Full Black, Broken, Shell, Parchment, Hull, Immature
    vision_results = {
        "device_id": "rpi5_vision_01",
        "timestamp": int(time.time()),
        "total_beans": 50,
        "summary": {
            "good": 40,
            "black": 4,
            "broken": 3,
            "shell": 1,
            "parchment": 1,
            "hull": 1,
            "immature": 0
        }
    }
    
    # 2. แปลงโครงสร้าง Dictionary เป็น JSON String Payload
    payload = json.dumps(vision_results)
    
    # 3. สั่ง Publish Payload ออกไป
    client.publish(TOPIC, payload)
    
    print(f"Sent Pi5 Payload: {payload}")

print("Raspberry Pi 5 Vision Node Running...")

try:
    while True:
        send_vision_payload()
        time.sleep(5)  # ส่งทุกๆ 5 วินาที
except KeyboardInterrupt:
    client.disconnect()
    print("Stopped.")
