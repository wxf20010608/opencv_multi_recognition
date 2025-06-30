# server.py
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import base64
from typing import  Dict
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


class FaceResult(BaseModel):
    face_id: int
    face_image: str  # base64编码的图像数据
    coordinates: Dict[str, int]  # x, y, w, h


@app.post("/detect_faces/")
async def detect_faces(file: UploadFile = File(...)):
    try:
        # 读取上传的图片
        image_data = await file.read()
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="无法解码图片")

        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 加载人脸检测模型
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        # 检测人脸
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6)

        # 处理检测到的人脸
        results = []
        for i, (x, y, w, h) in enumerate(faces):
            # 提取人脸区域
            face_roi = image[y:y + h, x:x + w]

            # 将人脸图像转为base64
            _, buffer = cv2.imencode('.jpg', face_roi)
            face_base64 = base64.b64encode(buffer).decode('utf-8')

            results.append(FaceResult(
                face_id=i + 1,
                face_image=face_base64,
                coordinates={"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
            ))

        return {"faces": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)