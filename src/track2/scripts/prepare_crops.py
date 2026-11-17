import cv2
import numpy as np
from pathlib import Path

# ชื่อคลาส 7 คลาสตามกติกา Day 1 เป๊ะๆ
CLASSES = ["black", "broken", "good", "husk", "immature", "parchment", "shell"]

def extract_beans_white_bg(img_path, pad=10):
    img = cv2.imread(str(img_path))
    if img is None:
        return []
    
    h, w = img.shape[:2]
    # ถ้าภาพใหญ่ระดับ 3072x4096 ให้ครอปเฉพาะพื้นที่ตรงกลาง 60% ตามคำแนะนำสไลด์หน้า 9
    if max(h, w) > 2000:
        cy, cx = h // 2, w // 2
        crop_size = int(min(h, w) * 0.65)
        y1, y2 = max(0, cy - crop_size // 2), min(h, cy + crop_size // 2)
        x1, x2 = max(0, cx - crop_size // 2), min(w, cx + crop_size // 2)
        img = img[y1:y2, x1:x2]

    # แปลงเป็น LAB ใช้ช่อง L (ความสว่าง) และ B แยกเม็ดกาแฟออกจากกระดาษขาว
    blurred = cv2.GaussianBlur(img, (7, 7), 0)
    lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)
    l_ch, _, _ = cv2.split(lab)

    # พื้นกระดาษขาวจะสว่างมาก -> ใช้ Otsu THRESH_BINARY_INV
    _, mask = cv2.threshold(l_ch, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # ลบฝุ่นผงและอุดรูโหว่ในเม็ด
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    crops = []
    img_area = img.shape[0] * img.shape[1]
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # กรองขนาดเม็ดกาแฟ (ปรับสัดส่วนตามขนาดภาพ)
        if (img_area * 0.001) < area < (img_area * 0.15):
            x, y, bw, bh = cv2.boundingRect(cnt)
            # เผื่อขอบเล็กน้อย (Padding) ให้โมเดลเห็นรูปทรงรอบเม็ดครบ
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(img.shape[1], x + bw + pad)
            y2 = min(img.shape[0], y + bh + pad)
            crops.append(img[y1:y2, x1:x2])
            
    return crops

def build_dataset(raw_dir="raw_day1", out_dir="crops"):
    raw_path = Path(raw_dir)
    for cls_name in CLASSES:
        cls_folder = raw_path / cls_name
        if not cls_folder.exists():
            continue
        
        img_files = sorted(list(cls_folder.glob("*.*")))
        # แบ่ง Split ตามไฟล์ภาพต้นฉบับ (เช่น 2 ภาพแรกเป็น train, ภาพสุดท้ายเป็น val)
        for idx, img_file in enumerate(img_files):
            split = "val" if (idx == len(img_files) - 1 and len(img_files) > 1) else "train"
            save_dir = Path(out_dir) / split / cls_name
            save_dir.mkdir(parents=True, exist_ok=True)
            
            bean_crops = extract_beans_white_bg(img_file)
            for b_idx, crop in enumerate(bean_crops):
                cv2.imwrite(str(save_dir / f"{img_file.stem}_bean{b_idx:02d}.jpg"), crop)
            print(f"[{cls_name}] {img_file.name} -> {split} ({len(bean_crops)} เม็ด)")

if __name__ == "__main__":
    build_dataset()