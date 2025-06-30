import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from paddleocr import PaddleOCR
import re
import time
import base64
from typing import List, Dict
from pydantic import BaseModel

app = FastAPI()

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LicensePlateResult(BaseModel):
    plate_text: str
    plate_type: str
    is_limited: bool
    plate_image_base64: str


class LicensePlateDetector:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        self.provinces = [
            "京", "沪", "津", "渝", "冀", "晋", "辽", "吉", "黑", "苏",
            "浙", "皖", "闽", "赣", "鲁", "豫", "鄂", "湘", "粤", "桂",
            "琼", "川", "贵", "云", "藏", "陕", "甘", "青", "宁", "新",
            "港", "澳", "台"
        ]
        self.provinces_str = "".join(self.provinces)
        self.limited_hours = [7, 8, 9, 17, 18, 19]

    def is_chinese_license_plate(self, plate_text: str) -> bool:
        patterns = [
            fr"^[{self.provinces_str}][A-Za-z]·?[A-Za-z0-9]{{5}}$",
            fr"^[{self.provinces_str}][A-Za-z]·[DFdf][A-Za-z0-9]{{5}}$",
            r"^使[0-9]{3}·[0-9]{3}$",
            fr"^[{self.provinces_str}][A-Za-z]·警[A-Za-z0-9]{{4}}$",
            r"^军[A-Za-z]·[A-Za-z0-9]{5}$"
        ]
        for pattern in patterns:
            if re.match(pattern, plate_text, re.IGNORECASE):
                return True
        return False

    def detect_plate_color(self, plate_image: np.ndarray) -> str:
        plate_hsv = cv2.cvtColor(plate_image, cv2.COLOR_BGR2HSV)

        green_mask = cv2.inRange(plate_hsv, np.array([20, 20, 30]), np.array([90, 255, 255]))
        green_pixels = np.count_nonzero(green_mask)
        green_ratio = green_pixels / (plate_image.shape[0] * plate_image.shape[1])

        blue_mask = cv2.inRange(plate_hsv, np.array([100, 43, 46]), np.array([124, 255, 255]))
        blue_pixels = np.count_nonzero(blue_mask)
        blue_ratio = blue_pixels / (plate_image.shape[0] * plate_image.shape[1])

        if green_ratio > 0.4:
            return "新能源车（绿牌）"
        elif blue_ratio > 0.2:
            return "燃油车（蓝牌）"
        else:
            return "未知颜色"

    def is_limited_time(self) -> bool:
        current_hour = time.localtime().tm_hour
        return current_hour in self.limited_hours

    async def process_image(self, image_data: bytes) -> List[Dict]:
        nparr = np.frombuffer(image_data, np.uint8)
        image_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        results = self.ocr.ocr(image_np, cls=True)
        plates_info = []

        for result in results[0]:
            if len(result[0]) < 2:
                continue

            plate_coords = np.array(result[0]).astype(int)
            plate_text = result[1][0]

            if not self.is_chinese_license_plate(plate_text):
                continue

            x_min, y_min = np.min(plate_coords, axis=0)
            x_max, y_max = np.max(plate_coords, axis=0)
            plate_image = image_np[y_min:y_max, x_min:x_max]

            # 将车牌图像转为base64
            _, buffer = cv2.imencode('.jpg', plate_image)
            plate_image_base64 = base64.b64encode(buffer).decode('utf-8')

            plate_type = self.detect_plate_color(plate_image)
            is_limited = plate_type == "燃油车（蓝牌）" and self.is_limited_time()

            plates_info.append({
                "plate_text": plate_text,
                "plate_type": plate_type,
                "is_limited": is_limited,
                "plate_image_base64": plate_image_base64
            })

        return plates_info

detector = LicensePlateDetector()

@app.post("/recognize_plate/", response_model=List[LicensePlateResult])
async def recognize_plate(file: UploadFile = File(...)):
    try:
        image_data = await file.read()
        results = await detector.process_image(image_data)
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)