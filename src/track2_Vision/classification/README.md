# Coffee Bean Classification

โมดูล Classification ของ Track 2 ใช้ชื่อคลาสมาตรฐานเดียวกับ Integration Data Contract ใน README หลัก

## Canonical classes

ลำดับคลาสถูกกำหนดใน `class_names.json` และต้องใช้ลำดับนี้เหมือนกันในขั้นตอนเตรียมข้อมูล ฝึกโมเดล ประเมินผล และ inference:

1. `good`
2. `shell`
3. `full_black`
4. `hull_husk`
5. `broken_chipped_cut`
6. `parchment_pergamino`
7. `immature_unripe`

ห้ามใช้ชื่อย่อ เช่น `black`, `broken`, `hull`, `parchment` หรือ `immature` ในผลลัพธ์ที่ส่งเข้า Integration

## Local-only directories

- `.venv/` - Python virtual environment
- `dataset/` - raw และ processed datasets
- `results/` - checkpoints, metrics และ generated outputs

ไดเรกทอรีเหล่านี้ไม่ถูก commit เข้า Git เพื่อป้องกัน repository มีขนาดใหญ่เกินไป ให้บันทึกแหล่งที่มา เวอร์ชัน และขั้นตอนสร้าง dataset แทน

## Current status

- `train.py` ยังไม่มี implementation
- `predict.py` ยังไม่มี implementation
- `requirements.txt` ยังไม่มี dependencies
- raw dataset มีภาพ แต่ยังต้องตรวจสอบ annotation และสร้าง mapping จาก label ต้นทางไปยัง 7 canonical classes ก่อนฝึกโมเดล
- ผู้จัดจะแจก dataset ทางการในวันแข่งขัน ข้อมูลและ mapping ที่สำรวจล่วงหน้าเป็น provisional เท่านั้น ห้ามใช้แทนข้อมูลทางการ

## Competition-day dataset check

เมื่อได้รับ dataset ทางการ ให้วางข้อมูลในรูปแบบต่อไปนี้:

```text
dataset/official/
├── train/
│   ├── good/
│   ├── shell/
│   ├── full_black/
│   ├── hull_husk/
│   ├── broken_chipped_cut/
│   ├── parchment_pergamino/
│   └── immature_unripe/
├── val/
│   └── <7 class directories>
└── test/                 # optional
    └── <7 class directories>
```

จากนั้นตรวจข้อมูลก่อนฝึก:

```powershell
python verify_dataset.py --dataset dataset/official
```

ตัวตรวจจะเช็กชื่อคลาส จำนวนภาพ โฟลเดอร์ส่วนเกิน ไฟล์ที่ไม่รองรับ และภาพซ้ำข้าม train/val/test
