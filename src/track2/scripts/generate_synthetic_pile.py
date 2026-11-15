import cv2
import numpy as np
import random
from pathlib import Path

# กำหนด ID คลาสทั้ง 7 คลาสตามโจทย์
CLASSES = [
    "Good",         # 0
    "Shell",        # 1
    "Full_Black",   # 2
    "Hull_Husk",    # 3
    "Broken",       # 4
    "Parchment",    # 5
    "Immature"      # 6
]

def rotate_image_and_mask(bgra, angle):
    """หมุนภาพ RGBA โดยไม่ให้ขอบภาพโดนตัด"""
    h, w = bgra.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]
    
    rotated = cv2.warpAffine(bgra, M, (new_w, new_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
    return rotated

def generate_piles(beans_dir, bg_dir, output_dir, num_images=200, min_beans=15, max_beans=35):
    beans_path = Path(beans_dir)
    bg_files = list(Path(bg_dir).glob("*.*"))
    out_img_dir = Path(output_dir) / "images"
    out_lbl_dir = Path(output_dir) / "labels"
    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    # โหลดรายการไฟล์เม็ดกาแฟแยกตามคลาส
    bean_pool = {}
    for idx, cls_name in enumerate(CLASSES):
        files = list((beans_path / cls_name).glob("*.png"))
        if files:
            bean_pool[idx] = files

    for i in range(num_images):
        # 1. สุ่มภาพพื้นหลัง (เช่น รูปถ่ายโต๊ะเปล่าๆ ในสนามแข่ง)
        bg = cv2.imread(str(random.choice(bg_files)))
        bg = cv2.resize(bg, (640, 640)) # ขนาดมาตรฐานสำหรับ YOLO
        canvas = bg.copy()
        img_h, img_w = canvas.shape[:2]

        # สร้าง Layer เก็บ ID ของวัตถุแต่ละชิ้นเพื่อป้องกันการซ้อนทับจนมองไม่เห็น (Occlusion handling)
        instance_map = np.zeros((img_h, img_w), dtype=np.int32)
        instance_classes = {}

        num_to_place = random.randint(min_beans, max_beans)
        
        # กำหนดจุดศูนย์กลางของกอง (Cluster center) เพื่อให้เม็ดเกาะกลุ่มกันเป็นธรรมชาติ
        cluster_x = random.randint(200, img_w - 200)
        cluster_y = random.randint(200, img_h - 200)

        for inst_id in range(1, num_to_place + 1):
            cls_id = random.choice(list(bean_pool.keys()))
            bean_file = random.choice(bean_pool[cls_id])
            bean_bgra = cv2.imread(str(bean_file), cv2.IMREAD_UNCHANGED)

            # 2. Augmentation: สุ่มหมุน 0-360 องศา และปรับขนาดเล็กน้อย (±10%)
            angle = random.uniform(0, 360)
            bean_bgra = rotate_image_and_mask(bean_bgra, angle)
            
            scale = random.uniform(0.9, 1.1)
            new_w = int(bean_bgra.shape[1] * scale)
            new_h = int(bean_bgra.shape[0] * scale)
            bean_bgra = cv2.resize(bean_bgra, (new_w, new_h))

            # ปรับความสว่าง/Contrast เล็กน้อย (ห้ามปรับ Hue แรง เดี๋ยวสีคลาสเพี้ยน)
            alpha_channel = bean_bgra[:, :, 3]
            bgr_channel = bean_bgra[:, :, :3].astype(np.float32)
            brightness = random.uniform(0.9, 1.1)
            bgr_channel = np.clip(bgr_channel * brightness, 0, 255).astype(np.uint8)

            # 3. สุ่มตำแหน่งแบบ Normal Distribution รอบจุดศูนย์กลางกอง (ให้เม็ดชิดและเกยกัน)
            px = int(np.random.normal(cluster_x, 90)) - new_w // 2
            py = int(np.random.normal(cluster_y, 90)) - new_h // 2

            # เช็กขอบเขตไม่ให้หลุดเฟรม
            if px < 0 or py < 0 or px + new_w >= img_w or py + new_h >= img_h:
                continue

            # 4. แปะเม็ดกาแฟลงบน Canvas และอัปเดต Instance Map (เม็ดที่มาทีหลังจะทับเม็ดก่อนหน้า)
            mask_bool = alpha_channel > 128
            roi = canvas[py:py+new_h, px:px+new_w]
            roi[mask_bool] = bgr_channel[mask_bool]
            canvas[py:py+new_h, px:px+new_w] = roi

            inst_roi = instance_map[py:py+new_h, px:px+new_w]
            inst_roi[mask_bool] = inst_id
            instance_map[py:py+new_h, px:px+new_w] = inst_roi
            instance_classes[inst_id] = cls_id

        # 5. แปลง Instance Map ที่เหลืออยู่จริง (หลังโดนทับ) เป็น YOLO Segmentation Polygon
        yolo_labels = []
        for inst_id, cls_id in instance_classes.items():
            # ดึงเฉพาะพิกเซลของเม็ดนี้ที่ยังมองเห็นอยู่
            visible_mask = np.uint8(instance_map == inst_id) * 255
            
            # ถ้าเม็ดโดนทับจนเหลือน้อยเกินไป (เช่น < 300 px) ให้ข้าม ไม่ต้องสร้าง Label
            if cv2.countNonZero(visible_mask) < 300:
                continue

            contours, _ = cv2.findContours(visible_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            
            # เลือก Contour ที่ใหญ่ที่สุดของเม็ดนั้น และลดทอนจุด Polygon ให้กระชับ
            largest_cnt = max(contours, key=cv2.contourArea)
            epsilon = 0.005 * cv2.arcLength(largest_cnt, True)
            approx = cv2.approxPolyDP(largest_cnt, epsilon, True)

            if len(approx) >= 3:
                # Normalize พิกัดให้อยู่ในช่วง 0.0 - 1.0 ตามมาตรฐาน YOLO
                norm_coords = []
                for pt in approx:
                    nx = round(pt[0][0] / img_w, 6)
                    ny = round(pt[0][1] / img_h, 6)
                    norm_coords.extend([nx, ny])
                
                coord_str = " ".join(map(str, norm_coords))
                yolo_labels.append(f"{cls_id} {coord_str}")

        # บันทึกภาพและไฟล์ Label
        cv2.imwrite(str(out_img_dir / f"pile_{i:04d}.jpg"), canvas)
        with open(out_lbl_dir / f"pile_{i:04d}.txt", "w") as f:
            f.write("\n".join(yolo_labels))

    print(f"สร้างชุดข้อมูลจำลองกองเมล็ดกาแฟสำเร็จ: {num_images} ภาพ")

if __name__ == "__main__":
    generate_piles(
        beans_dir="extracted_beans_rgba",
        bg_dir="empty_backgrounds", # ถ่ายรูปพื้นโต๊ะเปล่าๆ 2-3 รูปใส่โฟลเดอร์นี้
        output_dir="yolo_seg_dataset",
        num_images=300
    )