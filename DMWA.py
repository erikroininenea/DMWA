import sys
from tkinter import *
from win32api import GetSystemMetrics
import ctypes
import numpy as np
import cv2
import mss
import random
from PyQt6 import QtWidgets, QtGui, QtCore
import threading
import pygame
import urllib.request
import tempfile
import keyboard
import subprocess
import atexit


# ⚠️ OBS: detta blockar INTE Win pålitligt, men lämnas kvar som du hade det
keyboard.block_key('windows')


# ---------- EXPLORER KONTROLL ----------
def stop_explorer():
    try:
        subprocess.run(
            ["taskkill", "/f", "/im", "explorer.exe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True
        )
    except:
        pass


def start_explorer():
    try:
        subprocess.Popen(
            ["explorer.exe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True
        )
    except:
        pass


# 🔒 Säkerställ att explorer ALLTID återställs vid exit
atexit.register(start_explorer)


# ---------- WINDOWS POPUP ----------
def show_blocking_popup():
    flags = 0x30 | 0x40000 | 0x1000  # WARNING | TOPMOST | SYSTEM MODAL

    def message_loop():
        ctypes.windll.user32.MessageBoxW(
            0,
            "Programmet körs, du kan inte stänga detta!",
            "Varning",
            flags
        )
        threading.Thread(target=message_loop, daemon=True).start()

    threading.Thread(target=message_loop, daemon=True).start()


# ---------- LJUD ----------
def play_background_sound(url):
    try:
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        urllib.request.urlretrieve(url, tmp_file.name)
        tmp_file.close()

        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.music.load(tmp_file.name)
        pygame.mixer.music.set_volume(0.3)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print("Fel vid ljuduppspelning:", e)


# ---------- OVERLAY ----------
class ScreenOverlay(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.WindowStaysOnTopHint
        )

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        # FULL fokus
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.grabKeyboard()

        screen = QtWidgets.QApplication.primaryScreen()
        self.setGeometry(screen.geometry())

        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]

        self.frame = None

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.grab_frame)
        self.timer.start(30)

        self.focus_timer = QtCore.QTimer(self)
        self.focus_timer.timeout.connect(self.force_focus)
        self.focus_timer.start(200)

    def force_focus(self):
        self.raise_()
        self.activateWindow()

    def apply_effects(self, frame):
        b, g, r = cv2.split(frame)
        shift = random.randint(2, 6)
        b = np.roll(b, shift, axis=1)
        r = np.roll(r, -shift, axis=1)
        merged = cv2.merge([b, g, r])

        rows, cols, _ = merged.shape
        for i in range(0, rows, 10):
            offset = random.randint(-5, 5)
            merged[i:i+5] = np.roll(merged[i:i+5], offset, axis=1)

        noise = np.random.randint(-20, 20, merged.shape, dtype='int16')
        merged = merged.astype('int16') + noise
        merged = np.clip(merged, 0, 255).astype('uint8')

        return cv2.addWeighted(frame, 0.7, merged, 0.3, 0)

    def grab_frame(self):
        sct_img = self.sct.grab(self.monitor)
        frame = np.array(sct_img)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        frame = self.apply_effects(frame)

        max_shake = 5
        h, w, _ = frame.shape
        x_offset = max(0, random.randint(-max_shake, max_shake))
        y_offset = max(0, random.randint(-max_shake, max_shake))

        canvas = np.zeros_like(frame)
        canvas[y_offset:y_offset+h, x_offset:x_offset+w] = frame[:h - y_offset, :w - x_offset]

        self.frame = canvas
        self.update()

    def paintEvent(self, event):
        if self.frame is None:
            return
        painter = QtGui.QPainter(self)
        h, w, _ = self.frame.shape
        qImg = QtGui.QImage(
            self.frame.data, w, h, 3 * w,
            QtGui.QImage.Format.Format_BGR888
        )
        painter.drawImage(0, 0, qImg)

    # 🔒 ENDA EXIT: CTRL + Q
    def keyPressEvent(self, event):
        if (
            event.key() == QtCore.Qt.Key.Key_Q and
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            QtWidgets.QApplication.quit()
        else:
            event.accept()

    def closeEvent(self, event):
        event.ignore()


# ---------- MAIN ----------
if __name__ == "__main__":
    sound_url = "https://raw.githubusercontent.com/erikroininenea/DMWA/refs/heads/main/bgnoise.mp3"
    threading.Thread(target=play_background_sound, args=(sound_url,), daemon=True).start()

    app = QtWidgets.QApplication(sys.argv)
    overlay = ScreenOverlay()
    overlay.showFullScreen()

    # Popup
    QtCore.QTimer.singleShot(100, show_blocking_popup)

    # ❗ Stoppa explorer efter 10 sekunder
    QtCore.QTimer.singleShot(1000, stop_explorer)

    sys.exit(app.exec())
