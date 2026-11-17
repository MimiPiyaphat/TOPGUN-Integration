# ทดลองปรับกลยุทธ์โดยไม่แก้บอทใช้งานจริง

จำนวนเกมทดลองทั้งหมด 7,370; ชุดตรวจสุดท้าย 13 สนาม × 40 เกม × 3 สูตร = 1,560 เกม ไม่มี LLM ไม่มี network calls และไม่รอเวลาจริงแต่ละรอบ

สูตรที่เลือกก่อนตรวจชุดสุดท้าย: spread1. ใช้ seed 1310000–1310039 ซึ่งไม่ใช้เลือกสูตร ทั้งสามสูตรใช้ seed และประชากรคู่แข่งเดียวกัน

## ผลตรวจสุดท้าย

|สูตร|อันดับเฉลี่ย|สนามแย่สุด (อันดับเฉลี่ย)|Top5 ต่อเกม|สนามเฉลี่ย ≤5|สนามเฉลี่ย ≤10|PR เฉลี่ย|
|---|---:|---:|---:|---:|---:|---:|
|buyer_combo97|4.60|15.89|409/520|9/13|11/13|0.8704|
|react70|8.55|16.66|186/520|1/13|10/13|0.8571|
|spread1|3.00|6.24|445/520|10/13|13/13|0.8758|

อันดับเฉลี่ยเป็น midrank เมื่อ PR เสมอ; Top5 นับแบบเข้มงวด คือแม้ตกท้ายกลุ่มคะแนนเสมอก็ยังอยู่ ≤5 ไม่ใช่ให้ทีมเสมอทั้งหมดเป็นอันดับ 1 อันดับเหล่านี้เป็น PR rank ไม่ใช่การคำนวณคะแนนรวมผู้จัด ทั้งหมดได้คุณภาพและตัวอย่างเหมือนกันและใช้สูตรประเมินเดียวกันในสนามนี้

## รายสนาม

|สนาม|สูตร 70%|สูตรรายผู้ซื้อก่อนกระจาย|สูตรใหม่|Top5 สูตรใหม่|PR สูตรใหม่|
|---|---:|---:|---:|---:|---:|
|sandbox|4.65|2.01|1.64|38/40|0.8798|
|scarce|6.46|2.44|2.21|35/40|0.8565|
|abundant|5.64|2.09|1.76|37/40|0.8924|
|heterogeneous|6.22|2.19|2.01|35/40|0.8736|
|low_ceiling|5.06|2.79|2.36|33/40|0.8570|
|high_ceiling|6.08|2.39|2.14|36/40|0.8999|
|flat|6.44|2.24|1.89|37/40|0.8896|
|shared_noise|5.05|1.89|1.54|38/40|0.8791|
|day18_56|15.82|5.04|3.46|32/40|0.8872|
|day18_noise|16.66|5.34|6.01|30/40|0.8805|
|copies|9.81|2.29|1.94|37/40|0.8664|
|strong_rivals|7.03|13.19|6.24|26/40|0.8509|
|strong_56|16.16|15.89|5.86|31/40|0.8733|

## สูตรใหม่ทำอะไร

1. เริ่ม INSTANT ที่ markup .97; ประเภทอื่น 1.00 นี่เป็นค่าทดลอง ไม่ใช่เพดานที่ผู้จัดประกาศ
2. จำราคาแยกผู้ซื้อ โดยมีราคาประจำประเภทเป็นค่าอ้างอิง; น้ำหนักรายผู้ซื้อ = จำนวนรอบที่มี feedback ใช้ได้ / (จำนวนรอบดังกล่าว + 2)
3. รายประเภทคงก้าว 70% เดิม; รายผู้ซื้อปรับตามปริมาณ: ABOVE_LIMIT หัก .06 × kg, ข้อเสนออื่นคิด .02 × filled_kg − .03 × unfilled_kg, รวมแล้วหาร kg ของข้อเสนอที่ไม่ใช่ SPEC_MISMATCH และคูณ annealing
4. คง blacklist สเปก, PACE=2, split ครึ่งงบล็อต, ช่วง markup .85–1.30
5. spread1: ใช้ RNG อิสระของทีมเป็น seed เริ่มต้นในการจัดลำดับ RFQ แล้วเพิ่ม jitter ในคะแนนจัดอันดับ ±1% ไม่ได้สุ่มหรือเปลี่ยนราคาขายด้วย jitter
6. ไม่ใช้ข้อมูล true หรือเพดานลับในการตัดสินใจ; ข้อมูลดังกล่าวมีเฉพาะตัวตัดสินตลาดและการวิเคราะห์หลังเกม

## หลักฐานและข้อจำกัดของสนาม

ใช้สูตร TV, salvage .8, สเปก Commercial 7%/12.5% และ Instant 15%/14%, 6 รอบ และไม่มี capacity ของ sandbox จาก API snapshot จริง ขนาด RFQ สุ่มจาก wanted_kg ใน memory ที่ freeze ไว้
ทุกทีมได้ล็อตจริงและ sample ชุดเดียวกันในแต่ละเกม จึงไม่มีความได้เปรียบจาก noise แยกทีม ปริมาณสต็อกต่อทีมเท่ากัน
ส่วนที่ยังสมมติ: distribution คุณภาพจริง (defect .5–16%, moisture 10.5–15%, screen 12–18), กระสอบต่อล็อต 3–10, จำนวน RFQ 8/12, เพดาน Commercial 1.04/Instant .92/Specialty 1.12 พร้อม noise/shift, และโค้ดคู่แข่ง รายละเอียดใน experiment.py และ FIELDS ด้านล่าง ไม่ใช่โค้ดตลาดที่แกะได้จากผู้จัด
มี 20 ทีมในสนามทั่วไป; 56 ทีมและ 8 รอบในสนาม day18/strong_56 พร้อม capacity=ceil(stock_bags/rounds×1.5) ใช้ shared noise .45 หรือ .9 ใน defect และ .4 เท่าใน moisture
สนาม copies ใช้สูตร 70% เป็นคู่แข่งทั้งหมด; strong_rivals ใช้ buyer_start ทั้งหมด; strong_56 ใช้ buyer_volume ทั้งหมด ไม่ได้แทนคู่แข่งที่เป็นไปได้ทุกแบบ
บันทึก structurally_unsellable_kg จากการตรวจ true specs กับ RFQ ทุกใบหลังเกมเพื่อแยกสินค้าที่ไม่มีตลาดรับ ไม่กล่าวโทษกลยุทธ์จากสินค้าส่วนนั้น แต่ PR ยังรวม salvage ตามกติกา
PR เฉลี่ยสนามนี้อาจต่ำกว่าที่พบใน sandbox จริง เนื่องจาก distribution สินค้า/คู่แข่งยังเป็นสมมติฐาน ไม่บังคับปรับให้ starter ได้ .90 และไม่รับประกันอันดับจริงจากอันดับจำลอง

## การตรวจทางสถิติ

- spread1 − react70, rank: -5.54038, approximate paired 95% t interval [-6.47495, -4.60582]. Cluster by seed across fields; estimates simulation randomness, not market-model uncertainty.
- spread1 − react70, pr: +0.01871, approximate paired 95% t interval [+0.01577, +0.02165]. Cluster by seed across fields; estimates simulation randomness, not market-model uncertainty.
- spread1 − buyer_combo97, rank: -1.59231, approximate paired 95% t interval [-2.29738, -0.88724]. Cluster by seed across fields; estimates simulation randomness, not market-model uncertainty.
- spread1 − buyer_combo97, pr: +0.00548, approximate paired 95% t interval [+0.00417, +0.00679]. Cluster by seed across fields; estimates simulation randomness, not market-model uncertainty.

## การตรวจโค้ด/ขอบเขต

ทุกเกม assert ว่าปริมาณเป็นจำนวนกระสอบ ไม่เกินสต็อก/โควตา/RFQ ไม่ส่งคู่ซ้ำ และสต็อกหลังขายไม่ติดลบ ใช้ frozen react70 จากบอทปัจจุบันเป็น baseline โดยไม่มี monkeypatch เปลี่ยนบอทจริง

SHA256 โค้ดใช้งานจริงก่อน/หลังตรงกัน:
```json
{
  "main.py": true,
  "strategy.py": true,
  "react70.py": true,
  "memory.py": true,
  "appraisal.py": true
}
```

## สนามทั้งหมด
```json
{
  "sandbox": {},
  "scarce": {
    "demand": 0.5
  },
  "abundant": {
    "demand": 1.5
  },
  "heterogeneous": {
    "spread": 0.08
  },
  "low_ceiling": {
    "shift": -0.05
  },
  "high_ceiling": {
    "shift": 0.05
  },
  "flat": {
    "flat": true
  },
  "shared_noise": {
    "noise": 0.45
  },
  "day18_56": {
    "n": 56,
    "rounds": 8,
    "cap": true,
    "specialty": true,
    "noise": 0.45
  },
  "day18_noise": {
    "n": 56,
    "rounds": 8,
    "cap": true,
    "specialty": true,
    "noise": 0.9
  },
  "copies": {
    "copies": true
  },
  "strong_rivals": {
    "rivals": "buyer_start"
  },
  "strong_56": {
    "n": 56,
    "rounds": 8,
    "cap": true,
    "specialty": true,
    "noise": 0.45,
    "rivals": "buyer_volume"
  }
}
```

## ทำซ้ำ

ใช้ Python ใน .venv โครงการ รันจากโฟลเดอร์ lab_experiments: `python -B experiment.py search`, `validate`, `combine`, `final`, `spread`, `confirm` ตามลำดับ แล้ว `python -B report.py`
inputs.json, market_snapshot.json และ frozen/ เป็น input ที่ freeze ไว้; ผลทุกช่วงรวมสูตรที่แพ้อยู่ใน JSON แต่ละ stage. เมื่อใช้ชุดตรวจเพื่อออกแบบสูตรต่อ ถือว่าชุดนั้นกลายเป็น development data; ชุด confirm เท่านั้นที่ยังไม่ใช้เลือกสูตรในรายงานนี้

ยังไม่เขียนทับ strategy.py/react70.py/main.py และยังไม่ส่งสูตรนี้เข้าตลาดจริง ขั้นต่อไปคือทดสอบ sandbox จริงแบบสลับสูตรและเก็บ PR/อันดับ/reveal ครบทุกเกมก่อนรับเป็นค่าเริ่มต้น