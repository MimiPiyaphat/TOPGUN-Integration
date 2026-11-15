# Vision Classification Competition Runbook

คู่มือนี้ใช้สำหรับ Mi ในวันได้รับ dataset ทางการ ขั้นตอนทั้งหมดให้รันจากโฟลเดอร์ `src/track2_Vision/classification`

## 0. Before leaving for the event

- ตรวจว่า `.venv` เปิดใช้งานได้
- สำรอง `models/pretrained/mobilenet_v3_small_imagenet.pth` ลง USB
- รันการซ้อมหนึ่งรอบ:

```powershell
.venv\Scripts\python rehearse_pipeline.py
```

ต้องเห็นข้อความ `REHEARSAL PASSED`

## 1. Preserve the organizer dataset

เก็บไฟล์ต้นฉบับไว้ใน `dataset/official_raw` และห้ามแก้ไขโดยตรง จากนั้นสร้างข้อมูลที่จัดโครงสร้างแล้วไว้ใน `dataset/official`

```text
dataset/official/
├── train/<7 canonical classes>/
├── val/<7 canonical classes>/
└── test/<7 canonical classes>/    # optional
```

ห้ามอัปโหลด dataset ไปยัง cloud จนกว่าจะตรวจสอบกติกาของผู้จัด

## 2. Validate the dataset

```powershell
.venv\Scripts\python verify_dataset.py `
  --dataset dataset/official `
  --minimum-images 1 `
  --report results/dataset-validation.json
```

ห้ามเริ่มฝึกจนกว่า JSON จะแสดง `"valid": true`

## 3. Train a fast baseline

```powershell
.venv\Scripts\python train.py `
  --dataset dataset/official `
  --output results/classification-baseline `
  --architecture mobilenet_v3_small `
  --weights none `
  --weights-file models/pretrained/mobilenet_v3_small_imagenet.pth `
  --freeze-backbone `
  --epochs 20 `
  --batch-size 16 `
  --image-size 224
```

ผลลัพธ์สำคัญ:

- `results/classification-baseline/best_model.pt`
- `results/classification-baseline/training_history.json`

## 4. Predict one image

```powershell
.venv\Scripts\python predict.py `
  --checkpoint results/classification-baseline/best_model.pt `
  --image PATH_TO_TEST_IMAGE.jpg `
  --lot-id lot-20261117-001 `
  --output results/prediction.json `
  --pretty
```

ตรวจว่า `predicted_class` เป็นหนึ่งใน 7 canonical classes และ `lot_id` ตรงกับล็อตที่กำลังตรวจ

## 5. If something fails

| ปัญหา | สิ่งที่ตรวจ |
|---|---|
| Dataset validation failed | ชื่อโฟลเดอร์ 7 คลาส, ภาพซ้ำข้าม split และจำนวนภาพ |
| Offline weights not found | คัดลอกไฟล์ `.pth` จาก USB ไปที่ `models/pretrained/` |
| CUDA unavailable | ใช้ `--device cpu` หรือติดตั้ง PyTorch รุ่น CUDA ที่ตรงกับเครื่อง |
| Out of memory | ลด `--batch-size` เป็น 8 หรือ 4 |
| Accuracy ต่ำ | ตรวจ label, class imbalance, confusion matrix และภาพที่ทำนายผิดก่อนเพิ่ม epochs |
| ผู้จัดไม่อนุญาต pretrained weights | ใช้ `--weights none` และเอา `--weights-file`/`--freeze-backbone` ออก |

## 6. Handoff to Q / Raspberry Pi

ส่งให้ Q อย่างน้อย:

- `best_model.pt`
- `class_names.json`
- ภาพทดสอบ 3-5 ภาพ
- JSON ตัวอย่างจาก `predict.py`
- ค่า `image_size` และ `architecture` ที่บันทึกอยู่ใน checkpoint
