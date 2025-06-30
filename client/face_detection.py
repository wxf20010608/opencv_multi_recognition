# client.py
import subprocess
import sys
import requests
import base64
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QMessageBox
from UI.face_detection import Ui_Form2


class FaceDetectionUI(QWidget, Ui_Form2):
    send_signal1 = pyqtSignal()  # 设置了一个信号

    def __init__(self):
        super().__init__()
        self.setupUi2(self)
        self.setup_ui()
        self.setup_connections()
        self.current_image = None
        self.api_url = "http://localhost:8004/detect_faces"
        self.server_process = None  # 添加服务器进程变量

    def setup_ui(self):
        self.setWindowTitle("人脸检测系统")
        self.resize(1088, 850)

        # 主显示标签
        self.label = QtWidgets.QLabel(self)
        self.label.setGeometry(QtCore.QRect(40, 60, 481, 481))
        self.label.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.label.setText("请上传照片")

        # 人脸显示标签 (label_2到label_13)
        self.face_labels = []
        positions = [
            (590, 60), (760, 60), (930, 60),
            (590, 240), (760, 240), (930, 240),
            (590, 420), (760, 420), (930, 420),
            (590, 600), (760, 600), (930, 600)
        ]

        for i, (x, y) in enumerate(positions):
            label = QtWidgets.QLabel(self)
            label.setGeometry(QtCore.QRect(x, y, 131, 151))
            label.setStyleSheet("background-color: rgb(255, 255, 255);")
            label.setText(f"人脸{i + 1}")
            self.face_labels.append(label)

        # 按钮
        self.upload_btn = QtWidgets.QPushButton("上传图片", self)
        self.upload_btn.setGeometry(QtCore.QRect(70, 600, 91, 51))
        self.upload_btn.setStyleSheet("background-color:rgb(255, 255, 127);")

        self.detect_btn = QtWidgets.QPushButton("开始识别", self)
        self.detect_btn.setGeometry(QtCore.QRect(340, 600, 91, 51))
        self.detect_btn.setStyleSheet("background-color:rgb(255, 255, 127);")

        self.back_btn = QtWidgets.QPushButton("返回主界面", self)
        self.back_btn.setGeometry(QtCore.QRect(70, 710, 91, 51))
        self.back_btn.setStyleSheet("background-color:rgb(255, 255, 127);")

        self.quit_btn = QtWidgets.QPushButton("退出", self)
        self.quit_btn.setGeometry(QtCore.QRect(340, 710, 91, 51))
        self.quit_btn.setStyleSheet("background-color:rgb(255, 255, 127);")

    def setup_connections(self):
        self.upload_btn.clicked.connect(self.upload_image)
        self.detect_btn.clicked.connect(self.start_detection)
        self.back_btn.clicked.connect(self.go_back)
        self.quit_btn.clicked.connect(self.quit_app)

    def start_detection(self):
        """点击开始识别按钮时启动服务器和连接"""
        try:
            # 检查端口是否被占用
            if self.is_port_in_use(8002):
                QMessageBox.warning(self, "警告", "端口8002已被占用，请先关闭其他使用该端口的程序")
                return

            if not self.server_process or self.server_process.poll() is not None:
                # 启动人脸识别服务器
                self.server_process = subprocess.Popen(
                    ['python', 'server/face_detection.py'],
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
                # 等待服务器启动
                QtCore.QTimer.singleShot(2000, self.detect_faces_after_server_start)
            else:
                self.detect_faces()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动服务器失败: {str(e)}")

    def detect_faces_after_server_start(self):
        """服务器启动后执行人脸检测"""
        if self.server_process and self.server_process.poll() is None:
            self.detect_faces()
        else:
            QMessageBox.warning(self, "错误", "服务器启动失败")

    def is_port_in_use(self, port):
        """检查端口是否被占用"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def upload_image(self):
        """上传图片并显示在主标签"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_path:
            pixmap = QtGui.QPixmap(file_path)
            if not pixmap.isNull():
                self.current_image = file_path
                # 填充显示，不保持宽高比
                scaled_pixmap = pixmap.scaled(
                    self.label.size(),
                    QtCore.Qt.IgnoreAspectRatio,
                    QtCore.Qt.SmoothTransformation
                )
                self.label.setPixmap(scaled_pixmap)
            else:
                QMessageBox.warning(self, "错误", "无法加载图片文件")

    def detect_faces(self):
        """调用API检测人脸并显示结果"""
        if not self.current_image:
            QMessageBox.warning(self, "警告", "请先上传图片")
            return

        try:
            with open(self.current_image, 'rb') as f:
                files = {'file': f}
                response = requests.post(self.api_url, files=files)

            if response.status_code == 200:
                self.display_faces(response.json())
            else:
                QMessageBox.warning(self, "错误", f"请求失败: {response.text}")

        except requests.exceptions.ConnectionError:
            QMessageBox.warning(self, "连接错误", "无法连接到人脸识别服务器，请确保服务器已启动")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误: {str(e)}")

    def display_faces(self, result):
        """显示检测到的人脸"""
        # 先清空所有人脸标签
        for label in self.face_labels:
            label.clear()

        faces = result.get('faces', [])

        # 显示前12个人脸（根据UI标签数量限制）
        for i, face in enumerate(faces[:12]):
            face_data = base64.b64decode(face['face_image'])
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(face_data)

            if not pixmap.isNull():
                # 填充显示，不保持宽高比
                scaled_pixmap = pixmap.scaled(
                    self.face_labels[i].size(),
                    QtCore.Qt.IgnoreAspectRatio,
                    QtCore.Qt.SmoothTransformation
                )
                self.face_labels[i].setPixmap(scaled_pixmap)

    def quit_app(self):
        """退出应用"""
        self.stop_server()
        reply = QMessageBox.question(
            self, '退出', '确定要退出吗？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            QApplication.quit()

    def go_back(self):
        """返回主界面"""
        self.stop_server()
        self.close()
        self.send_signal1.emit()  # 发送信号

    def stop_server(self):
        """停止服务器"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except:
                self.server_process.kill()
            finally:
                self.server_process = None

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.stop_server()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client2 = FaceDetectionUI()
    client2.show()
    sys.exit(app.exec_())