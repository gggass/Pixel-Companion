import sys
import json
import subprocess
import random
import os
import ctypes
from collections import deque

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QBrush
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QSize, QThread, pyqtSignal

# --- 配置 --- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PET_IMAGE_PATH = os.path.join(BASE_DIR, "assets", "pixel_pet.png")
HOOK_EXE_PATH = os.path.join(BASE_DIR, "hook_core.exe")
KEY_DISPLAY_DURATION = 1500
PET_SIZE = 128


# --- 粒子 --- #
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
        self.alpha -= 5

    def draw(self, painter):
        if self.alpha > 0:
            c = QColor(self.color.red(), self.color.green(), self.color.blue(), self.alpha)
            painter.setBrush(QBrush(c))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(self.x), int(self.y), 5, 5)


# --- Hook 线程 --- #
class HookListener(QThread):
    key_signal = pyqtSignal(str)
    move_signal = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.running = True

    def run(self):
        try:
            self.process = subprocess.Popen(
                [HOOK_EXE_PATH],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, universal_newlines=True,
            )
            self.process.stdout.readline()
            for line in self.process.stdout:
                if not self.running:
                    break
                try:
                    data = json.loads(line)
                    t = data.get("event_type")
                    if t == "key_down":
                        self.key_signal.emit(data.get("key", "?"))
                    elif t == "mouse_move":
                        self.move_signal.emit(data.get("x", 0), data.get("y", 0))
                except Exception:
                    pass
        except FileNotFoundError:
            print("hook_core.exe not found")
        except Exception as e:
            print(f"Hook error: {e}")
        finally:
            if self.process and self.process.poll() is None:
                self.process.terminate()

    def stop(self):
        self.running = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()


# --- 粒子全屏覆盖层 --- #
class ParticleOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setGeometry(QApplication.desktop().availableGeometry())

        self.particles = deque()
        self.enabled = True

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def add(self, x, y):
        if not self.enabled:
            return
        c = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.particles.append(Particle(x, y, c))
        while len(self.particles) > 100:
            self.particles.popleft()

    def _tick(self):
        if not self.particles:
            return
        for p in list(self.particles):
            p.update()
            if p.alpha <= 0:
                self.particles.remove(p)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for pt in self.particles:
            pt.draw(p)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            hwnd = int(self.winId())
            WS_EX_TRANSPARENT = 0x20
            WS_EX_LAYERED = 0x80000
            u = ctypes.windll.user32
            ex = u.GetWindowLongPtrW(hwnd, -20) | WS_EX_TRANSPARENT | WS_EX_LAYERED
            u.SetWindowLongPtrW(hwnd, -20, ex)
            u.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0020 | 0x0002 | 0x0001 | 0x0004)
        except Exception:
            pass


# --- 宠物窗口 --- #
class PetWindow(QWidget):
    menu_requested = pyqtSignal(QPoint)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(PET_SIZE, PET_SIZE)

        screen = QApplication.desktop().availableGeometry()
        self.move(screen.width() - PET_SIZE - 20, screen.height() - PET_SIZE - 40)

        pix = QPixmap(PET_IMAGE_PATH)
        if pix.isNull():
            pix = QPixmap(PET_SIZE, PET_SIZE)
            pix.fill(QColor("red"))
        else:
            pix = pix.scaled(PET_SIZE, PET_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._pixmap = pix

        # 按键队列：每个按键一个独立标签，堆叠在宠物上方
        self._key_labels = []  # [(QLabel, QTimer), ...]
        self._drag_pos = None

    def show_key(self, text):
        """添加按键到队列顶部，旧键下移，到时自动消失"""
        label = QLabel(text, self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            "background-color: rgba(0,0,0,180); color: white; border-radius: 5px; padding: 5px;"
        )
        label.setFont(QFont("Arial", 10, QFont.Bold))
        label.adjustSize()
        label.show()

        timer = QTimer(self)
        timer.setSingleShot(True)

        entry = (label, timer)
        self._key_labels.insert(0, entry)  # 新键插入顶部

        # 限制队列长度
        while len(self._key_labels) > 5:
            old_label, old_timer = self._key_labels.pop()
            old_timer.stop()
            old_label.deleteLater()

        self._layout_key_labels()

        # 定时移除
        def remove():
            if entry in self._key_labels:
                self._key_labels.remove(entry)
                label.deleteLater()
                self._layout_key_labels()
        timer.timeout.connect(remove)
        timer.start(KEY_DISPLAY_DURATION)

    def _layout_key_labels(self):
        """从上到下排列所有按键标签"""
        y_offset = -10
        for label, _ in self._key_labels:
            label.adjustSize()
            label.move(
                (PET_SIZE - label.width()) // 2,
                y_offset - label.height(),
            )
            y_offset -= label.height() + 4

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.drawPixmap(0, 0, self._pixmap)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos()
        elif e.button() == Qt.RightButton:
            self.menu_requested.emit(e.globalPos())

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None:
            d = e.globalPos() - self._drag_pos
            self.move(self.pos() + d)
            self._drag_pos = e.globalPos()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._drag_pos is not None:
            d = e.globalPos() - self._drag_pos
            if d.manhattanLength() < 5:
                self.menu_requested.emit(e.globalPos())
            self._drag_pos = None


# --- 控制器 --- #
class Controller:
    def __init__(self):
        self.overlay = ParticleOverlay()
        self.pet = PetWindow()

        self.pet.menu_requested.connect(self._show_menu)

        self.hook = HookListener()
        self.hook.key_signal.connect(self.pet.show_key)
        self.hook.move_signal.connect(self.overlay.add)
        self.hook.start()

        app = QApplication.instance()
        app.aboutToQuit.connect(self._cleanup)

    def _show_menu(self, pos):
        # 菜单弹出时暂时隐藏覆盖层，确保菜单不被遮挡
        overlay_was_visible = self.overlay.isVisible()
        if overlay_was_visible:
            self.overlay.hide()

        menu = QMenu()
        if self.overlay.enabled:
            menu.addAction("Pause Particles", self._toggle)
        else:
            menu.addAction("Resume Particles", self._toggle)
        menu.addSeparator()
        menu.addAction("Exit", QApplication.quit)

        menu.exec_(pos)

        if overlay_was_visible:
            self.overlay.show()

    def _toggle(self):
        self.overlay.enabled = not self.overlay.enabled
        s = "ON" if self.overlay.enabled else "OFF"
        self.pet.show_key(f"Particles: {s}")

    def _cleanup(self):
        self.hook.stop()
        self.hook.wait()

    def show(self):
        self.overlay.show()
        self.pet.show()
        self.pet.raise_()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    os.makedirs(os.path.join(BASE_DIR, "assets"), exist_ok=True)
    if not os.path.exists(PET_IMAGE_PATH):
        p = QPixmap(PET_SIZE, PET_SIZE)
        p.fill(QColor("red"))
        p.save(PET_IMAGE_PATH)

    ctrl = Controller()
    ctrl.show()
    sys.exit(app.exec_())
