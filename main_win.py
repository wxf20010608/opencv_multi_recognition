import sys
from PyQt5.QtWidgets import QWidget, QMessageBox, QPushButton, QApplication, QLabel, QVBoxLayout
from UI.main import Ui_Form
from client.face_detection import FaceDetectionUI
from client.gesture_detection import GestureDetectionUI
from client.license_plates_detection import LicensePlateClient


class Main_Win(QWidget,Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # self.initUI()

        self.pushButton.clicked.connect(self.face_show)
        self.pushButton_2.clicked.connect(self.gesture_show)
        self.pushButton_3.clicked.connect(self.plates_show)
        self.pushButton_4.clicked.connect(self.quit)

        # 实例化主界面窗口GestureDetectionUI
        self.gd = GestureDetectionUI()
        self.gd.send_signal2.connect(self.handle_gesture_return)

        # 实例化主界面窗口FaceDetectionUI
        self.fd = FaceDetectionUI()
        self.fd.send_signal1.connect(self.show)

        # 实例化主界面窗口LicensePlateClient
        self.lpc = LicensePlateClient()
        self.lpc.send_signal.connect(self.show)

    def plates_show(self):
        self.close()
        self.lpc.show()

    def face_show(self):
        self.close()
        self.fd.show()

    def gesture_show(self):
        self.close()
        self.gd.show()

    def handle_gesture_return(self):
        """处理从手势界面返回"""
        self.show()  # 显示主窗口
        self.gesture_ui = None  # 清除引用

    def quit(self):
        self.result = QMessageBox.question(self, "退出", "是否退出程序", QMessageBox.Yes | QMessageBox.No)
        if self.result == QMessageBox.Yes:
            sys.exit(0)
        else:
            pass
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = Main_Win()
    main_win.show()
    sys.exit(app.exec_())

