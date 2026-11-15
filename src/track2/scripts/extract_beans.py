import cv2
import numpy as np
import os
from pathlib import Path

def extract_single_beans(input_dir, output_dir, min_area=1500, max_area=50000):
    """
    สกัดเม็ดกาแฟรายเม็ดออกจากภาพพื้นหลัง แล้วบันทึกเป็น PNG โปร่งใส (RGBA)
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # วนลูปตามโฟลเดอร์คลาส (เช่น Good, Shell, Full_Black, ...)
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

            # 1. แปลงเป็น LAB Color Space เพื่อแยกความต่างระหว่างเม็ดกาแฟกับพื้นหลังลายไม้
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # ใช้ Otsu's Thresholding กับช่องสี L (ความสว่าง) และ B (เหลือง-น้ำเงิน)
            # หมายเหตุ: หน้างานจริงให้ปรับค่า Threshold หรือใช้ HSV ตามสีพื้นหลังโต๊ะที่กรรมการจัดให้
            blur = cv2.GaussianBlur(b, (5, 5), 0)
            _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 2. ทำ Morphological Operations ลบจุดรบกวนเล็กๆ และอุดรูโหว่ในเม็ด
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

            # 3. หา Contours ของเม็ดกาแฟแต่ละเม็ด
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if min_area < area < max_area:
                    x, y, w, h = cv2.boundingRect(cnt)
                    
                    # สร้าง Mask เฉพาะเม็ดนี้
                    single_mask = np.zeros(img.shape[:2], dtype=np.uint8)
                    cv2.drawContours(single_mask, [cnt], -1, 255, thickness=cv2.FILLED)
                    
                    # Crop ภาพและ Mask
                    crop_bgr = img[y:y+h, x:x+w]
                    crop_alpha = single_mask[y:y+h, x:x+w]
                    
                    # รวมเป็นภาพ 4 Channels (BGRA) เพื่อให้พื้นหลังโปร่งใส
                    crop_bgra = cv2.merge([crop_bgr[:, :, 0], crop_bgr[:, :, 1], crop_bgr[:, :, 2], crop_alpha])
                    
                    save_name = save_class_dir / f"{class_name}_{bean_count:04d}.png"
                    cv2.imwrite(str(save_name), crop_bgra)
                    bean_count += 1

        print(f"[{class_name}] สกัดเม็ดกาแฟสำเร็จ: {bean_count} เม็ด")

if __name__ == "__main__":
    # โครงสร้างโฟลเดอร์: datasets/train/Good/img1.jpg
    extract_single_beans("datasets/train", "datasets/train_processed")