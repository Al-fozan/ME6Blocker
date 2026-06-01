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
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QEasingCurve, Property, QPointF, QRectF, Qt, QTimer, Signal, QPropertyAnimation
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
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
)


ENCODED_WEBHOOK = "aHR0cHM6Ly9zY3JpcHQuZ29vZ2xlLmNvbS9tYWNyb3Mvcy9BS2Z5Y2J4N0hBSGlwV2RvaFNlRllzQnRsOVRTcmNCNWJsMXc5aE9QMWVhOTNDbllkX2lYNjRnMllwSmFXZ2tQNjBPakZ3eGc2US9leGVj"

APP_NAME = "ME6Blocker"
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


@dataclass(frozen=True)
class ServerTarget:
    name: str
    remote_ip: str
    protocol: str = "any"
    remote_port: str = "any"

SERVER_TARGETS: list[ServerTarget] = [
    ServerTarget("Server Range 1", "34.164.0.0/16"),
    ServerTarget("Server Range 2", "34.165.0.0/16"),
    ServerTarget("Server Range 3", "35.252.0.0/16"),
]

def now_stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")

def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

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
    startupinfo.wShowWindow = 0  # SW_HIDE

    return subprocess.run(
        ["netsh", "advfirewall", "firewall", *args],
        capture_output=True,
        text=True,
        check=False,
        startupinfo=startupinfo,
    )

def build_rule_name(target: ServerTarget, direction: str) -> str:
    return f"{RULE_PREFIX} - {target.remote_ip.replace('/', '_')} - {direction}"

def unblock_target(target: ServerTarget) -> tuple[bool, str]:
    rule_out = build_rule_name(target, "OUT")
    rule_in = build_rule_name(target, "IN")
    
    run_netsh(["delete", "rule", f"name={rule_out}"])
    run_netsh(["delete", "rule", f"name={rule_in}"])
    return True, f"Cleaned rules for {target.remote_ip}"

def block_target(target: ServerTarget, program_path: str | None = None) -> tuple[bool, str]:
    unblock_target(target)
    
    rule_out = build_rule_name(target, "OUT")
    rule_in = build_rule_name(target, "IN")

    args_out = [
        "add", "rule", f"name={rule_out}", "dir=out", "action=block",
        f"remoteip={target.remote_ip}", "protocol=any", "profile=any", "enable=yes"
    ]
    args_in = [
        "add", "rule", f"name={rule_in}", "dir=in", "action=block",
        f"remoteip={target.remote_ip}", "protocol=any", "profile=any", "enable=yes"
    ]

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


# --- نافذة تقرير الأخطاء الجديدة ---
class BugReportDialog(QDialog):
    report_finished = Signal(bool, str)

    def __init__(self, logs: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report a Bug")
        self.resize(400, 300)
        self.setStyleSheet(f"background-color: {APP_BG}; color: {TEXT_PRIMARY};")
        self.logs = logs

        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Please describe the issue you are facing:"))
        self.desc_input = QTextEdit()
        self.desc_input.setStyleSheet("background-color: #12141a; border: 1px solid #2f3540; padding: 5px;")
        layout.addWidget(self.desc_input)

        self.submit_btn = QPushButton("Submit Report")
        self.submit_btn.setStyleSheet("background-color: #1d212b; border: 1px solid #2f3540; border-radius: 6px; padding: 10px; font-weight: bold;")
        self.submit_btn.clicked.connect(self._send_report)
        layout.addWidget(self.submit_btn)

        self.report_finished.connect(self._on_report_finished)

    def _send_report(self):
        description = self.desc_input.toPlainText().strip()
        if not description:
            QMessageBox.warning(self, "Warning", "Please enter a description.")
            return
            
        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("Sending...")
        
        # تشغيل الإرسال في مسار خلفي (Thread) عشان ما يعلق البرنامج
        threading.Thread(target=self._post_data, args=(description,), daemon=True).start()

    def _post_data(self, description):
        try:
            if ENCODED_WEBHOOK == "ضع_النص_المشفر_هنا" or not ENCODED_WEBHOOK:
                self.report_finished.emit(False, "Webhook URL not configured in code.")
                return

            url = base64.b64decode(ENCODED_WEBHOOK).decode('utf-8')
            payload = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "app_version": "v1.0.0",
                "os_version": platform.platform(),
                "user_description": description,
                "logs": self.logs
            }
            # إرسال الطلب لجوجل
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
            QMessageBox.warning(self, "Error", f"Failed to send report:\n{msg}")
            self.submit_btn.setEnabled(True)
            self.submit_btn.setText("Submit Report")


class PowerButton(QAbstractButton):
    glowLevelChanged = Signal(float)
    pressLevelChanged = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(200, 200)
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
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 190))
        self.setGraphicsEffect(shadow)
        self._shadow_effect = shadow

    def _advance_pulse(self) -> None:
        self._pulse_phase += 0.18
        if self._pulse_phase > math.tau:
            self._pulse_phase -= math.tau
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

        if checked:
            self._pulse_timer.start()
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

        width = self.width()
        height = self.height()
        center = QPointF(width / 2, height / 2)
        press_offset = 4 * self._press_level
        radius = min(width, height) / 2 - 10
        bezel_rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        button_rect = bezel_rect.adjusted(10, 10, -10, -10)

        # Bezel
        painter.setPen(QPen(QColor("#3b3f49"), 2))
        painter.setBrush(QColor("#2a2d36"))
        painter.drawEllipse(bezel_rect)

        glow = self._glow_level
        pulse = 0.85 + 0.15 * math.sin(self._pulse_phase) if self.isChecked() else 0.0
        halo_strength = glow * pulse

        # Halo Glow
        if halo_strength > 0.01:
            halo_rect = bezel_rect.adjusted(-12, -12, 12, 12)
            painter.setPen(QPen(QColor(0, 255, 102, int(150 * halo_strength)), 8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(halo_rect)

        # Button Surface
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
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(360, 780) # زدت الطول شوي عشان الزر الجديد
        self.setMinimumSize(340, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self._build_ui()
        self._load_config_into_ui()
        self._apply_console_state(False, "System initialized.")

    def _load_config(self) -> tuple[str, bool]:
        if not os.path.isfile(CONFIG_FILE):
            return "", False
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            return str(config.get("program_path", "")), bool(config.get("use_program", False))
        except Exception:
            return "", False

    def _save_config(self) -> None:
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "program_path": self.program_path_input.text().strip(),
                    "use_program": bool(self.path_filter_switch.isChecked()),
                }, f)
        except Exception:
            pass

    def _load_config_into_ui(self) -> None:
        path, use_prog = self._load_config()
        self.program_path_input.setText(path)
        self.path_filter_switch.blockSignals(True)
        self.path_filter_switch.setChecked(use_prog)
        self.path_filter_switch.blockSignals(False)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self.central_widget)
        root_layout.setContentsMargins(22, 25, 22, 15)
        root_layout.setSpacing(15)

        # Header Title
        title = QLabel(APP_NAME)
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(title)

        # Centralized Power Button
        self.power_button = PowerButton()
        self.power_button.toggled.connect(self._on_power_toggled)
        root_layout.addWidget(self.power_button, 0, Qt.AlignmentFlag.AlignHCenter)

        # Status Label
        self.status_label = QLabel("STATUS: OFF")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(self.status_label)

        # Divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("divider")
        root_layout.addWidget(divider)

        # Config Section
        config_layout = QVBoxLayout()
        config_layout.setSpacing(8)

        self.path_filter_switch = QCheckBox("Filter by EXE Path")
        self.path_filter_switch.stateChanged.connect(self._save_config)
        config_layout.addWidget(self.path_filter_switch)

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
        target_info = QLabel(f"Targets Loaded ({len(SERVER_TARGETS)} Ranges):\n{ips_text}")
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

        # 🐞 زر التبليغ عن الأخطاء الجديد 🐞
        self.bug_btn = QPushButton("🐞 Report Bug")
        self.bug_btn.clicked.connect(self._open_bug_report)
        root_layout.addWidget(self.bug_btn)

        # Footer Notice
        footer_notice = QLabel("Notice: This application dynamically modifies Windows Firewall rules.")
        footer_notice.setObjectName("footerNotice")
        footer_notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(footer_notice)

        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"""
            QWidget {{ color: {TEXT_PRIMARY}; font-family: "Segoe UI"; font-size: 11px; }}
            QMainWindow {{ background: {APP_BG}; }}
            #titleLabel {{ font-size: 24px; font-weight: bold; letter-spacing: 2px; }}
            #statusLabel {{ font-size: 13px; font-weight: 600; color: {TEXT_MUTED}; }}
            #divider {{ border-top: 1px solid #232630; }}
            #targetInfo {{ color: {GLOW_GREEN}; font-size: 10px; font-family: Consolas; line-height: 14px; padding: 4px; }}
            #footerNotice {{ color: {TEXT_MUTED}; font-size: 9px; font-style: italic; }}
            QLineEdit {{
                background-color: #12141a; border: 1px solid #2f3540;
                border-radius: 6px; padding: 6px; color: {TEXT_PRIMARY};
            }}
            QPushButton {{
                background-color: #1d212b; border: 1px solid #2f3540;
                border-radius: 6px; padding: 6px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #272c38; }}
            QCheckBox {{ spacing: 8px; color: {TEXT_PRIMARY}; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid #414857; background: #12141a; }}
            QCheckBox::indicator:checked {{ background: {GLOW_GREEN}; border: 1px solid {GLOW_GREEN}; }}
            #miniLog {{
                background-color: #0e1015; border: 1px solid #232630;
                border-radius: 8px; padding: 8px; font-family: Consolas;
                color: #a0a6b5; font-size: 10px;
            }}
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
        
        self.status_label.setText("BLOCKER: ACTIVE" if enabled else "BLOCKER: DISABLED")
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

    # --- دالة فتح نافذة التبليغ ---
    def _open_bug_report(self) -> None:
        current_logs = self.log_view.toPlainText()
        dialog = BugReportDialog(current_logs, self)
        if dialog.exec():
            QMessageBox.information(self, "Success", "Bug report sent successfully! Thank you.")
            self._append_log("Bug report submitted.")


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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()