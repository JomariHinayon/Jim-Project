import sys
import os
import time
import random
import threading
from datetime import datetime
import re
import warnings
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QSpinBox, QTextEdit, QMessageBox, QGroupBox, QHBoxLayout, QSizePolicy, QProgressBar, QFrame, QScrollArea
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon, QFont, QPixmap, QTextCursor
from twilio.rest import Client
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=DeprecationWarning)

def resource_path(relative_path):
    # Get absolute path to resource, works for dev and for PyInstaller
    import sys, os
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

LOGO_PATH = resource_path('sms logo.png')

# Load environment variables from .env
load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_SENDER_NUMBERS = os.getenv('TWILIO_SENDER_NUMBERS', '').split(',')

def is_valid_uk_phone(phone):
    return phone.startswith('+44') and phone[1:].isdigit() and len(phone) >= 12

def generate_generic_sender():
    return f'+4477009{random.randint(10000,99999)}'

def format_log_line(status, sender, recipient, reason=None):
    time_str = datetime.now().strftime('%H:%M:%S')
    if status == "SENT":
        return f"<span style='color:#107c10;'>✅ [{time_str}] From: <b>{sender}</b> → To: <b>{recipient}</b></span>"
    elif status == "FAILED":
        return f"<span style='color:#e81123;'>❌ [{time_str}] From: <b>{sender}</b> → To: <b>{recipient}</b> <i>({reason})</i></span>"
    elif status == "RETRY":
        return f"<span style='color:#ff8c00;'>🔁 [{time_str}] RETRY From: <b>{sender}</b> → To: <b>{recipient}</b></span>"
    else:
        return f"[{time_str}] {status}: {sender} → {recipient}"

class SMSSenderThread(QThread):
    progress = pyqtSignal(int, int, str, str, str, str)  # sent, total, sender, recipient, status, reason
    finished = pyqtSignal(int, int)
    failed = pyqtSignal(str)

    def __init__(self, recipient, num_texts, log_enabled, parent=None):
        super().__init__(parent)
        self.recipient = recipient
        self.num_texts = num_texts
        self.log_enabled = log_enabled
        self._stop_event = threading.Event()
        self.twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.sender_numbers = [num.strip() for num in TWILIO_SENDER_NUMBERS if num.strip()]

    def run(self):
        sent = 0
        failed = 0
        log_path = f"logs/sms_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        for i in range(self.num_texts):
            if self._stop_event.is_set():
                break
            sender = random.choice(self.sender_numbers) if self.sender_numbers else None
            try:
                message = self.twilio_client.messages.create(
                    body="Hi Jim This Tested from the Software",  # Updated message body
                    from_=sender,
                    to=self.recipient
                )
                sent += 1
                if self.log_enabled:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"SENT: {sender} -> {self.recipient} [{datetime.now()}] SID: {message.sid}\n")
                self.progress.emit(sent, i+1, sender, self.recipient, "SENT", None)
            except Exception as e:
                failed += 1
                if self.log_enabled:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"FAILED: {sender} -> {self.recipient} [{datetime.now()}] Reason: {str(e)}\n")
                self.progress.emit(sent, i+1, sender, self.recipient, "FAILED", str(e))
                self.failed.emit(f"Failed to send from {sender}: {str(e)}")
            time.sleep(0.1)  # Throttle
        self.finished.emit(sent, failed)

    def stop(self):
        self._stop_event.set()

class CollapsibleLog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.expanded = False
        self.toggle_btn = QPushButton('Show Log ▼')
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setStyleSheet('QPushButton { background: #f3f3f3; border: none; color: #0078d7; font-weight: bold; padding-top: 8px; padding-bottom: 8px; }')
        self.toggle_btn.clicked.connect(self.toggle)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 10))
        self.log_area.setStyleSheet("background: #fafcff; border: 1px solid #e0e0e0; border-radius: 4px; margin-top: 8px;")
        self.log_area.setMinimumHeight(120)
        self.log_area.setVisible(False)
        layout = QVBoxLayout()
        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.log_area)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
    def toggle(self):
        self.expanded = not self.expanded
        self.log_area.setVisible(self.expanded)
        self.toggle_btn.setText('Hide Log ▲' if self.expanded else 'Show Log ▼')
    def append(self, text):
        self.log_area.append(text)
        self.log_area.moveCursor(QTextCursor.End)
    def clear(self):
        self.log_area.clear()

class SMSTab(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout()
        # Header with logo and app name
        header_layout = QHBoxLayout()
        logo_label = QLabel()
        if os.path.exists(LOGO_PATH):
            pixmap = QPixmap(LOGO_PATH)
            logo_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header_layout.addWidget(logo_label)
        header_title = QLabel("<span style='font-size:22pt; font-weight:600; color:#0078d7;'>SMS Delivery Tester</span>")
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(12)
        # Card-like main panel
        card = QFrame()
        card.setStyleSheet("QFrame { background: #fff; border-radius: 16px; border: 1.5px solid #e0e0e0; }")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(32, 32, 32, 32)
        # Form
        form_layout = QFormLayout()
        self.recipient = QLineEdit()
        self.recipient.setPlaceholderText("Recipient UK phone number (e.g. +447700900001)")
        self.recipient.setToolTip("Enter the recipient's UK phone number (+44...)")
        self.recipient.setMinimumHeight(32)
        self.recipient.setFont(QFont("Segoe UI", 11))
        self.recipient.textChanged.connect(self.validate_inputs)
        self.num_texts = QSpinBox()
        self.num_texts.setMaximum(1000)
        self.num_texts.setMinimum(1)
        self.num_texts.setToolTip("Number of texts to send (max 1,000)")
        self.num_texts.setMinimumHeight(32)
        self.num_texts.setFont(QFont("Segoe UI", 11))
        self.num_texts.valueChanged.connect(self.validate_inputs)
        form_layout.addRow(QLabel("<b>Recipient Phone (+44):</b>"), self.recipient)
        form_layout.addRow(QLabel("<b>Number of Texts:</b>"), self.num_texts)
        card_layout.addLayout(form_layout)
        # Buttons
        btn_layout = QHBoxLayout()
        self.launch = QPushButton("Launch")
        self.launch.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; padding: 10px 32px; border-radius: 8px; font-size: 12pt;")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("background-color: #e81123; color: white; font-weight: bold; padding: 10px 32px; border-radius: 8px; font-size: 12pt;")
        self.stop_btn.setEnabled(False)
        self.launch.setToolTip("Start sending SMS.")
        self.stop_btn.setToolTip("Stop sending SMS.")
        self.launch.clicked.connect(self.start_sending)
        self.stop_btn.clicked.connect(self.stop_sending)
        btn_layout.addWidget(self.launch)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)
        card_layout.addSpacing(10)
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet("QProgressBar { border: 1px solid #bbb; border-radius: 8px; background: #f5f5f5; height: 18px; } QProgressBar::chunk { background: #0078d7; border-radius: 8px; }")
        card_layout.addWidget(self.progress)
        # Status/Summary panel
        self.status = QLabel()
        self.status.setFont(QFont("Segoe UI", 11))
        self.status.setStyleSheet("padding: 12px; background: #f5f5f5; border: 1px solid #ddd; border-radius: 8px; margin-top: 8px;")
        self.status.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.status.setMinimumHeight(32)
        card_layout.addWidget(self.status)
        # Collapsible log area
        self.log_widget = CollapsibleLog()
        card_layout.addWidget(self.log_widget)
        card.setLayout(card_layout)
        main_layout.addWidget(card)
        main_layout.addStretch()
        self.setLayout(main_layout)
        self.thread = None
        self.log_lines = []
        self.validate_inputs()

    def validate_inputs(self):
        phone = self.recipient.text()
        valid = is_valid_uk_phone(phone)
        if not phone:
            self.recipient.setStyleSheet("")
            self.launch.setEnabled(False)
            self.status.setText("")
        elif not valid:
            self.recipient.setStyleSheet("border: 2px solid #e81123;")
            self.recipient.setToolTip("Invalid UK phone number.")
            self.launch.setEnabled(False)
            self.status.setText("<span style='color:#e81123;'>Invalid UK phone number.</span>")
        else:
            self.recipient.setStyleSheet("")
            self.recipient.setToolTip("Valid UK phone number.")
            self.launch.setEnabled(True)
            self.status.setText("")

    def start_sending(self):
        if not self.recipient.text() or not is_valid_uk_phone(self.recipient.text()):
            QMessageBox.warning(self, "Input Error", "Please enter a valid UK phone number (+44...)")
            return
        self.status.setText("<span style='color:#0078d7;'>Sending...</span>")
        self.log_widget.clear()
        self.log_lines = []
        self.progress.setValue(0)
        self.launch.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.thread = SMSSenderThread(
            self.recipient.text(),
            self.num_texts.value(),
            True
        )
        self.thread.progress.connect(self.update_status)
        self.thread.finished.connect(self.finish_status)
        self.thread.failed.connect(self.show_error)
        self.thread.start()

    def stop_sending(self):
        if self.thread:
            self.thread.stop()
            self.status.setText("<span style='color:#e81123;'>Stopped by user.</span>")
            self.launch.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def update_status(self, sent, total, sender=None, recipient=None, status=None, reason=None):
        percent = int((total / max(1, self.num_texts.value())) * 100)
        self.progress.setValue(percent)
        self.status.setText(f"<span style='color:#0078d7;'>Sent: {sent}/{total}</span>")
        if sender and recipient and status:
            line = format_log_line(status, sender, recipient, reason)
        else:
            line = f"Sent: {sent}/{total}"
            self.log_widget.append(line)
            self.log_lines.append(line)

    def finish_status(self, sent, failed):
        color = "#107c10" if failed == 0 else "#e81123"
        summary = f"<b>Summary:</b> <span style='color:{color};'>Sent: {sent}, Failed: {failed}</span>"
        self.status.setText(summary)
        self.log_widget.append(f"Done. Sent: {sent}, Failed: {failed}")
        self.log_lines.append(f"Done. Sent: {sent}, Failed: {failed}")
        self.launch.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setValue(100)

    def show_error(self, msg):
        self.status.setText(f"<span style='color:#e81123;'>Error: {msg}</span>")
        self.log_widget.append(f"Error: {msg}")
        self.log_lines.append(f"Error: {msg}")

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delivery Testing App - SMS Only")
        if os.path.exists(LOGO_PATH):
            self.setWindowIcon(QIcon(LOGO_PATH))
        self.setStyleSheet("QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11pt; background: #f8fafd; } QGroupBox { font-weight: bold; border: 1.5px solid #e0e0e0; border-radius: 16px; margin-top: 8px; background: #ffffff; } QGroupBox:title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; background: #f8fafd; } QPushButton { min-width: 80px; } QLabel { min-height: 24px; }")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        self.sms_tab = SMSTab()
        layout.addWidget(self.sms_tab)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_()) 