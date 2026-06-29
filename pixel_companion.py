import sys
import json
import subprocess
import random
import os
import ctypes
from collections import deque

from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QBrush
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QSize, QThread, pyqtSignal

# --- 配置 --- #
PET_IMAGE_PATH = "./assets/pixel_pet.png"
KEY_DISPLAY_DURATION = 1500  # 按键显示时长 (毫秒)
PET_SIZE = 128  # 宠物图片大小


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
        self.alpha -= 5  # 逐渐消失

    def draw(self, painter):
        if self.alpha > 0:
            color = QColor(
                self.color.red(), self.color.green(), self.color.blue(), self.alpha
            )
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
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
            self.process = subprocess.Popen(
                ["./hook_core.exe"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # 预热输出：跳过初始化 JSON
            self.process.stdout.readline()

            for line in self.process.stdout:
                if not self.running:
                    break
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


# --- 主窗口类（全屏透明覆盖层） --- #
class PixelCompanion(QWidget):
    def __init__(self):
        super().__init__()

        # 全屏透明覆盖层：不拦截鼠标事件，所有交互通过全局钩子
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 先用 Qt 属性，showEvent 里再用 Win32 API 加固
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        screen = QApplication.desktop().availableGeometry()
        self.setGeometry(screen)
        self._click_through_set = False

        # 加载宠物图片
        self.pet_pixmap = QPixmap(PET_IMAGE_PATH)
        if self.pet_pixmap.isNull():
            print(f"Error: Could not load pet image from {PET_IMAGE_PATH}")
            self.pet_pixmap = QPixmap(PET_SIZE, PET_SIZE)
            self.pet_pixmap.fill(QColor("red"))
        else:
            self.pet_pixmap = self.pet_pixmap.scaled(
                PET_SIZE, PET_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

        # 宠物在全屏窗口中的位置（初始：右下角）
        self.pet_pos = QPoint(
            screen.width() - PET_SIZE - 20, screen.height() - PET_SIZE - 40
        )

        # 按键显示标签
        self.key_display_label = QLabel(self)
        self.key_display_label.setAlignment(Qt.AlignCenter)
        self.key_display_label.setStyleSheet(
            "background-color: rgba(0, 0, 0, 180); color: white;"
            "border-radius: 5px; padding: 5px;"
        )
        self.key_display_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.key_display_label.hide()
        self.key_display_timer = QTimer(self)
        self.key_display_timer.timeout.connect(self.hide_key_display)

        # 粒子系统
        self.particles = deque()
        self.mouse_effect_enabled = True
        self.mouse_effect_timer = QTimer(self)
        self.mouse_effect_timer.timeout.connect(self.update_particles)
        self.mouse_effect_timer.start(30)  # 每 30ms 更新粒子

        # 拖动状态
        self.dragging = False
        self.drag_offset = QPoint()
        self.drag_start_pos = QPoint()

        # 启动 Hook 监听线程
        self.hook_listener = HookListener()
        self.hook_listener.key_event_signal.connect(self.show_key_on_pet)
        self.hook_listener.mouse_event_signal.connect(self.handle_mouse_event)
        self.hook_listener.start()

    def pet_rect(self):
        """返回宠物在窗口中的矩形区域"""
        return QRect(self.pet_pos, QSize(PET_SIZE, PET_SIZE))

    # ---------- 按键显示 ----------
    def show_key_on_pet(self, key_name):
        self.key_display_label.setText(key_name)
        self.key_display_label.adjustSize()
        self._reposition_key_label()
        self.key_display_label.show()
        self.key_display_timer.start(KEY_DISPLAY_DURATION)

    def hide_key_display(self):
        self.key_display_label.hide()
        self.key_display_timer.stop()

    def _reposition_key_label(self):
        """将按键标签放在宠物上方"""
        lw = self.key_display_label.width()
        lh = self.key_display_label.height()
        self.key_display_label.move(
            self.pet_pos.x() + (PET_SIZE - lw) // 2,
            self.pet_pos.y() - lh - 10,
        )

    # ---------- 鼠标事件（来自 Hook） ----------
    def handle_mouse_event(self, event_type, x, y):
        if event_type == "mouse_move":
            # 粒子拖尾：x, y 是屏幕坐标，窗口全屏 → 坐标直接可用
            if self.mouse_effect_enabled:
                for _ in range(random.randint(1, 3)):
                    color = QColor(
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                    )
                    self.particles.append(Particle(x, y, color))
                while len(self.particles) > 100:
                    self.particles.popleft()
                self.update()

            # 拖拽更新
            if self.dragging:
                self.pet_pos = QPoint(
                    x - self.drag_offset.x(), y - self.drag_offset.y()
                )
                self._reposition_key_label()

        elif event_type == "mouse_left_down":
            if self.pet_rect().contains(x, y):
                self.dragging = True
                self.drag_offset = QPoint(
                    x - self.pet_pos.x(), y - self.pet_pos.y()
                )
                self.drag_start_pos = QPoint(x, y)

        elif event_type == "mouse_left_up":
            if self.dragging:
                # 几乎没有移动 → 视为点击，切换粒子特效
                dx = x - self.drag_start_pos.x()
                dy = y - self.drag_start_pos.y()
                if (dx * dx + dy * dy) < 25:  # 移动距离 < 5px
                    self._toggle_mouse_effect()
                self.dragging = False
                self.drag_start_pos = QPoint()

    def _toggle_mouse_effect(self):
        self.mouse_effect_enabled = not self.mouse_effect_enabled
        status = "ON" if self.mouse_effect_enabled else "OFF"
        self.show_key_on_pet(f"Particles: {status}")

    # ---------- 粒子更新 ----------
    def update_particles(self):
        if self.mouse_effect_enabled:
            for p in list(self.particles):
                p.update()
                if p.alpha <= 0:
                    self.particles.remove(p)
            self.update()

    # ---------- 绘制 ----------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 鼠标粒子
        for p in self.particles:
            p.draw(painter)

        # 宠物
        painter.drawPixmap(self.pet_pos.x(), self.pet_pos.y(), self.pet_pixmap)

    def showEvent(self, event):
        """窗口显示后，通过 Win32 API 强制设置鼠标穿透"""
        super().showEvent(event)
        if not self._click_through_set:
            self._enable_click_through()

    def _enable_click_through(self):
        """用 Win32 SetWindowLongPtr 设置 WS_EX_TRANSPARENT，比 Qt 属性更可靠"""
        try:
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_TOPMOST = 0x00000008

            user32 = ctypes.windll.user32
            ex_style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
            user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex_style)
            # 刷新窗口框架使样式生效
            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            ctypes.windll.user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER
            )
            self._click_through_set = True
        except Exception as e:
            print(f"Failed to enable click-through: {e}")

    # ---------- 退出 ----------
    def closeEvent(self, event):
        self.hook_listener.stop()
        self.hook_listener.wait()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 确保 assets 目录和占位符图片存在
    os.makedirs("./assets", exist_ok=True)
    if not os.path.exists(PET_IMAGE_PATH):
        placeholder = QPixmap(PET_SIZE, PET_SIZE)
        placeholder.fill(QColor("red"))
        placeholder.save(PET_IMAGE_PATH)
        print(f"Created placeholder pet image at {PET_IMAGE_PATH}")

    companion = PixelCompanion()
    companion.show()
    sys.exit(app.exec_())
