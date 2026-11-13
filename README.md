# ☕ Smart Robusta Coffee
### แพลตฟอร์ม AIoT สำหรับประเมินคุณภาพและซื้อขายกาแฟโรบัสต้าจังหวัดชุมพร

โครงการพัฒนาแพลตฟอร์ม **AIoT (Artificial Intelligence of Things)** เพื่อประเมินคุณภาพเมล็ดกาแฟโรบัสต้า โดยผสานเทคโนโลยีระบบสมองกลฝังตัว ปัญญาประดิษฐ์ด้านภาพ และ AI Agent เข้าด้วยกัน เพื่อสนับสนุนการตรวจสอบคุณภาพและการซื้อขายกาแฟในตลาดจำลอง

โครงการนี้เป็นส่วนหนึ่งของการแข่งขัน **TESA Top Gun Rally #20**

---

## 1. ที่มาและความสำคัญ

กาแฟโรบัสต้าจังหวัดชุมพรเป็นผลิตภัณฑ์ทางการเกษตรที่มีความสำคัญต่อเกษตรกรในพื้นที่ อย่างไรก็ตาม คุณภาพของเมล็ดกาแฟอาจแตกต่างกันตามความชื้น กระบวนการผลิต และลักษณะของเมล็ดกาแฟที่มีข้อบกพร่อง

โครงการนี้จึงนำเทคโนโลยี AIoT มาประยุกต์ใช้ในการตรวจวัดความชื้น วิเคราะห์ลักษณะของเมล็ดกาแฟ และนำข้อมูลไปใช้ประกอบการตัดสินใจซื้อขายผ่าน AI Agent

## 2. วัตถุประสงค์

- พัฒนาระบบตรวจวัดความชื้นของเมล็ดกาแฟด้วย ESP32 และเซนเซอร์
- ใช้ Computer Vision ในการจำแนกประเภทและตรวจจับข้อบกพร่องของเมล็ดกาแฟ
- นำโมเดลปัญญาประดิษฐ์ไปประมวลผลบน Raspberry Pi 5
- พัฒนา AI Agent สำหรับวิเคราะห์ข้อมูลและตัดสินใจซื้อขายกาแฟ
- เชื่อมโยงการทำงานของระบบทั้งหมดเข้าด้วยกัน

## 3. ภาพรวมของระบบ

ระบบแบ่งออกเป็น 3 ส่วนหลัก ได้แก่

### Track 1: Embedded System

พัฒนาระบบตรวจวัดความชื้นของเมล็ดกาแฟ โดยใช้ ESP32 เชื่อมต่อกับเซนเซอร์ เพื่ออ่านค่าและเตรียมข้อมูลสำหรับนำไปใช้งานในระบบ

### Track 2: Vision AI

พัฒนาระบบ Computer Vision สำหรับวิเคราะห์ภาพเมล็ดกาแฟ โดยแบ่งการทำงานออกเป็น

- Classification: จำแนกประเภทของเมล็ดกาแฟ
- Object Detection: ตรวจจับตำแหน่งของเมล็ดกาแฟ
- Segmentation: แบ่งส่วนพื้นที่ของเมล็ดกาแฟในภาพ

ประเภทของเมล็ดกาแฟที่ใช้ในการจำแนกมี 7 ประเภท ได้แก่

1. Good – เมล็ดกาแฟปกติ
2. Shell – เมล็ดกาแฟลักษณะเปลือก
3. Full Black – เมล็ดกาแฟดำทั้งเมล็ด
4. Hull / Husk – เปลือกกาแฟ
5. Broken / Chipped / Cut – เมล็ดกาแฟแตกหรือบิ่น
6. Parchment / Pergamino – เมล็ดกาแฟที่ยังมีเยื่อกะลา
7. Immature / Unripe – เมล็ดกาแฟที่ยังไม่สุกเต็มที่

### Track 3: AI Agent

พัฒนา AI Agent เพื่อทำงานร่วมกับระบบตลาดซื้อขายกาแฟ โดยสามารถรับข้อมูลตลาด วิเคราะห์สถานการณ์ และตัดสินใจดำเนินการซื้อขายตามกลยุทธ์ที่พัฒนาขึ้น

## 4. ลำดับการทำงานของระบบ (System Workflow)

1. ESP32 อ่านค่าความชื้นจากเซนเซอร์
2. กล้องบันทึกภาพเมล็ดกาแฟ
3. Vision AI วิเคราะห์และจำแนกประเภทเมล็ดกาแฟ
4. Raspberry Pi 5 ประมวลผลโมเดล Vision AI
5. จัดเตรียมข้อมูลที่เกี่ยวข้องกับล็อตกาแฟ
6. AI Agent วิเคราะห์ข้อมูลตลาดและตัดสินใจซื้อขาย

*หมายเหตุ: การเชื่อมต่อและการส่งข้อมูลระหว่างแต่ละส่วนจะดำเนินการตามข้อกำหนดของการแข่งขัน*

## 5. เทคโนโลยีและเครื่องมือที่ใช้ (Technologies & Tools)

| เทคโนโลยี | การใช้งาน |
|---|---|
| ESP32 | ควบคุมและอ่านค่าจากเซนเซอร์ |
| Moisture Sensor | ตรวจวัดความชื้น |
| Python | พัฒนาโปรแกรมและระบบ AI |
| Computer Vision | วิเคราะห์ภาพเมล็ดกาแฟ |
| Raspberry Pi 5 | ประมวลผล AI บนอุปกรณ์ Edge |
| AI Agent | วิเคราะห์และตัดสินใจซื้อขาย |
| REST API | ติดต่อสื่อสารกับระบบตลาด |
| GitHub | จัดเก็บและจัดการซอร์สโค้ด |

## 6. โครงสร้างโปรเจกต์ (Project Structure)

```text
TOPGUN-Integration/
│
├── README.md
├── .gitignore
│
├── docs/
│   ├── project-plan.md
│   ├── team-responsibilities.md
│   ├── system-architecture.md
│   └── data-contract.md
│
└── src/
    ├── track1_esp32/
    ├── track2_vision/
    ├── track2_raspberry_pi/
    ├── track3_agent/
    └── integration/
```

*หมายเหตุ: โครงสร้างในส่วน `docs/` และโฟลเดอร์ย่อยภายใน `src/` เป็นโครงสร้างที่เสนอให้จัดเตรียม อาจปรับเปลี่ยนได้ตามการพัฒนาจริง*

## 7. สมาชิกและหน้าที่รับผิดชอบ (Team Members)

| สมาชิก | หน้าที่รับผิดชอบ |
|---|---|
| Mi | Project Manager และ Vision AI |
| Q | Raspberry Pi 5 และ Edge AI |
| Cyn | Embedded System และ ESP32 |
| Bonus | AI Agent |
| One | Market API และกลยุทธ์การซื้อขาย |

## 8. การจัดการโปรเจกต์ (Project Management)

ใช้ GitHub เป็นพื้นที่กลางสำหรับจัดเก็บซอร์สโค้ด เอกสาร และติดตามความคืบหน้าของการพัฒนา โดยแบ่งงานตาม Track และหน้าที่ของสมาชิกแต่ละคน

เอกสารประกอบโครงการจะจัดเก็บไว้ในโฟลเดอร์ `docs/` เพื่อให้สมาชิกสามารถศึกษาและติดตามรายละเอียดได้จากแหล่งข้อมูลเดียวกัน

## 9. ข้อตกลงข้อมูลกลาง (Integration Data Contract)

ทุก Track ต้องใช้ Data Contract นี้ร่วมกัน เพื่อป้องกันการนำค่าความชื้นและผล Vision จากคนละล็อตมาจับคู่กัน

### 9.1 ผู้รับผิดชอบและลำดับการทำงาน

1. **Q / Raspberry Pi** สร้าง `lot_id` ใหม่ก่อนเริ่มตรวจแต่ละล็อต และประกาศไปยัง MQTT control topic
2. **Cyn / ESP32** แนบ `lot_id` ดังกล่าวกับผลวัดความชื้น
3. **Mi / Vision AI และ Q / Raspberry Pi** แนบ `lot_id` เดียวกันกับผล Vision
4. **Bonus / AI Agent** รวมข้อมูลด้วย `lot_id` เท่านั้น ห้ามจับคู่ด้วยลำดับเวลาหรือข้อความล่าสุด
5. **One / Market API** รับเฉพาะ `lot.assessment` ที่ผ่านการตรวจสอบแล้วไปใช้กับกลยุทธ์ตลาด

ระหว่างพัฒนาที่ยังไม่มี control service สามารถกำหนด `lot_id` เดียวกันด้วยตนเองทั้ง ESP32 และ Raspberry Pi เพื่อทดสอบได้

### 9.2 MQTT Topics

ให้แทน `<team-id>` ด้วยชื่อทีมที่ตกลงร่วมกัน และใช้ชื่อเดียวกันทุกอุปกรณ์

```text
tgr2026/<team-id>/v1/control/current-lot
tgr2026/<team-id>/v1/moisture
tgr2026/<team-id>/v1/vision
tgr2026/<team-id>/v1/assessment
```

การใส่ `<team-id>` และ `v1` ช่วยป้องกัน topic ชนกับทีมอื่นบน public broker และรองรับการเปลี่ยน schema ในอนาคต

### 9.3 Common Envelope

ทุกข้อความต้องมี field ส่วนกลางต่อไปนี้

| Field | Type | Required | ความหมาย |
|---|---|---|---|
| `schema_version` | string | Yes | เวอร์ชันของ Data Contract ปัจจุบันคือ `1.0` |
| `message_id` | string | Yes | ID ไม่ซ้ำของข้อความ ใช้ตรวจข้อความซ้ำ |
| `lot_id` | string | Yes | ID ของล็อตกาแฟที่กำลังตรวจ |
| `type` | string | Yes | ชนิดข้อความ เช่น `moisture.measurement` |
| `timestamp` | string | Yes | เวลามาตรฐาน ISO 8601 แบบ UTC |
| `source` | object | Yes | อุปกรณ์และ Track ที่สร้างข้อมูล |
| `data` | object | Yes | ผลการตรวจของแต่ละ Track |

ตัวอย่างส่วนกลาง:

```json
{
  "schema_version": "1.0",
  "message_id": "esp32-01-000123",
  "lot_id": "lot-20261117-001",
  "type": "moisture.measurement",
  "timestamp": "2026-11-17T02:15:30Z",
  "source": {
    "device_id": "esp32_sensor_01",
    "track": "embedded"
  },
  "data": {}
}
```

### 9.4 ESP32 Moisture Payload

Publish ไปยัง `tgr2026/<team-id>/v1/moisture`

```json
{
  "schema_version": "1.0",
  "message_id": "esp32-01-000123",
  "lot_id": "lot-20261117-001",
  "type": "moisture.measurement",
  "timestamp": "2026-11-17T02:15:30Z",
  "source": {
    "device_id": "esp32_sensor_01",
    "track": "embedded"
  },
  "data": {
    "moisture_pct": 12.5,
    "raw_adc": 2450,
    "status": "ok"
  }
}
```

### 9.5 Vision Payload

Publish ไปยัง `tgr2026/<team-id>/v1/vision`

```json
{
  "schema_version": "1.0",
  "message_id": "rpi5-01-000456",
  "lot_id": "lot-20261117-001",
  "type": "vision.inference",
  "timestamp": "2026-11-17T02:15:35Z",
  "source": {
    "device_id": "rpi5_vision_01",
    "track": "vision"
  },
  "model": {
    "name": "coffee-defect",
    "version": "0.1.0",
    "task": "detection"
  },
  "data": {
    "total_beans": 50,
    "counts": {
      "good": 40,
      "shell": 1,
      "full_black": 4,
      "hull_husk": 1,
      "broken_chipped_cut": 3,
      "parchment_pergamino": 1,
      "immature_unripe": 0
    },
    "inference_ms": 185,
    "status": "ok"
  }
}
```

ชื่อ key ของเมล็ดกาแฟทั้ง 7 ประเภทต้องใช้ตามรายการนี้เท่านั้น:

```text
good
shell
full_black
hull_husk
broken_chipped_cut
parchment_pergamino
immature_unripe
```

### 9.6 Integrated Lot Assessment

Integration service รวม Moisture และ Vision ที่มี `lot_id` ตรงกัน ตรวจสอบข้อมูล แล้ว publish ไปยัง `tgr2026/<team-id>/v1/assessment`

```json
{
  "schema_version": "1.0",
  "message_id": "integration-01-000789",
  "lot_id": "lot-20261117-001",
  "type": "lot.assessment",
  "timestamp": "2026-11-17T02:15:36Z",
  "source": {
    "device_id": "integration_01",
    "track": "integration"
  },
  "data": {
    "moisture": {
      "moisture_pct": 12.5,
      "status": "ok"
    },
    "vision": {
      "total_beans": 50,
      "counts": {
        "good": 40,
        "shell": 1,
        "full_black": 4,
        "hull_husk": 1,
        "broken_chipped_cut": 3,
        "parchment_pergamino": 1,
        "immature_unripe": 0
      }
    },
    "validation": {
      "complete": true,
      "count_sum_matches_total": true
    }
  }
}
```

### 9.7 Validation Rules

- รวมข้อมูลเฉพาะข้อความที่มี `lot_id` ตรงกัน
- `schema_version` ต้องเป็นเวอร์ชันที่ระบบรองรับ
- `message_id` ต้องไม่เคยถูกประมวลผลมาก่อน
- `moisture_pct` ต้องอยู่ระหว่าง `0` ถึง `100`
- จำนวนของทั้ง 7 คลาสต้องเป็นจำนวนเต็มที่ไม่ติดลบ
- ผลรวม `counts` ทั้ง 7 คลาสต้องเท่ากับ `total_beans`
- `status` ใช้ค่า `ok`, `warning` หรือ `error`
- AI Agent และ Market API ต้องไม่ใช้ assessment ที่ `validation.complete` เป็น `false`

## 10. สถานะการพัฒนา (Development Status)

- [ ] พัฒนาระบบตรวจวัดความชื้นด้วย ESP32
- [ ] เตรียมชุดข้อมูลเมล็ดกาแฟ 7 ประเภท
- [ ] พัฒนาและฝึกสอนโมเดล Vision AI
- [ ] ติดตั้งโมเดลบน Raspberry Pi 5
- [ ] พัฒนา AI Agent
- [ ] เชื่อมต่อระบบแต่ละ Track
- [ ] ทดสอบการทำงานร่วมกันของระบบ
- [ ] เตรียมการสาธิตผลงาน

---

**Project:** Smart Robusta Coffee  
**Competition:** TESA Top Gun Rally #20  
**Repository:** TOPGUN-Integration
