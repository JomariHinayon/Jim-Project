# Delivery Testing App (SMS Only)

A Windows desktop application for bulk delivery testing of SMS (simulated), with sender rotation, logging, and no authentication required. Built with Python and PyQt5.

## Features
- Mobile (SMS) tab for sending simulated SMS
- Bulk sending (up to 1,000 SMS per session)
- Sender rotation from text file
- Throttling, error handling, retry logic
- Real-time counters and logs
- No session persistence
- No authentication required

## Requirements
- Python 3.7+
- pip
- Windows 10 or 11

## Setup
1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
2. **Prepare sender pool:**
   - Create `senders_sms.txt` (one sender phone number per line, format +44...)

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
- No user data is persisted between runs.

## License
MIT