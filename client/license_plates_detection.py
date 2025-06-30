import os
import subprocess
import sys
import requests
import base64
import socket
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QApplication, QWidget, QFileDialog,
                             QMessageBox, QTableWidgetItem)
from UI.license_plates_detection import Ui_Form1


class LicensePlateClient(QWidget, Ui_Form1):
    send_signal = pyqtSignal()  # 修正拼写错误

    def __init__(self):
        super().__init__()
        self.setWindowTitle("车牌识别系统")
        self.setupUi1(self)
        self.api_url = "http://localhost:8001/recognize_plate/"
        self.plate_results = []
        self.server_process = None  # 添加服务器进程变量
        self.current_image = None
        self.image_folder = None  # 明确初始化image_folder

        # 初始化所有图片标签的属性
        self.setup_label_properties()

        # 连接按钮信号
        self.pushButton.clicked.connect(self.upload_image)  # 上传图片
        self.pushButton_2.clicked.connect(self.upload_folder)  # 上传文件夹
        self.pushButton_6.clicked.connect(self.start_detection)  # 识别车牌
        self.pushButton_3.clicked.connect(self.go_back)  # 返回

        # 初始化表格
        self.init_table()

    def init_table(self):
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(["车牌号", "类型", "状态"])
        self.tableWidget.setRowCount(14)

        # 设置行标题
        for i in range(14):
            self.tableWidget.setVerticalHeaderItem(i, QTableWidgetItem(f"车牌{i + 1}"))

    def start_detection(self):
        """点击开始识别按钮时启动服务器和连接"""
        try:
            # 检查端口是否被占用
            if self.is_port_in_use(8001):
                QMessageBox.warning(self, "警告", "端口8001已被占用，请先关闭其他使用该端口的程序")
                return

            if not self.server_process or self.server_process.poll() is not None:
                # 启动车牌识别服务器
                self.server_process = subprocess.Popen(
                    ['python', 'server/license_plates_detection.py'],
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
                # 等待服务器启动
                QTimer.singleShot(2000, self.recognize_plates_after_server_start)
            else:
                self.recognize_plates()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动服务器失败: {str(e)}")

    def recognize_plates_after_server_start(self):
        """服务器启动后执行车牌识别"""
        if self.server_process and self.server_process.poll() is None:
            self.recognize_plates()
        else:
            QMessageBox.warning(self, "错误", "服务器启动失败")

    def is_port_in_use(self, port):
        """检查端口是否被占用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.current_image = file_path
            self.image_folder = None  # 切换到单图模式
            pixmap = QtGui.QPixmap(file_path)
            self.label.setPixmap(pixmap.scaled(
                self.label.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            ))

    def upload_folder(self):
        """处理文件夹上传"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:  # 确保用户确实选择了文件夹
            self.image_folder = folder_path
            self.current_image = None  # 清除单图模式
            QMessageBox.information(self, "成功", f"已选择文件夹: {folder_path}")
        else:
            self.image_folder = None  # 明确设置为None

    def recognize_plates(self):
        """识别车牌主逻辑"""
        if self.current_image:
            self.process_single_image(self.current_image)
        elif self.image_folder:
            self.process_folder(self.image_folder)
        else:
            QMessageBox.warning(self, "警告", "请先上传图片或文件夹")

    def process_single_image(self, image_path):
        try:
            with open(image_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(self.api_url, files=files, timeout=10)

            if response.status_code == 200:
                self.plate_results = response.json()
                self.display_results()
            else:
                raise Exception(response.json().get("detail", "识别失败"))
        except requests.exceptions.ConnectionError:
            QMessageBox.warning(self, "连接错误", "无法连接到车牌识别服务器，请确保服务器已启动")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"识别失败: {str(e)}")

    def process_folder(self, folder_path):
        """处理文件夹中的所有图片"""
        try:
            if not folder_path or not os.path.isdir(folder_path):
                raise ValueError("无效的文件夹路径")

            all_results = []
            valid_images = [
                f for f in os.listdir(folder_path)
                if f.lower().endswith(('.png', '.jpg', '.jpeg'))
            ]

            if not valid_images:
                QMessageBox.warning(self, "警告", "文件夹中没有有效的图片文件")
                return

            progress = QtWidgets.QProgressDialog(
                "正在处理图片...", "取消", 0, len(valid_images), self)
            progress.setWindowTitle("请稍候")
            progress.setWindowModality(QtCore.Qt.WindowModal)

            for i, img_file in enumerate(valid_images):
                progress.setValue(i)
                if progress.wasCanceled():
                    break

                img_path = os.path.join(folder_path, img_file)
                try:
                    if not os.path.isfile(img_path):
                        continue

                    with open(img_path, 'rb') as f:
                        response = requests.post(
                            self.api_url,
                            files={'file': f},
                            timeout=10
                        )

                    if response.status_code == 200:
                        result = response.json()
                        if result:
                            all_results.extend(result)
                except Exception:
                    continue

            progress.close()

            if not all_results:
                QMessageBox.warning(self, "警告", "未识别到任何有效车牌")
                return

            self.plate_results = all_results
            self.display_results()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理文件夹失败: {str(e)}")

    def setup_label_properties(self):
        """设置所有图片标签的显示属性 - 填充模式"""
        self.label.setScaledContents(True)
        self.label.setAlignment(QtCore.Qt.AlignCenter)

        for i in range(1, 15):
            label_name = f"label_{i}" if i > 1 else "label"
            label = getattr(self, label_name)
            label.setScaledContents(True)
            label.setAlignment(QtCore.Qt.AlignCenter)

    def display_results(self):
        """显示所有识别结果"""
        self.clear_display()

        for i, plate in enumerate(self.plate_results[:14]):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(plate['plate_text']))
            self.tableWidget.setItem(i, 1, QTableWidgetItem(plate['plate_type']))
            status = "限行" if plate['is_limited'] else "不限行"
            self.tableWidget.setItem(i, 2, QTableWidgetItem(status))

            label_name = f"label_{i + 1}" if i > 0 else "label"
            label = getattr(self, label_name)
            self.display_plate_image(plate['plate_image_base64'], label)

    def display_plate_image(self, image_base64, label):
        try:
            image_data = base64.b64decode(image_base64)
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    label.size(),
                    QtCore.Qt.IgnoreAspectRatio,
                    QtCore.Qt.SmoothTransformation
                )
                label.setPixmap(scaled_pixmap)
        except Exception:
            pass

    def clear_display(self):
        """清除所有显示内容"""
        for i in range(self.tableWidget.rowCount()):
            for j in range(self.tableWidget.columnCount()):
                self.tableWidget.setItem(i, j, QTableWidgetItem(""))

        for i in range(15):
            label_name = "label" if i == 0 else f"label_{i}"
            if hasattr(self, label_name):
                label = getattr(self, label_name)
                label.clear()

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

    def go_back(self):
        """返回主界面"""
        self.stop_server()
        self.close()
        self.send_signal.emit()

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.stop_server()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client1 = LicensePlateClient()
    client1.show()
    sys.exit(app.exec_())