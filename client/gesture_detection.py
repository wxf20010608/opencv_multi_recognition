import sys
import cv2
import numpy as np
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QMessageBox, QApplication
import websockets
import asyncio
import json


class GestureDetectionUI(QWidget):
    send_signal2 = pyqtSignal()  # 返回信号

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.server_process = None
        self.websocket_thread = None

    def setup_ui(self):
        self.setWindowTitle("手势识别系统")
        self.resize(1139, 898)

        self.label = QLabel(self)
        self.label.setGeometry(30, 10, 1091, 771)
        self.label.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.label.setText("准备开始手势识别")

        self.start_btn = QPushButton("开始识别", self)
        self.start_btn.setGeometry(110, 810, 101, 61)
        self.start_btn.setStyleSheet("background-color: rgb(85, 255, 0);")
        self.start_btn.clicked.connect(self.start_detection)

        self.back_btn = QPushButton("返回主界面", self)
        self.back_btn.setGeometry(480, 810, 101, 61)
        self.back_btn.setStyleSheet("background-color: rgb(85, 255, 0);")
        self.back_btn.clicked.connect(self.go_back)

        self.quit_btn = QPushButton("退出", self)
        self.quit_btn.setGeometry(850, 810, 101, 61)
        self.quit_btn.setStyleSheet("background-color: rgb(85, 255, 0);")
        self.quit_btn.clicked.connect(self.quit_app)

    def start_detection(self):
        """点击开始识别按钮时启动服务器和连接"""
        if not self.server_process:
            # 启动手势识别服务器
            self.server_process = subprocess.Popen(['python', 'server/gesture_detection.py'])

        if not self.websocket_thread:
            self.websocket_thread = WebSocketClientThread()
            self.websocket_thread.frame_received.connect(self.update_frame)
            self.websocket_thread.start()
            self.start_btn.setEnabled(False)

    def update_frame(self, frame, finger_count):
        """更新显示画面"""
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        scaled_pixmap = pixmap.scaled(
            self.label.size(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation
        )
        self.label.setPixmap(scaled_pixmap)

        painter = QPainter(self.label.pixmap())
        painter.setPen(QColor(0, 255, 0))
        painter.setFont(QFont("Arial", 30))
        painter.drawText(50, 50, f"手指数量: {finger_count}")
        painter.end()

    def go_back(self):
        """返回主界面"""
        self.stop_detection()
        self.send_signal2.emit()
        self.close()

    def stop_detection(self):
        """停止检测"""
        if self.websocket_thread:
            self.websocket_thread.stop()
            self.websocket_thread = None

        if self.server_process:
            self.server_process.terminate()
            self.server_process = None

    def quit_app(self):
        """退出应用"""
        reply = QMessageBox.question(
            self, '退出', '确定要退出吗？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.stop_detection()
            QApplication.quit()

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.stop_detection()
        event.accept()


class WebSocketClientThread(QThread):
    frame_received = pyqtSignal(np.ndarray, int)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        asyncio.run(self.connect_websocket())

    async def connect_websocket(self):
        try:
            async with websockets.connect("ws://localhost:8004/ws/gesture-detection") as websocket:
                while self.running:
                    data = await websocket.recv()
                    message = json.loads(data)

                    frame_data = bytes.fromhex(message["frame"])
                    nparr = np.frombuffer(frame_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    self.frame_received.emit(frame, message["finger_count"])
        except Exception as e:
            print(f"WebSocket error: {e}")

    def stop(self):
        self.running = False
        self.wait()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = GestureDetectionUI()
    client.show()
    sys.exit(app.exec_())