import cv2
import numpy as np
from pathlib import Path
from ultralytics import SAM

BASE_DIR = Path(__file__).resolve().parents[1]

def extract_with_sam(input_dir, output_dir, debug_dir, min_area_ratio=0.005, max_area_ratio=0.85):
    # โหลดโมเดล SAM 2 ขนาดเล็ก (ultralytics จะดาวน์โหลดให้อัตโนมัติในครั้งแรก)
    model = SAM(f"{BASE_DIR}/models/sam2.1_b.pt") 

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    debug_path = Path(debug_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    debug_path.mkdir(parents=True, exist_ok=True)

    for class_dir in input_path.iterdir():
        if not class_dir.is_dir():
            continue
        
        class_name = class_dir.name
        save_class_dir = output_path / class_name
        save_class_dir.mkdir(exist_ok=True)
        
        bean_count = 0
        for img_file in class_dir.glob("*.*"):
            if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
                continue
                
            img = cv2.imread(str(img_file))
            if img is None:
                continue

            h, w = img.shape[:2]
            total_pixels = h * w
            min_area = total_pixels * min_area_ratio
            max_area = total_pixels * max_area_ratio

            # สั่ง SAM หา Mask ของวัตถุทั้งหมดในภาพอัตโนมัติ (Segment Everything)
            results = model.predict(img, verbose=False)
            debug_img = img.copy()

            if results[0].masks is not None:
                masks = results[0].masks.data.cpu().numpy() # (N, H, W)

                for mask_bool in masks:
                    mask_uint8 = np.uint8(mask_bool) * 255
                    # ปรับขนาด Mask ให้ตรงกับภาพต้นฉบับเป๊ะๆ
                    if mask_uint8.shape != (h, w):
                        mask_uint8 = cv2.resize(mask_uint8, (w, h), interpolation=cv2.INTER_NEAREST)

                    area = cv2.countNonZero(mask_uint8)
                    # กรองขนาด: ตัดพื้นหลังแผ่นใหญ่ (area > max_area) และฝุ่นผง (area < min_area) ทิ้ง
                    if min_area < area < max_area:
                        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        if not contours:
                            continue
                        
                        cnt = max(contours, key=cv2.contourArea)
                        x, y, bw, bh = cv2.boundingRect(cnt)

                        # กรองสัดส่วน (กันขอบโต๊ะหรือแถบยาวๆ)
                        aspect_ratio = max(bw, bh) / (min(bw, bh) + 1e-5)
                        if aspect_ratio > 3.2:
                            continue

                        # เช็กความทึบของรูปทรง (Solidity) เม็ดกาแฟต้องเป็นก้อนค่อนข้างตัน ไม่ใช่เส้นยุ่งเหยิง
                        hull = cv2.convexHull(cnt)
                        hull_area = cv2.contourArea(hull)
                        solidity = area / (hull_area + 1e-5)
                        if solidity < 0.75:
                            continue

                        cv2.rectangle(debug_img, (x, y), (x+bw, y+bh), (0, 255, 0), 2)

                        crop_bgr = img[y:y+bh, x:x+bw]
                        crop_alpha = mask_uint8[y:y+bh, x:x+bw]
                        crop_bgra = cv2.merge([crop_bgr[:, :, 0], crop_bgr[:, :, 1], crop_bgr[:, :, 2], crop_alpha])

                        save_name = save_class_dir / f"{class_name}_{bean_count:04d}.png"
                        cv2.imwrite(str(save_name), crop_bgra)
                        bean_count += 1

            cv2.imwrite(str(debug_path / f"sam_{class_name}_{img_file.name}"), debug_img)
        print(f"[{class_name}] SAM สกัดได้: {bean_count} เม็ด")

if __name__ == "__main__":
    
    extract_with_sam(
        BASE_DIR / "datasets" / "raw",
        BASE_DIR / "datasets" / "extracted",
        BASE_DIR / "datasets" / "debug"
    )