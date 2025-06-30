import cv2
import mediapipe as mp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


class GestureDetector:
    def __init__(self):
        self.cap = None
        self.is_running = False
        self.hands = mp_hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )

    async def detect_gestures(self, websocket: WebSocket):
        self.cap = cv2.VideoCapture(0)
        self.is_running = True

        try:
            while self.is_running:
                success, frame = self.cap.read()
                if not success:
                    break

                # 处理图像
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(frame)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                finger_count = 0
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        # 绘制手部关键点
                        mp_drawing.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                            mp_drawing.DrawingSpec(color=(127, 255, 255), thickness=2)
                        )
                        finger_count += self.count_fingers(hand_landmarks)

                # 翻转并编码图像
                frame = cv2.flip(frame, 1)
                _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                frame_data = buffer.tobytes()

                # 发送结果到客户端
                await websocket.send_json({
                    "frame": frame_data.hex(),
                    "finger_count": finger_count
                })

                await asyncio.sleep(0.033)  # ~30fps

        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.release_camera()

    def count_fingers(self, hand_landmarks):
        """改进的手指计数方法"""
        finger_tips = [4, 8, 12, 16, 20]  # 拇指、食指、中指、无名指、小指的指尖
        finger_dips = [3, 7, 11, 15, 19]  # 各手指的第二关节

        count = 0
        for tip, dip in zip(finger_tips, finger_dips):
            # 如果指尖的y坐标小于第二关节的y坐标(手指伸直)
            if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[dip].y:
                count += 1

        return count

    def release_camera(self):
        if self.cap:
            self.cap.release()
        if self.hands:
            self.hands.close()
        self.is_running = False


detector = GestureDetector()


@app.websocket("/ws/gesture-detection")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await detector.detect_gestures(websocket)
    except WebSocketDisconnect:
        detector.release_camera()
    except Exception as e:
        print(f"Error: {e}")
        detector.release_camera()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)