import sys
import json
import subprocess
import threading
import time
import random
from collections import deque

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QPen, QBrush
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal

# --- 配置 --- #
PET_IMAGE_PATH = "./assets/pixel_pet.png" # 像素宠物图片路径
KEY_DISPLAY_DURATION = 1500 # 按键显示时长 (毫秒)
MOUSE_EFFECT_DURATION = 500 # 鼠标粒子效果时长 (毫秒)
PET_SIZE = 128 # 宠物图片大小

# --- 鼠标粒子效果类 --- #
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.alpha = 255
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.alpha -= 5 # 逐渐消失

    def draw(self, painter):
        if self.alpha > 0:
            color = QColor(self.color.red(), self.color.green(), self.color.blue(), self.alpha)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(self.x), int(self.y), 5, 5)

# --- C++ Hook Core 监听线程 --- #
class HookListener(QThread):
    key_event_signal = pyqtSignal(str)
    mouse_event_signal = pyqtSignal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.running = True

    def run(self):
        try:
            # 启动 C++ Hook Core
            self.process = subprocess.Popen(
                ["./hook_core.exe"], # Windows 平台的可执行文件
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 预热输出
            self.process.stdout.readline()

            for line in self.process.stdout:
                if not self.running: break
                try:
                    data = json.loads(line)
                    event_type = data.get("event_type")
                    if event_type == "key_down":
                        key = data.get("key", "Unknown")
                        self.key_event_signal.emit(key)
                    elif event_type and event_type.startswith("mouse_"):
                        x = data.get("x", 0)
                        y = data.get("y", 0)
                        self.mouse_event_signal.emit(event_type, x, y)
                except json.JSONDecodeError:
                    print(f"Error decoding JSON: {line.strip()}")
                except Exception as e:
                    print(f"Error processing event: {e}")
        except FileNotFoundError:
            print("Error: hook_core.exe not found. Please compile it first.")
        except Exception as e:
            print(f"Error starting hook_core: {e}")
        finally:
            if self.process and self.process.poll() is None:
                self.process.terminate()
            print("Hook Listener stopped.")

    def stop(self):
        self.running = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()

# --- 主窗口类 --- #
class PixelCompanion(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(100, 100, PET_SIZE, PET_SIZE) # 初始位置和大小

        self.pet_label = QLabel(self)
        pixmap = QPixmap(PET_IMAGE_PATH)
        if pixmap.isNull():
            print(f"Error: Could not load pet image from {PET_IMAGE_PATH}")
            # 使用一个默认的纯色方块作为宠物
            pixmap = QPixmap(PET_SIZE, PET_SIZE)
            pixmap.fill(QColor("red"))
        self.pet_label.setPixmap(pixmap.scaled(PET_SIZE, PET_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.pet_label.setGeometry(0, 0, PET_SIZE, PET_SIZE)

        # 按键显示
        self.key_display_label = QLabel(self)
        self.key_display_label.setAlignment(Qt.AlignCenter)
        self.key_display_label.setStyleSheet("background-color: rgba(0, 0, 0, 180); color: white; border-radius: 5px; padding: 5px;")
        self.key_display_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.key_display_label.hide()
        self.key_display_timer = QTimer(self)
        self.key_display_timer.timeout.connect(self.hide_key_display)

        # 鼠标粒子效果
        self.particles = deque()
        self.mouse_effect_enabled = True
        self.mouse_effect_timer = QTimer(self)
        self.mouse_effect_timer.timeout.connect(self.update_particles)
        self.mouse_effect_timer.start(30) # 每 30ms 更新一次粒子

        # 拖动功能
        self.old_pos = None

        # 启动 Hook 监听线程
        self.hook_listener = HookListener()
        self.hook_listener.key_event_signal.connect(self.show_key_on_pet)
        self.hook_listener.mouse_event_signal.connect(self.handle_mouse_event)
        self.hook_listener.start()

        # 初始位置：右下角
        self.move_to_bottom_right()

    def move_to_bottom_right(self):
        screen_rect = QApplication.desktop().availableGeometry(self)
        self.move(screen_rect.width() - self.width(), screen_rect.height() - self.height())

    def show_key_on_pet(self, key_name):
        self.key_display_label.setText(key_name)
        self.key_display_label.adjustSize()
        # 将按键显示在宠物上方
        self.key_display_label.move(
            (self.width() - self.key_display_label.width()) // 2,
            -self.key_display_label.height() - 10
        )
        self.key_display_label.show()
        self.key_display_timer.start(KEY_DISPLAY_DURATION)

    def hide_key_display(self):
        self.key_display_label.hide()
        self.key_display_timer.stop()

    def handle_mouse_event(self, event_type, x, y):
        if event_type == "mouse_move" and self.mouse_effect_enabled:
            # 在鼠标位置生成粒子
            for _ in range(random.randint(1, 3)): # 每次生成 1-3 个粒子
                self.particles.append(Particle(x, y, QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))))
            # 限制粒子数量
            while len(self.particles) > 100: # 最多 100 个粒子
                self.particles.popleft()
            self.update() # 触发重绘
        elif event_type == "mouse_left_down":
            # 检查是否点击了宠物
            if self.pet_label.geometry().contains(self.pet_label.mapFromGlobal(QPoint(x, y))):
                self.toggle_mouse_effect_menu()

    def toggle_mouse_effect_menu(self):
        # 简单的菜单切换，实际可以弹出一个 QMenu
        self.mouse_effect_enabled = not self.mouse_effect_enabled
        status = "Enabled" if self.mouse_effect_enabled else "Disabled"
        self.show_key_on_pet(f"Mouse Effect: {status}")

    def update_particles(self):
        if self.mouse_effect_enabled:
            for p in list(self.particles): # 遍历副本，因为可能会删除元素
                p.update()
                if p.alpha <= 0:
                    self.particles.remove(p)
            self.update() # 触发重绘

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制鼠标粒子
        for p in self.particles:
            p.draw(painter)

        # 绘制宠物 (由 pet_label 负责，这里不需要额外绘制)

    # 拖动窗口
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def closeEvent(self, event):
        self.hook_listener.stop()
        self.hook_listener.wait()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 创建 assets 目录并放置一个占位符图片
    # 实际使用时，用户需要替换为自己的像素宠物图片
    import os
    assets_dir = "./assets"
    os.makedirs(assets_dir, exist_ok=True)
    if not os.path.exists(PET_IMAGE_PATH):
        # 创建一个简单的红色方块作为占位符
        placeholder_pixmap = QPixmap(PET_SIZE, PET_SIZE)
        placeholder_pixmap.fill(QColor("red"))
        placeholder_pixmap.save(PET_IMAGE_PATH)
        print(f"Created placeholder pet image at {PET_IMAGE_PATH}")

    companion = PixelCompanion()
    companion.show()
    sys.exit(app.exec_()))
