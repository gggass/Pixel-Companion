import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

class TestWin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFixedSize(200, 200)
        self.move(500, 500)
        self.setStyleSheet("background-color: green;")
        self.label = QLabel("Click me!", self)
        self.label.setFont(QFont("Arial", 16))
        self.label.move(40, 80)
        self.clicked = False

    def mousePressEvent(self, e):
        self.clicked = not self.clicked
        self.label.setText("CLICKED!" if self.clicked else "Click me!")
        self.setStyleSheet("background-color: red;" if self.clicked else "background-color: green;")

app = QApplication(sys.argv)
w = TestWin()
w.show()
sys.exit(app.exec_())
