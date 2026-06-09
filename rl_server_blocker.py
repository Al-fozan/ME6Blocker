from __future__ import annotations

import base64
import ctypes
import json
import math
import os
import platform
import subprocess
import sys
import threading
import requests
import webbrowser
import winreg
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QEasingCurve, Property, QPointF, QRectF, Qt, QTimer, Signal, QPropertyAnimation, QCoreApplication
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QIcon, QAction
from PySide6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QSystemTrayIcon,
    QMenu,
    QStyle,
    QRadioButton,
    QButtonGroup
)

ENCODED_WEBHOOK = "aHR0cHM6Ly9zY3JpcHQuZ29vZ2xlLmNvbS9tYWNyb3Mvcy9BS2Z5Y2J4N0hBSGlwV2RvaFNlRllzQnRsOVRTcmNCNWJsMXc5aE9QMWVhOTNDbllkX2lYNjRnMllwSmFXZ2tQNjBPakZ3eGc2US9leGVj"

APP_NAME = "ME6Blocker"
APP_VERSION = "v1.4.0" 
RULE_PREFIX = "ME6Blocker"
CONFIG_DIR = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "ME6Blocker")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# Minimalist Dark Theme Colors
APP_BG = "#0b0c10"
PANEL_BG = "#15161b"
TEXT_PRIMARY = "#ffffff"
TEXT_MUTED = "#8a8f9e"
GLOW_GREEN = "#00ff66"
GLOW_RED = "#ef4444"

# --- القاموس (Translations) ---
TR = {
    "en": {
        "status_off": "STATUS: OFF",
        "status_on": "BLOCKER: ACTIVE",
        "filter_path": "Filter by EXE Path",
        "hint": "(Enable only if it affects other apps)",
        "targets": "Targets Loaded",
        "report_bug": "🐞 Report Bug",
        "notice": "Notice: This application dynamically modifies Windows Firewall rules.",
        "settings": "⚙️ Settings",
        "close_behavior": "When clicking Close (X):",
        "close_exit": "Exit and Disable Blocker",
        "close_tray": "Minimize to Tray (Keep Blocker ON)",
        "startup_behavior": "Startup Behavior:",
        "run_startup": "Run automatically with Windows",
        "auto_enable": "Auto-enable Blocker on startup",
        "language": "Interface Language:",
        "save": "Save & Apply",
        "cancel": "Cancel",
        "update_title": "Update Available",
        "update_msg": "A new version ({v}) is available!\n\nWould you like to download it?",
        "btn_yes": "Yes, Download",
        "btn_skip": "Skip this version",
        "btn_no": "Remind me later",
        "tray_open": "Open ME6Blocker",
        "tray_exit": "Exit App (Disable Blocker)",
        "support_me": "💖 Support Me"
    },
    "ar": {
        "status_off": "الحالة: متوقف",
        "status_on": "الحظر: نشط ومفعل",
        "filter_path": "حظر للعبة فقط (تحديد المسار)",
        "hint": "(قم بتفعيله فقط إذا تأثرت البرامج الأخرى)",
        "targets": "النطاقات المحظورة",
        "report_bug": "🐞 الإبلاغ عن مشكلة",
        "notice": "ملاحظة: هذا البرنامج يقوم بتعديل قواعد جدار حماية ويندوز ديناميكياً.",
        "settings": "⚙️ الإعدادات",
        "close_behavior": "عند إغلاق البرنامج (زر X):",
        "close_exit": "إغلاق تام وإيقاف الحظر (الافتراضي)",
        "close_tray": "إخفاء للشريط السفلي (إبقاء الحظر يعمل)",
        "startup_behavior": "عند تشغيل الكمبيوتر:",
        "run_startup": "تشغيل البرنامج تلقائياً مع ويندوز",
        "auto_enable": "تفعيل الحظر تلقائياً عند التشغيل",
        "language": "لغة البرنامج:",
        "save": "حفظ وتطبيق",
        "cancel": "إلغاء",
        "update_title": "تحديث جديد متوفر",
        "update_msg": "توجد نسخة جديدة ({v}) متاحة!\n\nهل ترغب في تحميلها الآن؟",
        "btn_yes": "نعم، حمل التحديث",
        "btn_skip": "تخطي هذه النسخة",
        "btn_no": "ذكرني لاحقاً",
        "tray_open": "فتح نافذة البرنامج",
        "tray_exit": "إغلاق البرنامج وإيقاف الحظر",
        "support_me": "💖 ادعمني"
    }
}

DEFAULT_CONFIG = {
    "program_path": "",
    "use_program": False,
    "close_behavior": "exit",
    "run_startup": False,
    "auto_enable": False,
    "language": "en",
    "skipped_version": ""
}

def resource_path(relative_path: str) -> str:
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def load_config_dict() -> dict:
    config = DEFAULT_CONFIG.copy()
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception:
            pass
    return config

def save_config_dict(config: dict) -> None:
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f)
    except Exception:
        pass

def set_run_on_startup(enable: bool):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{sys.executable}"')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass

@dataclass(frozen=True)
class ServerTarget:
    name: str
    remote_ip: str
    protocol: str = "any"
    remote_port: str = "any"

# تحديث الايبيات تلقائيا 
TARGETS_URL = "https://gist.githubusercontent.com/Al-fozan/834f77cb5e1a8e7e2ce310159c8ba013/raw/ips.json"

# آيبيات احتياطية في حال ما كان فيه إنترنت عند المستخدم وقت تشغيل البرنامج
DEFAULT_TARGETS: list[ServerTarget] = [
    ServerTarget("Server Range 1", "34.164.0.0/16"),
    ServerTarget("Server Range 2", "34.165.0.0/16"),
    ServerTarget("Server Range 3", "35.252.0.0/16"),
]

# القائمة الأساسية اللي بيستخدمها البرنامج
SERVER_TARGETS: list[ServerTarget] = DEFAULT_TARGETS.copy()

def update_targets_from_cloud():
    global SERVER_TARGETS
    try:
        response = requests.get(TARGETS_URL, timeout=3)
        if response.status_code == 200:
            cloud_data = response.json()
            new_targets = []
            for item in cloud_data:
                new_targets.append(ServerTarget(item["name"], item["ip"]))
            
            if new_targets:
                SERVER_TARGETS = new_targets
    except Exception:
        pass

def now_stamp() -> str: return datetime.now().strftime("%H:%M:%S")

def is_admin() -> bool:
    try: return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception: return False

def relaunch_as_admin() -> bool:
    try:
        executable = sys.executable
        if getattr(sys, "frozen", False):
            parameters = " ".join(f'"{arg}"' for arg in sys.argv[1:])
        else:
            script_path = os.path.abspath(sys.argv[0])
            parameters = " ".join([f'"{script_path}"', *[f'"{arg}"' for arg in sys.argv[1:]]])
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, parameters, None, 1)
        return result > 32
    except Exception:
        return False

def run_netsh(args: list[str]) -> subprocess.CompletedProcess:
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return subprocess.run(
        ["netsh", "advfirewall", "firewall", *args],
        capture_output=True, text=True, check=False, startupinfo=startupinfo,
    )

def build_rule_name(target: ServerTarget, direction: str) -> str:
    return f"{RULE_PREFIX} - {target.remote_ip.replace('/', '_')} - {direction}"

def unblock_target(target: ServerTarget) -> tuple[bool, str]:
    run_netsh(["delete", "rule", f"name={build_rule_name(target, 'OUT')}"])
    run_netsh(["delete", "rule", f"name={build_rule_name(target, 'IN')}"])
    return True, f"Cleaned rules for {target.remote_ip}"

def block_target(target: ServerTarget, program_path: str | None = None) -> tuple[bool, str]:
    unblock_target(target)
    args_out = ["add", "rule", f"name={build_rule_name(target, 'OUT')}", "dir=out", "action=block", f"remoteip={target.remote_ip}", "protocol=any", "profile=any", "enable=yes"]
    args_in = ["add", "rule", f"name={build_rule_name(target, 'IN')}", "dir=in", "action=block", f"remoteip={target.remote_ip}", "protocol=any", "profile=any", "enable=yes"]
    if program_path:
        args_out.append(f"program={program_path}")
        args_in.append(f"program={program_path}")
    res_out = run_netsh(args_out)
    res_in = run_netsh(args_in)
    if res_out.returncode == 0 and res_in.returncode == 0:
        return True, f"Blocked {target.remote_ip} (IN/OUT)"
    return False, f"Failed to block {target.remote_ip}"

def block_all_targets(program_path: str | None = None) -> list[str]:
    return [f"[{'OK' if ok else 'ERR'}] {msg}" for target in SERVER_TARGETS for ok, msg in [block_target(target, program_path)]]

def unblock_all_targets() -> list[str]:
    return [f"[{'OK' if ok else 'ERR'}] {msg}" for target in SERVER_TARGETS for ok, msg in [unblock_target(target)]]

# --- نوافذ الواجهة ---
class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.lang = config.get("language", "en")
        self.t = TR[self.lang]
        
        self.setWindowTitle(self.t["settings"])
        self.resize(340, 420)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {APP_BG}; color: {TEXT_PRIMARY}; font-family: 'Segoe UI'; font-size: 12px; }}
            QLabel {{ color: {TEXT_PRIMARY}; }}
            QFrame#groupFrame {{ border: 1px solid #2f3540; border-radius: 6px; background-color: #12141a; }}
            QRadioButton, QCheckBox {{ background: transparent; spacing: 8px; color: {TEXT_PRIMARY}; }}
            QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 7px; border: 1px solid #414857; background: #1a1d24; }}
            QRadioButton::indicator:checked {{ background: {GLOW_GREEN}; border: 3px solid #1a1d24; }}
            QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid #414857; background: #1a1d24; }}
            QCheckBox::indicator:checked {{ background: {GLOW_GREEN}; border: 1px solid {GLOW_GREEN}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Close Behavior
        layout.addWidget(QLabel(f"<b>{self.t['close_behavior']}</b>"))
        frame1 = QFrame()
        frame1.setObjectName("groupFrame")
        lay1 = QVBoxLayout(frame1)
        lay1.setContentsMargins(12, 12, 12, 12)
        lay1.setSpacing(10)
        
        self.close_bg = QButtonGroup(self)
        self.radio_exit = QRadioButton(self.t["close_exit"])
        self.radio_tray = QRadioButton(self.t["close_tray"])
        self.close_bg.addButton(self.radio_exit)
        self.close_bg.addButton(self.radio_tray)
        if config.get("close_behavior") == "tray": self.radio_tray.setChecked(True)
        else: self.radio_exit.setChecked(True)
        lay1.addWidget(self.radio_exit)
        lay1.addWidget(self.radio_tray)
        layout.addWidget(frame1)

        # Startup Behavior
        layout.addWidget(QLabel(f"<b>{self.t['startup_behavior']}</b>"))
        frame2 = QFrame()
        frame2.setObjectName("groupFrame")
        lay2 = QVBoxLayout(frame2)
        lay2.setContentsMargins(12, 12, 12, 12)
        lay2.setSpacing(10)
        
        self.chk_startup = QCheckBox(self.t["run_startup"])
        self.chk_auto_enable = QCheckBox(self.t["auto_enable"])
        self.chk_startup.setChecked(config.get("run_startup", False))
        self.chk_auto_enable.setChecked(config.get("auto_enable", False))
        lay2.addWidget(self.chk_startup)
        lay2.addWidget(self.chk_auto_enable)
        layout.addWidget(frame2)

        # Language
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel(f"<b>{self.t['language']}</b>"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["English", "العربية"])
        self.combo_lang.setCurrentIndex(1 if self.lang == "ar" else 0)
        self.combo_lang.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid #2f3540; padding: 4px; color: {TEXT_PRIMARY};")
        lang_layout.addWidget(self.combo_lang)
        layout.addLayout(lang_layout)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton(self.t["save"])
        self.btn_cancel = QPushButton(self.t["cancel"])
        self.btn_save.setStyleSheet(f"background-color: {GLOW_GREEN}; color: #000; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_cancel.setStyleSheet("background-color: #272c38; color: #fff; padding: 8px; border-radius: 4px; border: 1px solid #2f3540;")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_updated_config(self) -> dict:
        self.config["close_behavior"] = "tray" if self.radio_tray.isChecked() else "exit"
        self.config["run_startup"] = self.chk_startup.isChecked()
        self.config["auto_enable"] = self.chk_auto_enable.isChecked()
        self.config["language"] = "ar" if self.combo_lang.currentIndex() == 1 else "en"
        return self.config

class BugReportDialog(QDialog):
    report_finished = Signal(bool, str)

    def __init__(self, logs: str, parent=None):
        super().__init__(parent)
        self.lang = parent.config.get("language", "en") if parent else "en"
        self.t = TR[self.lang]
        self.setWindowTitle(self.t["report_bug"])
        self.resize(400, 300)
        self.setStyleSheet(f"background-color: {APP_BG}; color: {TEXT_PRIMARY};")
        self.logs = logs

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("الرجاء وصف المشكلة:" if self.lang == "ar" else "Please describe the issue:"))
        self.desc_input = QTextEdit()
        self.desc_input.setStyleSheet("background-color: #12141a; border: 1px solid #2f3540; padding: 5px;")
        layout.addWidget(self.desc_input)

        self.submit_btn = QPushButton("إرسال" if self.lang == "ar" else "Submit Report")
        self.submit_btn.setStyleSheet("background-color: #1d212b; border: 1px solid #2f3540; border-radius: 6px; padding: 10px; font-weight: bold;")
        self.submit_btn.clicked.connect(self._send_report)
        layout.addWidget(self.submit_btn)

        self.report_finished.connect(self._on_report_finished)

    def _send_report(self):
        description = self.desc_input.toPlainText().strip()
        if not description: return
        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("جاري الإرسال..." if self.lang == "ar" else "Sending...")
        threading.Thread(target=self._post_data, args=(description,), daemon=True).start()

    def _post_data(self, description):
        try:
            if ENCODED_WEBHOOK == "ضع_النص_المشفر_هنا" or not ENCODED_WEBHOOK:
                self.report_finished.emit(False, "Webhook URL not configured.")
                return
            url = base64.b64decode(ENCODED_WEBHOOK).decode('utf-8')
            payload = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "app_version": APP_VERSION,
                "os_version": platform.platform(),
                "user_description": description,
                "logs": self.logs
            }
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code in (200, 201, 302):
                self.report_finished.emit(True, "Success")
            else:
                self.report_finished.emit(False, f"HTTP Error: {response.status_code}")
        except Exception as e:
            self.report_finished.emit(False, str(e))

    def _on_report_finished(self, success: bool, msg: str):
        if success:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", f"Failed:\n{msg}")
            self.submit_btn.setEnabled(True)
            self.submit_btn.setText("إرسال" if self.lang == "ar" else "Submit Report")


class PowerButton(QAbstractButton):
    glowLevelChanged = Signal(float)
    pressLevelChanged = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(280, 280) 
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._glow_level = 0.0
        self._press_level = 0.0
        self._pulse_phase = 0.0

        self._glow_animation = QPropertyAnimation(self, b"glowLevel", self)
        self._glow_animation.setDuration(320)
        self._glow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._press_animation = QPropertyAnimation(self, b"pressLevel", self)
        self._press_animation.setDuration(120)
        self._press_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(30)
        self._pulse_timer.timeout.connect(self._advance_pulse)

        self.pressed.connect(self._handle_pressed)
        self.released.connect(self._handle_released)
        self.toggled.connect(self._handle_toggled)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(50) 
        shadow.setOffset(0, 0) 
        shadow.setColor(QColor(0, 0, 0, 190))
        self.setGraphicsEffect(shadow)
        self._shadow_effect = shadow

    def _advance_pulse(self) -> None:
        self._pulse_phase += 0.18
        if self._pulse_phase > math.tau: self._pulse_phase -= math.tau
        self.update()

    def _handle_pressed(self) -> None:
        self._press_animation.stop()
        self._press_animation.setStartValue(self._press_level)
        self._press_animation.setEndValue(1.0)
        self._press_animation.start()

    def _handle_released(self) -> None:
        self._press_animation.stop()
        self._press_animation.setStartValue(self._press_level)
        self._press_animation.setEndValue(0.0)
        self._press_animation.start()

    def _handle_toggled(self, checked: bool) -> None:
        self._glow_animation.stop()
        self._glow_animation.setStartValue(self._glow_level)
        self._glow_animation.setEndValue(1.0 if checked else 0.0)
        self._glow_animation.start()
        if checked: self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
            self._pulse_phase = 0.0
        self._shadow_effect.setColor(QColor(0, 255, 102, 130) if checked else QColor(0, 0, 0, 190))
        self.update()

    def getGlowLevel(self) -> float: return self._glow_level
    def setGlowLevel(self, value: float) -> None:
        self._glow_level = value
        self.update()

    def getPressLevel(self) -> float: return self._press_level
    def setPressLevel(self, value: float) -> None:
        self._press_level = value
        self.update()

    glowLevel = Property(float, getGlowLevel, setGlowLevel)
    pressLevel = Property(float, getPressLevel, setPressLevel)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width, height = self.width(), self.height()
        center = QPointF(width / 2, height / 2)
        press_offset = 4 * self._press_level
        radius = min(width, height) / 2 - 50 
        
        bezel_rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        button_rect = bezel_rect.adjusted(10, 10, -10, -10)

        painter.setPen(QPen(QColor("#3b3f49"), 2))
        painter.setBrush(QColor("#2a2d36"))
        painter.drawEllipse(bezel_rect)

        glow = self._glow_level
        pulse = 0.85 + 0.15 * math.sin(self._pulse_phase) if self.isChecked() else 0.0
        halo_strength = glow * pulse

        if halo_strength > 0.01:
            halo_rect = bezel_rect.adjusted(-12, -12, 12, 12)
            painter.setPen(QPen(QColor(0, 255, 102, int(150 * halo_strength)), 8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(halo_rect)

        button_gradient = QLinearGradient(button_rect.topLeft(), button_rect.bottomRight())
        if glow < 0.1:
            button_gradient.setColorAt(0.0, QColor("#4a111a"))
            button_gradient.setColorAt(1.0, QColor("#1a0508"))
        else:
            button_gradient.setColorAt(0.0, QColor("#34d399"))
            button_gradient.setColorAt(1.0, QColor("#059669"))

        painter.translate(0, press_offset)
        painter.setPen(QPen(QColor(255, 255, 255, 36), 1))
        painter.setBrush(button_gradient)
        painter.drawEllipse(button_rect)

        mode_text = "ON" if self.isChecked() else "OFF"
        mode_color = QColor("#ecfdf5") if self.isChecked() else QColor("#fecaca")
        painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        painter.setPen(mode_color)
        painter.drawText(button_rect, Qt.AlignmentFlag.AlignCenter, mode_text)


class MainWindow(QMainWindow):
    update_found = Signal(str, str)  
    
    def __init__(self) -> None:
        super().__init__()
        self.config = load_config_dict()
        self.lang = self.config.get("language", "en")
        self.t = TR[self.lang]
        
        self.setWindowTitle(APP_NAME)
        self.resize(360, 780) 
        self.setMinimumSize(340, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 🚀 التعديل المضاف: استدعاء التحديث من السحابة هنا قبل فك الحظر وبناء الواجهة
        update_targets_from_cloud()

        unblock_all_targets()

        self._setup_tray_icon()
        self._build_ui()
        self._load_config_into_ui()
        self._apply_console_state(False, "System initialized.")

        # تطبيق خيار التشغيل التلقائي عند الفتح
        if self.config.get("auto_enable", False):
            QTimer.singleShot(500, lambda: self.power_button.setChecked(True))

        # فحص التحديثات مرة واحدة فقط عند بدء البرنامج
        self.update_found.connect(self._show_update_popup)
        threading.Thread(target=self._fetch_latest_version, daemon=True).start()

    def _setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        icon_path = resource_path("logo.ico")
        icon = QIcon(icon_path)
        
        if icon.isNull():
            icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
            
        self.tray_icon.setIcon(icon)
        self.setWindowIcon(icon) 
        
        tray_menu = QMenu()
        open_action = tray_menu.addAction(self.t["tray_open"])
        exit_action = tray_menu.addAction(self.t["tray_exit"])
        
        open_action.triggered.connect(self.show)
        exit_action.triggered.connect(self._force_exit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def _save_config(self) -> None:
        self.config["program_path"] = self.program_path_input.text().strip()
        self.config["use_program"] = bool(self.path_filter_switch.isChecked())
        save_config_dict(self.config)

    def _load_config_into_ui(self) -> None:
        self.program_path_input.setText(self.config.get("program_path", ""))
        self.path_filter_switch.blockSignals(True)
        self.path_filter_switch.setChecked(self.config.get("use_program", False))
        self.path_filter_switch.blockSignals(False)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self.central_widget)
        root_layout.setContentsMargins(22, 15, 22, 15)
        root_layout.setSpacing(15)

        # Header with Settings Button
        header_layout = QHBoxLayout()
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.clicked.connect(self._open_settings)
        header_layout.addWidget(self.settings_btn)
        
        title = QLabel(APP_NAME)
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)
        
        # Spacer for centering title
        spacer = QWidget()
        spacer.setFixedSize(30, 30)
        header_layout.addWidget(spacer)
        
        root_layout.addLayout(header_layout)

        # Centralized Power Button
        self.power_button = PowerButton()
        self.power_button.toggled.connect(self._on_power_toggled)
        root_layout.addWidget(self.power_button, 0, Qt.AlignmentFlag.AlignHCenter)

        # Status Label
        self.status_label = QLabel(self.t["status_off"])
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(self.status_label)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("divider")
        root_layout.addWidget(divider)

        # Config Section
        config_layout = QVBoxLayout()
        config_layout.setSpacing(8)
        
        switch_layout = QHBoxLayout()
        switch_layout.setContentsMargins(0, 0, 0, 0)
        self.path_filter_switch = QCheckBox(self.t["filter_path"])
        self.path_filter_switch.stateChanged.connect(self._save_config)
        switch_layout.addWidget(self.path_filter_switch)
        
        hint_label = QLabel(self.t["hint"])
        hint_label.setObjectName("hintLabel")
        switch_layout.addWidget(hint_label)
        switch_layout.addStretch() 
        config_layout.addLayout(switch_layout)

        path_row = QHBoxLayout()
        self.program_path_input = QLineEdit()
        self.program_path_input.setPlaceholderText("RocketLeague.exe path...")
        self.program_path_input.textChanged.connect(self._save_config)
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(40)
        browse_btn.clicked.connect(self._browse_program)
        path_row.addWidget(self.program_path_input)
        path_row.addWidget(browse_btn)
        config_layout.addLayout(path_row)

        ips_text = " | ".join([t.remote_ip for t in SERVER_TARGETS])
        target_info = QLabel(f"{self.t['targets']} ({len(SERVER_TARGETS)}):\n{ips_text}")
        target_info.setObjectName("targetInfo")
        target_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(target_info)
        
        root_layout.addLayout(config_layout)

        # Log Section
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(100)
        self.log_view.setObjectName("miniLog")
        root_layout.addWidget(self.log_view)

        # Bug Report
        self.bug_btn = QPushButton(self.t["report_bug"])
        self.bug_btn.clicked.connect(self._open_bug_report)
        root_layout.addWidget(self.bug_btn)

        # Footer Notice
        footer_notice = QLabel(self.t["notice"])
        footer_notice.setObjectName("footerNotice")
        footer_notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(footer_notice)

        # --- زر الدعم (Support Button) ---
        self.support_btn = QPushButton(self.t["support_me"])
        self.support_btn.setObjectName("supportBtn")
        self.support_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.support_btn.clicked.connect(self._open_support_link)
        root_layout.addWidget(self.support_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        self._apply_styles()
        
        self.version_label = QLabel(f"Version: {APP_VERSION}")
        self.version_label.setObjectName("versionLabel")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(self.version_label)

    def _open_support_link(self) -> None:
        webbrowser.open("https://creators.sa/fozy1")

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"""
            QWidget {{ color: {TEXT_PRIMARY}; font-family: "Segoe UI"; font-size: 11px; }}
            QMainWindow {{ background: {APP_BG}; }}
            #titleLabel {{ font-size: 24px; font-weight: bold; letter-spacing: 2px; }}
            #statusLabel {{ font-size: 13px; font-weight: 600; color: {TEXT_MUTED}; }}
            #divider {{ border-top: 1px solid #232630; }}
            #targetInfo {{ color: {GLOW_GREEN}; font-size: 10px; font-family: Consolas; line-height: 14px; padding: 4px; }}
            #footerNotice {{ color: {TEXT_MUTED}; font-size: 9px; font-style: italic; }}
            #versionLabel {{ color: {TEXT_MUTED}; font-size: 9px; }}
            #hintLabel {{ color: #8a8f9e; font-size: 10px; font-style: italic; margin-top: 1px; }}
            #settingsBtn {{ background: transparent; border: none; font-size: 18px; }}
            #settingsBtn:hover {{ color: {GLOW_GREEN}; }}
            QLineEdit {{ background-color: #12141a; border: 1px solid #2f3540; border-radius: 6px; padding: 6px; color: {TEXT_PRIMARY}; }}
            QPushButton {{ background-color: #1d212b; border: 1px solid #2f3540; border-radius: 6px; padding: 6px; font-weight: bold; }}
            QPushButton:hover {{ background-color: #272c38; }}
            
            /* ستايل زر الدعم */
            #supportBtn {{
                background-color: #1a1423;
                border: 1px solid #4a2b50;
                border-radius: 6px;
                padding: 6px 18px;
                color: #d4a5e3;
                font-weight: bold;
            }}
            #supportBtn:hover {{
                background-color: #261e35;
                border: 1px solid #6b3f75;
                color: #f1caff;
            }}
            
            QCheckBox {{ spacing: 8px; color: {TEXT_PRIMARY}; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid #414857; background: #12141a; }}
            QCheckBox::indicator:checked {{ background: {GLOW_GREEN}; border: 1px solid {GLOW_GREEN}; }}
            #miniLog {{ background-color: #0e1015; border: 1px solid #232630; border-radius: 8px; padding: 8px; font-family: Consolas; color: #a0a6b5; font-size: 10px; }}
        """)

    def _browse_program(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Game EXE", "", "Executable (*.exe);;All (*.*)")
        if path:
            self.program_path_input.setText(path)
            self._save_config()

    def _append_log(self, msg: str) -> None:
        self.log_view.appendPlainText(f"[{now_stamp()}] {msg}")
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def _apply_console_state(self, enabled: bool, detail: str) -> None:
        self.power_button.blockSignals(True)
        self.power_button.setChecked(enabled)
        self.power_button.blockSignals(False)
        self.power_button._handle_toggled(enabled)
        
        self.status_label.setText(self.t["status_on"] if enabled else self.t["status_off"])
        self.status_label.setStyleSheet(f"color: {GLOW_GREEN if enabled else TEXT_MUTED};")
        self._append_log(detail)

    def _revert_button(self) -> None:
        self.power_button.blockSignals(True)
        self.power_button.setChecked(False)
        self.power_button.blockSignals(False)
        self.power_button._handle_toggled(False)

    def _on_power_toggled(self, checked: bool) -> None:
        if checked and not is_admin():
            self._revert_button()
            QMessageBox.critical(self, APP_NAME, "Administrator privileges required.")
            self._append_log("ERR: Run as Admin required.")
            return

        try:
            program_path = self.program_path_input.text().strip() if self.path_filter_switch.isChecked() else None
            self._save_config()

            if checked:
                msgs = block_all_targets(program_path)
                self._apply_console_state(True, "Rules successfully injected.")
            else:
                msgs = unblock_all_targets()
                self._apply_console_state(False, "Rules successfully removed.")

            for m in msgs: self._append_log(m)
        except Exception as e:
            self._revert_button()
            self._append_log(f"ERR: {e}")

    def _open_settings(self) -> None:
        # save current language to check for changes later
        old_lang = self.config.get("language", "en")
        
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            new_config = dlg.get_updated_config()
            new_lang = new_config.get("language", "en")
            
            self.config.update(new_config)
            save_config_dict(self.config)
            set_run_on_startup(self.config.get("run_startup", False))
            
            
            if old_lang != new_lang:
                QMessageBox.information(self, "Restart Required", "Settings saved! Please restart the app to apply language changes." if self.lang == "en" else "تم الحفظ! يرجى إعادة تشغيل البرنامج لتطبيق تغيير اللغة.")

    def _open_bug_report(self) -> None:
        current_logs = self.log_view.toPlainText()
        dialog = BugReportDialog(current_logs, self)
        if dialog.exec():
            QMessageBox.information(self, "Success", "Bug report sent!" if self.lang == "en" else "تم إرسال التقرير بنجاح، شكراً لك.")
            self._append_log("Bug report submitted.")
    
    def _fetch_latest_version(self):
        try:
            url = "https://api.github.com/repos/Al-fozan/ME6Blocker/releases/latest"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "")
                release_url = data.get("html_url", "")
                
                skipped = self.config.get("skipped_version", "")
                if latest_version and latest_version != APP_VERSION and latest_version != skipped:
                    self.update_found.emit(latest_version, release_url)
        except Exception:
            pass

    def _show_update_popup(self, latest_version: str, release_url: str):
        msg = QMessageBox(self)
        msg.setWindowTitle(self.t["update_title"])
        msg.setText(self.t["update_msg"].format(v=latest_version))
        msg.setStyleSheet(f"background-color: {APP_BG}; color: {TEXT_PRIMARY};")
        
        btn_yes = msg.addButton(self.t["btn_yes"], QMessageBox.ButtonRole.AcceptRole)
        btn_skip = msg.addButton(self.t["btn_skip"], QMessageBox.ButtonRole.RejectRole)
        btn_no = msg.addButton(self.t["btn_no"], QMessageBox.ButtonRole.RejectRole)
        
        msg.exec()
        
        clicked = msg.clickedButton()
        if clicked == btn_yes:
            webbrowser.open(release_url)  
        elif clicked == btn_skip:
            self.config["skipped_version"] = latest_version
            save_config_dict(self.config)

    def closeEvent(self, event) -> None:
        if self.config.get("close_behavior") == "tray":
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(APP_NAME, "Running in background..." if self.lang == "en" else "البرنامج يعمل في الخلفية...", QSystemTrayIcon.MessageIcon.Information, 2000)
        else:
            self._force_exit()

    def _force_exit(self):
        if self.power_button.isChecked():
            unblock_all_targets()
        QCoreApplication.quit()


def main() -> None:
    if sys.platform != "win32": return
    if not is_admin():
        if relaunch_as_admin(): return
        app = QApplication([])
        QMessageBox.critical(None, APP_NAME, "Restart as Administrator required.")
        app.quit()
        return

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    config = load_config_dict()
    if config.get("language") == "ar":
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()