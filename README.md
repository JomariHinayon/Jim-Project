# Delivery Testing App

A Windows desktop application for bulk delivery testing of email and SMS (simulated), with sender rotation, logging, and no authentication required. Built with Python and PyQt5.

## Features
- Two tabs: Email and Mobile (SMS)
- Bulk sending (up to 5,000 emails, 1,000 SMS per session)
- Sender rotation from text files
- Throttling, error handling, retry logic
- Real-time counters and logs
- No session persistence
- No authentication required (uses local SMTP server for email)

## Requirements
- Python 3.7+
- pip
- Windows 10 or 11

## Setup
1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
2. **Prepare sender pools:**
   - Create `senders_email.txt` (one sender email per line)
   - Create `senders_sms.txt` (one sender phone number per line, format +44...)
3. **Start a local SMTP debug server (for email testing):**
   ```sh
   python -m aiosmtpd -n -l localhost:1025
   ```
   - This will print all received emails to the terminal. No real emails are sent.

## Usage
- Run the app:
  ```sh
  python main.py
  ```
- Enter recipient, select number of messages, and click Launch.
- Status and logs will update in real time.
- Logs are saved in the `logs/` directory.

## Packaging as .exe
1. Install PyInstaller:
   ```sh
   pip install pyinstaller
   ```
2. Build the executable:
   ```sh
   pyinstaller --onefile --windowed main.py
   ```
3. The `.exe` will be in the `dist/` folder.

## Notes
- No real SMS are sent; SMS sending is simulated and logged.
- For real email delivery, you must use a real SMTP server and update the code accordingly.
- No user data is persisted between runs.

## License
MIT