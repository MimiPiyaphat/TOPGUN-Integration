# Dataset Notes

ไฟล์ภาพจริงในโฟลเดอร์นี้เก็บไว้เฉพาะเครื่องและไม่ commit เข้า Git

ก่อนเริ่มฝึกโมเดล ต้องบันทึกข้อมูลต่อไปนี้:

- แหล่งที่มาและ license ของ dataset
- วันที่ดาวน์โหลดหรือเวอร์ชัน
- รูปแบบ annotation
- mapping จาก label ต้นทางไปยัง 7 canonical classes ใน `../class_names.json`
- จำนวนตัวอย่างแยกตาม train, validation และ test
- วิธีป้องกันภาพซ้ำหรือภาพจากต้นฉบับเดียวกันหลุดข้าม split

## Dataset audit (2026-11-13)

> ข้อมูลส่วนนี้เป็นการสำรวจ dataset ที่มีอยู่ก่อนการแข่งขัน ไม่ใช่ dataset ทางการของผู้จัด และห้ามนำ mapping นี้ไปแทนข้อกำหนดที่ได้รับในวันแข่งขัน

ตรวจพบไฟล์ภาพทั้งหมด 4,038 ภาพใน raw dataset แต่ไม่พบไฟล์ annotation เช่น YOLO labels, COCO JSON หรือ CSV ภายในโฟลเดอร์ที่ได้รับ ชื่อไฟล์บางส่วนระบุวัตถุหลายชนิดในภาพเดียว จึงไม่ควรนำทุกภาพไปใช้เป็น single-label classification โดยตรง

จำนวนภาพที่ชื่อไฟล์ระบุ source label เดี่ยวอย่างชัดเจน:

| Source label | Train | Valid | Test | Total | Mapping status |
|---|---:|---:|---:|---:|---|
| `Biji_Normal` | 51 | 22 | 3 | 76 | Confirmed -> `good` |
| `Biji_Hitam` | 57 | 20 | 3 | 80 | Confirmed -> `full_black` |
| `Biji_Pecah` | 75 | 13 | 4 | 92 | Confirmed -> `broken_chipped_cut` |
| `Biji_Muda` | 48 | 18 | 8 | 74 | Confirmed -> `immature_unripe` |
| `Biji_Berkulit_Tanduk` | 48 | 18 | 8 | 74 | Confirmed -> `parchment_pergamino` |
| `Biji_Gelondong` | 51 | 17 | 8 | 76 | Candidate -> `hull_husk` |
| `Kulit_Kopi_Besar` | 42 | 20 | 8 | 70 | Candidate -> `hull_husk` |
| `Kulit_Kopi_Sedang` | 39 | 18 | 11 | 68 | Candidate -> `hull_husk` |
| `Kulit_Kopi_Kecil` | 81 | 10 | 5 | 96 | Candidate -> `hull_husk` |
| `Kulit_Tanduk_Besar` | 51 | 18 | 7 | 76 | Needs review |
| `Kulit_Tanduk_Sedang` | 48 | 14 | 12 | 74 | Needs review |
| `Kulit_Tanduk_Kecil` | 45 | 16 | 11 | 72 | Needs review |

ยังไม่พบ source label ที่ตรงกับ `shell` อย่างชัดเจน จึงต้องขอภาพจากชุดข้อมูลทางการหรือถ่ายเพิ่มก่อนฝึกโมเดล 7 คลาส

รายละเอียด mapping ชั่วคราวอยู่ใน `../label_mapping.csv` ปัจจุบันทุกแถวตั้ง `use_for_training=false` จนกว่าจะได้รับและตรวจสอบ dataset ทางการในวันแข่งขัน
