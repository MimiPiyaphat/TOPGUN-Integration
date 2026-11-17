import json,statistics,math,hashlib
from pathlib import Path
from experiment import HERE,FIELDS

d=json.loads((HERE/'confirm.json').read_text()); rows=d['rows']; summary=d['summary']
chosen=next(p for p in d['policies'] if p.startswith('spread'))
inputs=json.loads((HERE/'inputs.json').read_text(encoding='utf-8'))
unchanged={n:hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()==h for n,h in inputs['production_hashes'].items()}
count=sum(len(json.loads((HERE/(s+'.json')).read_text())['rows']) for s in ('search','validate','combine','final','spread','confirm'))
lines=['# ทดลองปรับกลยุทธ์โดยไม่แก้บอทใช้งานจริง','',
f'จำนวนเกมทดลองทั้งหมด {count:,}; ชุดตรวจสุดท้าย 13 สนาม × 40 เกม × 3 สูตร = 1,560 เกม ไม่มี LLM ไม่มี network calls และไม่รอเวลาจริงแต่ละรอบ', '',
f'สูตรที่เลือกก่อนตรวจชุดสุดท้าย: {chosen}. ใช้ seed 1310000–1310039 ซึ่งไม่ใช้เลือกสูตร ทั้งสามสูตรใช้ seed และประชากรคู่แข่งเดียวกัน', '',
'## ผลตรวจสุดท้าย','','|สูตร|อันดับเฉลี่ย|สนามแย่สุด (อันดับเฉลี่ย)|Top5 ต่อเกม|สนามเฉลี่ย ≤5|สนามเฉลี่ย ≤10|PR เฉลี่ย|','|---|---:|---:|---:|---:|---:|---:|']
for p,s in summary.items():
 rs=[r for r in rows if r['policy']==p]
 lines.append(f"|{p}|{s['mean_rank']:.2f}|{s['worst_field']:.2f}|{sum(r['rank_worst']<=5 for r in rs)}/{len(rs)}|{sum(v['rank']<=5 for v in s['fields'].values())}/13|{sum(v['rank']<=10 for v in s['fields'].values())}/13|{s['pr']:.4f}|")
lines+=['','อันดับเฉลี่ยเป็น midrank เมื่อ PR เสมอ; Top5 นับแบบเข้มงวด คือแม้ตกท้ายกลุ่มคะแนนเสมอก็ยังอยู่ ≤5 ไม่ใช่ให้ทีมเสมอทั้งหมดเป็นอันดับ 1 อันดับเหล่านี้เป็น PR rank ไม่ใช่การคำนวณคะแนนรวมผู้จัด ทั้งหมดได้คุณภาพและตัวอย่างเหมือนกันและใช้สูตรประเมินเดียวกันในสนามนี้', '',
'## รายสนาม','','|สนาม|สูตร 70%|สูตรรายผู้ซื้อก่อนกระจาย|สูตรใหม่|Top5 สูตรใหม่|PR สูตรใหม่|','|---|---:|---:|---:|---:|---:|']
for f in FIELDS:
 rs=[r for r in rows if r['field']==f and r['policy']==chosen]
 s=summary[chosen]['fields'][f]
 lines.append(f"|{f}|{summary['react70']['fields'][f]['rank']:.2f}|{summary['buyer_combo97']['fields'][f]['rank']:.2f}|{s['rank']:.2f}|{sum(r['rank_worst']<=5 for r in rs)}/40|{s['pr']:.4f}|")
lines+=['','## สูตรใหม่ทำอะไร','','1. เริ่ม INSTANT ที่ markup .97; ประเภทอื่น 1.00 นี่เป็นค่าทดลอง ไม่ใช่เพดานที่ผู้จัดประกาศ',
'2. จำราคาแยกผู้ซื้อ โดยมีราคาประจำประเภทเป็นค่าอ้างอิง; น้ำหนักรายผู้ซื้อ = จำนวนรอบที่มี feedback ใช้ได้ / (จำนวนรอบดังกล่าว + 2)',
'3. รายประเภทคงก้าว 70% เดิม; รายผู้ซื้อปรับตามปริมาณ: ABOVE_LIMIT หัก .06 × kg, ข้อเสนออื่นคิด .02 × filled_kg − .03 × unfilled_kg, รวมแล้วหาร kg ของข้อเสนอที่ไม่ใช่ SPEC_MISMATCH และคูณ annealing',
'4. คง blacklist สเปก, PACE=2, split ครึ่งงบล็อต, ช่วง markup .85–1.30',
f'5. {chosen}: ใช้ RNG อิสระของทีมเป็น seed เริ่มต้นในการจัดลำดับ RFQ แล้วเพิ่ม jitter ในคะแนนจัดอันดับ ±{int(chosen.removeprefix("spread"))}% ไม่ได้สุ่มหรือเปลี่ยนราคาขายด้วย jitter',
'6. ไม่ใช้ข้อมูล true หรือเพดานลับในการตัดสินใจ; ข้อมูลดังกล่าวมีเฉพาะตัวตัดสินตลาดและการวิเคราะห์หลังเกม', '',
'## หลักฐานและข้อจำกัดของสนาม','','ใช้สูตร TV, salvage .8, สเปก Commercial 7%/12.5% และ Instant 15%/14%, 6 รอบ และไม่มี capacity ของ sandbox จาก API snapshot จริง ขนาด RFQ สุ่มจาก wanted_kg ใน memory ที่ freeze ไว้',
'ทุกทีมได้ล็อตจริงและ sample ชุดเดียวกันในแต่ละเกม จึงไม่มีความได้เปรียบจาก noise แยกทีม ปริมาณสต็อกต่อทีมเท่ากัน',
'ส่วนที่ยังสมมติ: distribution คุณภาพจริง (defect .5–16%, moisture 10.5–15%, screen 12–18), กระสอบต่อล็อต 3–10, จำนวน RFQ 8/12, เพดาน Commercial 1.04/Instant .92/Specialty 1.12 พร้อม noise/shift, และโค้ดคู่แข่ง รายละเอียดใน experiment.py และ FIELDS ด้านล่าง ไม่ใช่โค้ดตลาดที่แกะได้จากผู้จัด',
'มี 20 ทีมในสนามทั่วไป; 56 ทีมและ 8 รอบในสนาม day18/strong_56 พร้อม capacity=ceil(stock_bags/rounds×1.5) ใช้ shared noise .45 หรือ .9 ใน defect และ .4 เท่าใน moisture',
'สนาม copies ใช้สูตร 70% เป็นคู่แข่งทั้งหมด; strong_rivals ใช้ buyer_start ทั้งหมด; strong_56 ใช้ buyer_volume ทั้งหมด ไม่ได้แทนคู่แข่งที่เป็นไปได้ทุกแบบ',
'บันทึก structurally_unsellable_kg จากการตรวจ true specs กับ RFQ ทุกใบหลังเกมเพื่อแยกสินค้าที่ไม่มีตลาดรับ ไม่กล่าวโทษกลยุทธ์จากสินค้าส่วนนั้น แต่ PR ยังรวม salvage ตามกติกา',
'PR เฉลี่ยสนามนี้อาจต่ำกว่าที่พบใน sandbox จริง เนื่องจาก distribution สินค้า/คู่แข่งยังเป็นสมมติฐาน ไม่บังคับปรับให้ starter ได้ .90 และไม่รับประกันอันดับจริงจากอันดับจำลอง', '',
'## การตรวจทางสถิติ','']
for baseline in ('react70','buyer_combo97'):
 for metric in ('rank','pr'):
  ds=[]
  for seed in range(1310000,1310040):
   own=statistics.mean(r[metric] for r in rows if r['seed']==seed and r['policy']==chosen)
   other=statistics.mean(r[metric] for r in rows if r['seed']==seed and r['policy']==baseline)
   ds.append(own-other)
  m=statistics.mean(ds); half=2.023*statistics.stdev(ds)/math.sqrt(40)
  lines.append(f'- {chosen} − {baseline}, {metric}: {m:+.5f}, approximate paired 95% t interval [{m-half:+.5f}, {m+half:+.5f}]. Cluster by seed across fields; estimates simulation randomness, not market-model uncertainty.')
lines+=['','## การตรวจโค้ด/ขอบเขต','','ทุกเกม assert ว่าปริมาณเป็นจำนวนกระสอบ ไม่เกินสต็อก/โควตา/RFQ ไม่ส่งคู่ซ้ำ และสต็อกหลังขายไม่ติดลบ ใช้ frozen react70 จากบอทปัจจุบันเป็น baseline โดยไม่มี monkeypatch เปลี่ยนบอทจริง', '',
'SHA256 โค้ดใช้งานจริงก่อน/หลังตรงกัน:', '```json',json.dumps(unchanged,indent=2),'```', '',
'## สนามทั้งหมด','```json',json.dumps(FIELDS,indent=2),'```', '',
'## ทำซ้ำ','','ใช้ Python ใน .venv โครงการ รันจากโฟลเดอร์ lab_experiments: `python -B experiment.py search`, `validate`, `combine`, `final`, `spread`, `confirm` ตามลำดับ แล้ว `python -B report.py`',
'inputs.json, market_snapshot.json และ frozen/ เป็น input ที่ freeze ไว้; ผลทุกช่วงรวมสูตรที่แพ้อยู่ใน JSON แต่ละ stage. เมื่อใช้ชุดตรวจเพื่อออกแบบสูตรต่อ ถือว่าชุดนั้นกลายเป็น development data; ชุด confirm เท่านั้นที่ยังไม่ใช้เลือกสูตรในรายงานนี้', '',
'ยังไม่เขียนทับ strategy.py/react70.py/main.py และยังไม่ส่งสูตรนี้เข้าตลาดจริง ขั้นต่อไปคือทดสอบ sandbox จริงแบบสลับสูตรและเก็บ PR/อันดับ/reveal ครบทุกเกมก่อนรับเป็นค่าเริ่มต้น']
(HERE/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(dict(chosen=chosen,games=count,production_unchanged=unchanged,summary=summary),ensure_ascii=True))
