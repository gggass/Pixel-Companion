import sys
import json
import subprocess
import random
import os
import ctypes
from collections import deque

from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QMenu,
                             QInputDialog, QMessageBox, QTextEdit, QDialog,
                             QVBoxLayout, QDialogButtonBox, QAction)
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QBrush, QClipboard
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


# --- 按键显示面板（浮动在宠物左边） --- #
class KeyPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(120)

        self._entries = []  # [(QLabel, QTimer), ...]
        self._max_entries = 5

    def add_key(self, text):
        label = QLabel(text, self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            "color: white; background-color: rgba(0,0,0,160);"
            "border-radius: 4px; padding: 3px 6px;"
        )
        label.setFont(QFont("Arial", 10, QFont.Bold))
        label.adjustSize()
        label.show()

        timer = QTimer(self)
        timer.setSingleShot(True)

        self._entries.insert(0, (label, timer))
        while len(self._entries) > self._max_entries:
            old_label, old_timer = self._entries.pop()
            old_timer.stop()
            old_label.deleteLater()

        self._relayout()

        def remove():
            if (label, timer) in self._entries:
                self._entries.remove((label, timer))
                label.deleteLater()
                self._relayout()
        timer.timeout.connect(remove)
        timer.start(KEY_DISPLAY_DURATION)

    def _relayout(self):
        y = 4
        for label, _ in self._entries:
            label.adjustSize()
            label.move((self.width() - label.width()) // 2, y)
            y += label.height() + 3
        self.setFixedHeight(y + 4)

    def anchor_to(self, pet_global_pos):
        """定位在宠物左边"""
        self.move(pet_global_pos.x() - self.width() - 8, pet_global_pos.y())


# --- 宠物窗口 --- #
class PetWindow(QWidget):
    menu_requested = pyqtSignal(QPoint)
    moved = pyqtSignal(QPoint)  # 位置变化 → 通知 KeyPanel 跟随

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

        self._drag_pos = None

    def set_image(self, path):
        pix = QPixmap(path)
        if pix.isNull():
            return
        self._pixmap = pix.scaled(PET_SIZE, PET_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.update()

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
            self.moved.emit(self.pos())

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
        self.key_panel = KeyPanel()

        self.pet.menu_requested.connect(self._show_menu)
        self.pet.moved.connect(self.key_panel.anchor_to)
        self.pet.moved.connect(self._on_pet_moved)

        self._pet_pos = self.pet.pos()

        # 剪贴板历史
        self._clipboard_history = deque(maxlen=10)
        clipboard = QApplication.clipboard()
        clipboard.dataChanged.connect(self._on_clipboard_changed)

        # 便签存储路径
        self._notes_path = os.path.join(BASE_DIR, "assets", "notes.txt")

        # 可切换角色列表
        self._pets = self._scan_pets()

        self.hook = HookListener()
        self.hook.key_signal.connect(self.key_panel.add_key)
        self.hook.move_signal.connect(self.overlay.add)
        self.hook.start()

        app = QApplication.instance()
        app.aboutToQuit.connect(self._cleanup)

    def _on_pet_moved(self, pos):
        self._pet_pos = pos

    def _scan_pets(self):
        """扫描所有可用角色"""
        pets = [PET_IMAGE_PATH]  # 默认角色
        pet_dir = os.path.join(BASE_DIR, "assets", "pets")
        if os.path.isdir(pet_dir):
            for f in sorted(os.listdir(pet_dir)):
                if f.endswith(".png"):
                    pets.append(os.path.join(pet_dir, f))
        return pets

    def _on_clipboard_changed(self):
        text = QApplication.clipboard().text()
        if text and text not in self._clipboard_history:
            self._clipboard_history.appendleft(text)

    def _show_menu(self, pos):
        overlay_was_visible = self.overlay.isVisible()
        if overlay_was_visible:
            self.overlay.hide()

        menu = QMenu()

        # 粒子开关
        if self.overlay.enabled:
            menu.addAction("暂停粒子", self._toggle)
        else:
            menu.addAction("恢复粒子", self._toggle)

        menu.addSeparator()

        # 剪贴板历史
        cb_menu = menu.addMenu("剪贴板历史")
        if self._clipboard_history:
            for i, text in enumerate(self._clipboard_history):
                snippet = text[:40] + "..." if len(text) > 40 else text
                action = cb_menu.addAction(f"{i+1}. {snippet}")
                action.setData(text)
            cb_menu.addSeparator()
            cb_menu.addAction("清除历史", self._clear_clipboard_history)
        else:
            cb_menu.addAction("(空)").setEnabled(False)

        # 剪贴板子菜单点击处理
        cb_menu.triggered.connect(self._on_clipboard_menu)

        # 快捷便签
        note_menu = menu.addMenu("快捷便签")
        note_menu.addAction("查看便签", self._view_notes)
        note_menu.addAction("添加便签", self._add_note)

        # 切换角色
        pet_menu = menu.addMenu("切换角色")
        for pet_path in self._pets:
            name = os.path.splitext(os.path.basename(pet_path))[0]
            # 翻译名称
            name_cn = {"pixel_pet": "紫发娘", "blonde": "金发娘",
                       "catgirl": "猫耳娘", "twin": "双马尾", "witch": "小魔女"}
            display = name_cn.get(name, name)
            action = pet_menu.addAction(display)
            action.setData(pet_path)
        pet_menu.triggered.connect(self._on_pet_select)

        # 快捷键说明
        menu.addAction("快捷键说明", self._show_shortcuts)

        menu.addSeparator()
        menu.addAction("退出", QApplication.quit)

        menu.exec_(pos)

        if overlay_was_visible:
            self.overlay.show()

    def _on_clipboard_menu(self, action):
        text = action.data()
        if isinstance(text, str):
            QApplication.clipboard().setText(text)
            self.key_panel.add_key("已复制")

    def _on_pet_select(self, action):
        path = action.data()
        if isinstance(path, str) and os.path.exists(path):
            self.pet.set_image(path)
            name = os.path.splitext(os.path.basename(path))[0]
            name_cn = {"pixel_pet": "紫发娘", "blonde": "金发娘",
                       "catgirl": "猫耳娘", "twin": "双马尾", "witch": "小魔女"}
            self.key_panel.add_key(name_cn.get(name, name))

    def _clear_clipboard_history(self):
        self._clipboard_history.clear()

    def _toggle(self):
        self.overlay.enabled = not self.overlay.enabled
        s = "开" if self.overlay.enabled else "关"
        self.key_panel.add_key(f"粒子: {s}")

    def _view_notes(self):
        dlg = QDialog()
        dlg.setWindowTitle("快捷便签")
        dlg.setWindowFlags(Qt.WindowStaysOnTopHint)
        dlg.resize(400, 300)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        if os.path.exists(self._notes_path):
            with open(self._notes_path, "r", encoding="utf-8") as f:
                text_edit.setText(f.read())
        else:
            text_edit.setText("(暂无便签)")

        btn = QDialogButtonBox(QDialogButtonBox.Ok)
        btn.accepted.connect(dlg.accept)

        layout = QVBoxLayout()
        layout.addWidget(text_edit)
        layout.addWidget(btn)
        dlg.setLayout(layout)
        dlg.exec_()

    def _add_note(self):
        text, ok = QInputDialog.getMultiLineText(
            None, "添加便签", "输入内容:",
            flags=Qt.WindowStaysOnTopHint,
        )
        if ok and text:
            timestamp = __import__('datetime').datetime.now().strftime("%m-%d %H:%M")
            line = f"[{timestamp}] {text}\n"
            os.makedirs(os.path.dirname(self._notes_path), exist_ok=True)
            with open(self._notes_path, "a", encoding="utf-8") as f:
                f.write(line)
            self.key_panel.add_key("便签已存")

    def _show_shortcuts(self):
        QMessageBox.information(
            None, "快捷键说明",
            "左键点击宠物 → 弹出菜单\n"
            "右键点击宠物 → 弹出菜单\n"
            "拖拽宠物 → 移动位置\n"
            "按键 → 显示在左侧面板\n"
            "Ctrl+C → 自动记录剪贴板\n"
            "鼠标移动 → 粒子拖尾",
        )

    def _cleanup(self):
        self.hook.stop()
        self.hook.wait()

    def show(self):
        self.overlay.show()
        self.pet.show()
        self.pet.raise_()
        self.key_panel.anchor_to(self.pet.pos())
        self.key_panel.show()


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
