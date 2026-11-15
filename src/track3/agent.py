import json
import paho.mqtt.client as mqtt
 
# ตั้งค่า Broker และ Topic ให้ตรงกับฝั่งส่ง
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_MOISTURE = "hotcoffee/sensor/moisture"
TOPIC_VISION = "hotcoffee/vision/defects"
 
# กล่องสำหรับรวมข้อมูลจาก 2 ฝั่ง
current_lot_data = {
    "moisture_data": None,
    "vision_data": None
}
 
def process_agent_logic():
    """ฟังก์ชันที่จะถูกเรียกเมื่อได้ข้อมูลครบทั้ง 2 ฝั่งแล้ว"""
    moisture_info = current_lot_data["moisture_data"]
    vision_info = current_lot_data["vision_data"]
    print("\n==========================================")
    print(" [AGENT] ข้อมูลพร้อมสำหรับวิเคราะห์ราคาแล้ว!")
    print(f" - ข้อมูลจาก ESP32: ความชื้น {moisture_info['moisture']}% (Status: {moisture_info['status']})")
    print(f" - ข้อมูลจาก Pi 5: เมล็ดทั้งหมด {vision_info['total_beans']} เมล็ด")
    print(f"   * เมล็ดดี: {vision_info['summary']['good']}")
    print(f"   * เมล็ดเสีย: {vision_info['summary']['black']} ดำ, {vision_info['summary']['broken']} แตก")
    print("==========================================\n")
    # ตรงนี้คือจุดที่จะส่งข้อมูลต่อไปยัง LLM หรือสูตรตั้งราคา Bidding
    # เช่น: bid_price = calculate_bid(moisture_info, vision_info)
 
def on_connect(client, userdata, flags, rc, properties=None):
    """Callback เมื่อต่อ MQTT Brokerสำเร็จ"""
    if rc == 0:
        print("[MQTT] เชื่อมต่อ Brokerสำเร็จ! กำลัง Subscribe...")
        client.subscribe(TOPIC_MOISTURE)
        client.subscribe(TOPIC_VISION)
    else:
        print(f"[MQTT] เชื่อมต่อล้มเหลว Code: {rc}")
 
def on_message(client, userdata, msg):
    """Callback เมื่อมี Message ส่งเข้ามาใน Topic ที่ติดตาม"""
    try:
        # 1. แปลงข้อความที่ได้รับจาก Bytes เป็น String และ Decode JSON
        payload_str = msg.payload.decode("utf-8")
        data = json.loads(payload_str)
        # 2. แยกประมวลผลตาม Topic ที่รับเข้ามา
        if msg.topic == TOPIC_MOISTURE:
            print(f"[RECV - ESP32] {data}")
            current_lot_data["moisture_data"] = data
        elif msg.topic == TOPIC_VISION:
            print(f"[RECV - Pi 5 ] {data}")
            current_lot_data["vision_data"] = data
        # 3. ตรวจสอบว่าได้รับข้อมูลครบทั้ง 2 ฝั่งหรือยัง
        if current_lot_data["moisture_data"] is not None and current_lot_data["vision_data"] is not None:
            process_agent_logic()
            # ล้างค่าในกล่องเพื่อรอรับข้อมูลรอบ/ล็อตถัดไป (Optional)
            current_lot_data["moisture_data"] = None
            current_lot_data["vision_data"] = None
 
    except json.JSONDecodeError:
        print(f"[ERROR] ไม่สามารถแปลง JSON ได้: {msg.payload}")
    except Exception as e:
        print(f"[ERROR] เกิดข้อผิดพลาด: {e}")
 
# ==========================================
# เริ่มต้นการทำงานของ Subscriber
# ==========================================
if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
 
    print("[AGENT] กำลังเชื่อมต่อ MQTT Broker...")
    client.connect(BROKER, PORT, 60)
    # รัน Loop ค้างไว้เพื่อเฝ้ารับข้อมูลตลอดเวลา
    client.loop_forever()