# Raspberry Pi 5 ONNX Handoff

ไฟล์ที่ Mi ส่งให้ Q หลังฝึกโมเดลจริง:

```text
coffee_classifier.onnx
coffee_classifier.onnx.json
onnx_predict.py
sample.jpg
sample_prediction.json
```

## 1. Install the runtime

บน Raspberry Pi OS 64-bit:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install onnxruntime numpy Pillow
```

## 2. Run inference

```bash
.venv/bin/python onnx_predict.py \
  --model coffee_classifier.onnx \
  --image sample.jpg \
  --lot-id lot-20261117-001 \
  --pretty
```

ตรวจว่า JSON มี `status: ok`, `lot_id` ถูกต้อง และ `predicted_class` เป็นหนึ่งใน 7 canonical classes

## 3. Measure on the Raspberry Pi

บันทึกข้อมูลต่อไปนี้เพื่อส่งกลับให้ Mi:

- เวลาทำนายเฉลี่ยต่อภาพ
- RAM ที่ใช้
- อุณหภูมิ CPU ก่อนและหลังทดสอบ
- ผลทำนายจากภาพตัวอย่าง 3-5 ภาพ
- เวอร์ชัน Python และ ONNX Runtime

## 4. Troubleshooting

| ปัญหา | แนวทางแก้ |
|---|---|
| `No module named onnxruntime` | ตรวจว่าใช้ Python จาก `.venv` และติดตั้ง wheel สำหรับ aarch64 |
| โมเดลโหลดไม่ได้ | ตรวจ SHA-256 ในไฟล์ `.onnx.json` และคัดลอกไฟล์ใหม่ |
| ทำงานช้า | ลดจำนวน process อื่น ทดสอบ CPU temperature และใช้ภาพขนาดตาม metadata |
| JSON คลาสผิดลำดับ | ใช้ `class_names` จาก `.onnx.json` ห้ามเขียนลำดับคลาสใหม่เอง |
