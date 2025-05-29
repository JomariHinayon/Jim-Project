import sys
import os
import time
import smtplib
from email.message import EmailMessage
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QSpinBox, QTextEdit, QFileDialog, QMessageBox, QGroupBox, QHBoxLayout, QSizePolicy, QProgressBar, QFrame
)
from PyQt5.QtCore import QThread, pyqtSignal
from datetime import datetime
import threading
import random
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor
import warnings
import re
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- Utility Functions ---
def load_senders(filename):
    """Load sender identities from a file (one per line)."""
    if not os.path.exists(filename):
        return []
    with open(filename, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def log_message(logfile, content):
    os.makedirs(os.path.dirname(logfile), exist_ok=True)
    with open(logfile, 'a', encoding='utf-8') as f:
        f.write(content + '\n')

def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)

def is_valid_uk_phone(phone):
    return phone.startswith('+44') and phone[1:].isdigit() and len(phone) >= 12

# --- Email Sending Thread ---
class EmailSenderThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int, int)
    failed = pyqtSignal(str)

    def __init__(self, recipient, num_emails, senders, log_enabled, parent=None):
        super().__init__(parent)
        self.recipient = recipient
        self.num_emails = num_emails
        self.senders = senders
        self.log_enabled = log_enabled
        self._stop_event = threading.Event()

    def run(self):
        sent = 0
        failed = 0
        log_path = f"logs/email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        for i in range(self.num_emails):
            if self._stop_event.is_set():
                break
            sender = self.senders[i % len(self.senders)]
            msg = EmailMessage()
            msg['Subject'] = f"Test Email {i+1}"
            msg['From'] = sender
            msg['To'] = self.recipient
            msg.set_content(f"This is a test email number {i+1}.")
            try:
                with smtplib.SMTP('localhost', 1025, timeout=10) as server:
                    server.send_message(msg)
                sent += 1
                if self.log_enabled:
                    log_message(log_path, f"SENT: {sender} -> {self.recipient} [{datetime.now()}]")
            except Exception as e:
                failed += 1
                if self.log_enabled:
                    log_message(log_path, f"FAILED: {sender} -> {self.recipient} [{datetime.now()}] Reason: {e}")
                self.failed.emit(f"Failed to send from {sender}: {e}")
                # Basic retry logic: try once more after a short delay
                time.sleep(1)
                try:
                    with smtplib.SMTP('localhost', 1025, timeout=10) as server:
                        server.send_message(msg)
                    sent += 1
                    if self.log_enabled:
                        log_message(log_path, f"RETRY SENT: {sender} -> {self.recipient} [{datetime.now()}]")
                except Exception as e2:
                    if self.log_enabled:
                        log_message(log_path, f"RETRY FAILED: {sender} -> {self.recipient} [{datetime.now()}] Reason: {e2}")
            self.progress.emit(sent, i+1)
            time.sleep(0.1)  # Throttle to avoid flooding
        self.finished.emit(sent, failed)

    def stop(self):
        self._stop_event.set()

# --- SMS Sending Thread (Simulated) ---
class SMSSenderThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int, int)
    failed = pyqtSignal(str)

    def __init__(self, recipient, num_texts, senders, log_enabled, parent=None):
        super().__init__(parent)
        self.recipient = recipient
        self.num_texts = num_texts
        self.senders = senders
        self.log_enabled = log_enabled
        self._stop_event = threading.Event()

    def run(self):
        sent = 0
        failed = 0
        log_path = f"logs/sms_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        for i in range(self.num_texts):
            if self._stop_event.is_set():
                break
            sender = self.senders[i % len(self.senders)]
            # Simulate random failure
            if random.random() < 0.02:  # 2% chance to fail
                failed += 1
                if self.log_enabled:
                    log_message(log_path, f"FAILED: {sender} -> {self.recipient} [{datetime.now()}] Reason: Simulated failure")
                self.failed.emit(f"Failed to send from {sender} (simulated)")
                # Basic retry logic
                time.sleep(1)
                if random.random() < 0.5:
                    sent += 1
                    if self.log_enabled:
                        log_message(log_path, f"RETRY SENT: {sender} -> {self.recipient} [{datetime.now()}]")
                else:
                    if self.log_enabled:
                        log_message(log_path, f"RETRY FAILED: {sender} -> {self.recipient} [{datetime.now()}] Reason: Simulated failure")
            else:
                sent += 1
                if self.log_enabled:
                    log_message(log_path, f"SENT: {sender} -> {self.recipient} [{datetime.now()}]")
            self.progress.emit(sent, i+1)
            time.sleep(0.1)  # Throttle
        self.finished.emit(sent, failed)

    def stop(self):
        self._stop_event.set()

# --- Email Tab ---
class EmailTab(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout()
        group = QGroupBox("Send Test Emails")
        layout = QFormLayout()
        self.recipient = QLineEdit()
        self.recipient.setPlaceholderText("Recipient email address (e.g. test@example.com)")
        self.recipient.setToolTip("Enter the recipient's email address.")
        self.recipient.textChanged.connect(self.validate_inputs)
        self.num_emails = QSpinBox()
        self.num_emails.setMaximum(5000)
        self.num_emails.setMinimum(1)
        self.num_emails.setToolTip("Number of emails to send (max 5,000)")
        self.num_emails.valueChanged.connect(self.validate_inputs)
        self.status = QLabel()
        self.status.setFont(QFont("Segoe UI", 10))
        self.status.setStyleSheet("padding: 6px; background: #f5f5f5; border: 1px solid #ddd;")
        self.status.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.status.setMinimumHeight(28)
        self.log_enabled = True
        self.launch = QPushButton("Launch")
        self.launch.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; padding: 6px 18px; border-radius: 4px;")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("background-color: #e81123; color: white; font-weight: bold; padding: 6px 18px; border-radius: 4px;")
        self.stop_btn.setEnabled(False)
        self.launch.setToolTip("Start sending emails.")
        self.stop_btn.setToolTip("Stop sending emails.")
        self.launch.clicked.connect(self.start_sending)
        self.stop_btn.clicked.connect(self.stop_sending)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.launch)
        btn_layout.addWidget(self.stop_btn)
        layout.addRow("Recipient Email:", self.recipient)
        layout.addRow("Number of Emails:", self.num_emails)
        layout.addRow(btn_layout)
        group.setLayout(layout)
        main_layout.addWidget(group)
        main_layout.addSpacing(10)
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet("QProgressBar { border: 1px solid #bbb; border-radius: 4px; background: #f5f5f5; } QProgressBar::chunk { background: #0078d7; }")
        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.status)
        # Log/feedback area
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 9))
        self.log_view.setStyleSheet("background: #fafcff; border: 1px solid #e0e0e0;")
        self.log_view.setMinimumHeight(120)
        main_layout.addWidget(self.log_view)
        self.setLayout(main_layout)
        self.sender_pool = load_senders('senders_email.txt')
        if not self.sender_pool:
            QMessageBox.warning(self, "No Senders", "No sender emails found in senders_email.txt. Please add at least one.")
        self.thread = None
        self.log_lines = []
        self.validate_inputs()

    def validate_inputs(self):
        email = self.recipient.text()
        valid = is_valid_email(email)
        if not email:
            self.recipient.setStyleSheet("")
            self.launch.setEnabled(False)
            self.status.setText("")
        elif not valid:
            self.recipient.setStyleSheet("border: 2px solid #e81123;")
            self.recipient.setToolTip("Invalid email address.")
            self.launch.setEnabled(False)
            self.status.setText("<span style='color:#e81123;'>Invalid email address.</span>")
        else:
            self.recipient.setStyleSheet("")
            self.recipient.setToolTip("Valid email address.")
            self.launch.setEnabled(True)
            self.status.setText("")

    def start_sending(self):
        if not self.recipient.text() or not is_valid_email(self.recipient.text()):
            QMessageBox.warning(self, "Input Error", "Please enter a valid recipient email address.")
            return
        if not self.sender_pool:
            QMessageBox.warning(self, "No Senders", "No sender emails found in senders_email.txt.")
            return
        self.status.setText("<span style='color:#0078d7;'>Sending...</span>")
        self.log_view.clear()
        self.log_lines = []
        self.progress.setValue(0)
        self.launch.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.thread = EmailSenderThread(
            self.recipient.text(),
            self.num_emails.value(),
            self.sender_pool,
            self.log_enabled
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

    def update_status(self, sent, total):
        percent = int((total / max(1, self.num_emails.value())) * 100)
        self.progress.setValue(percent)
        self.status.setText(f"<span style='color:#0078d7;'>Sent: {sent}/{total}</span>")
        line = f"Sent: {sent}/{total}"
        self.log_view.append(line)
        self.log_lines.append(line)

    def finish_status(self, sent, failed):
        color = "#107c10" if failed == 0 else "#e81123"
        self.status.setText(f"<span style='color:{color};'>Done. Sent: {sent}, Failed: {failed}</span>")
        self.log_view.append(f"Done. Sent: {sent}, Failed: {failed}")
        self.log_lines.append(f"Done. Sent: {sent}, Failed: {failed}")
        self.launch.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setValue(100)

    def show_error(self, msg):
        self.status.setText(f"<span style='color:#e81123;'>Error: {msg}</span>")
        self.log_view.append(f"Error: {msg}")
        self.log_lines.append(f"Error: {msg}")

# --- SMS Tab ---
class SMSTab(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout()
        group = QGroupBox("Send Test SMS (Simulated)")
        layout = QFormLayout()
        self.recipient = QLineEdit()
        self.recipient.setPlaceholderText("Recipient UK phone number (e.g. +447700900001)")
        self.recipient.setToolTip("Enter the recipient's UK phone number (+44...)")
        self.recipient.textChanged.connect(self.validate_inputs)
        self.num_texts = QSpinBox()
        self.num_texts.setMaximum(1000)
        self.num_texts.setMinimum(1)
        self.num_texts.setToolTip("Number of texts to send (max 1,000)")
        self.num_texts.valueChanged.connect(self.validate_inputs)
        self.status = QLabel()
        self.status.setFont(QFont("Segoe UI", 10))
        self.status.setStyleSheet("padding: 6px; background: #f5f5f5; border: 1px solid #ddd;")
        self.status.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.status.setMinimumHeight(28)
        self.log_enabled = True
        self.launch = QPushButton("Launch")
        self.launch.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; padding: 6px 18px; border-radius: 4px;")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("background-color: #e81123; color: white; font-weight: bold; padding: 6px 18px; border-radius: 4px;")
        self.stop_btn.setEnabled(False)
        self.launch.setToolTip("Start sending SMS.")
        self.stop_btn.setToolTip("Stop sending SMS.")
        self.launch.clicked.connect(self.start_sending)
        self.stop_btn.clicked.connect(self.stop_sending)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.launch)
        btn_layout.addWidget(self.stop_btn)
        layout.addRow("Recipient Phone (+44):", self.recipient)
        layout.addRow("Number of Texts:", self.num_texts)
        layout.addRow(btn_layout)
        group.setLayout(layout)
        main_layout.addWidget(group)
        main_layout.addSpacing(10)
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet("QProgressBar { border: 1px solid #bbb; border-radius: 4px; background: #f5f5f5; } QProgressBar::chunk { background: #0078d7; }")
        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.status)
        # Log/feedback area
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 9))
        self.log_view.setStyleSheet("background: #fafcff; border: 1px solid #e0e0e0;")
        self.log_view.setMinimumHeight(120)
        main_layout.addWidget(self.log_view)
        self.setLayout(main_layout)
        self.sender_pool = load_senders('senders_sms.txt')
        if not self.sender_pool:
            QMessageBox.warning(self, "No Senders", "No sender phone numbers found in senders_sms.txt. Please add at least one.")
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
        phone = self.recipient.text()
        if not phone or not is_valid_uk_phone(phone):
            QMessageBox.warning(self, "Input Error", "Please enter a valid UK phone number (+44...)")
            return
        if not self.sender_pool:
            QMessageBox.warning(self, "No Senders", "No sender phone numbers found in senders_sms.txt.")
            return
        self.status.setText("<span style='color:#0078d7;'>Sending...</span>")
        self.log_view.clear()
        self.log_lines = []
        self.progress.setValue(0)
        self.launch.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.thread = SMSSenderThread(
            phone,
            self.num_texts.value(),
            self.sender_pool,
            self.log_enabled
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

    def update_status(self, sent, total):
        percent = int((total / max(1, self.num_texts.value())) * 100)
        self.progress.setValue(percent)
        self.status.setText(f"<span style='color:#0078d7;'>Sent: {sent}/{total}</span>")
        line = f"Sent: {sent}/{total}"
        self.log_view.append(line)
        self.log_lines.append(line)

    def finish_status(self, sent, failed):
        color = "#107c10" if failed == 0 else "#e81123"
        self.status.setText(f"<span style='color:{color};'>Done. Sent: {sent}, Failed: {failed}</span>")
        self.log_view.append(f"Done. Sent: {sent}, Failed: {failed}")
        self.log_lines.append(f"Done. Sent: {sent}, Failed: {failed}")
        self.launch.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setValue(100)

    def show_error(self, msg):
        self.status.setText(f"<span style='color:#e81123;'>Error: {msg}</span>")
        self.log_view.append(f"Error: {msg}")
        self.log_lines.append(f"Error: {msg}")

# --- Main App ---
class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delivery Testing App")
        self.setWindowIcon(QIcon())  # You can set a custom icon here if you have one
        self.setStyleSheet("QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11pt; background: #f8fafd; } QTabWidget::pane { border: 1px solid #e0e0e0; } QGroupBox { font-weight: bold; border: 1px solid #e0e0e0; border-radius: 6px; margin-top: 8px; background: #ffffff; } QGroupBox:title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; background: #f8fafd; } QPushButton { min-width: 80px; } QLabel { min-height: 24px; }")
        layout = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(EmailTab(), "Email")
        tabs.addTab(SMSTab(), "Mobile")
        layout.addWidget(tabs)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_()) 