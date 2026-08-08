# ME6Blocker 🚫🎮

**ME6Blocker** is a dedicated, open-source tool designed to block Rocket League's Middle East 6 (ME6) servers. It helps players avoid high ping lobbies by dynamically managing Windows Firewall rules to block specific server IP ranges, ensuring you only connect to the best performing servers.

---

## ✨ Features

- **One-Click Blocking**: Instantly block or unblock servers with a single button press.
- **Silent Background Operation**: Runs seamlessly in the system tray without interrupting your gameplay.
- **Dynamic Updates**: Automatically fetches the latest server IP ranges from the cloud.
- **App-Specific Filtering**: Option to apply firewall rules *only* to Rocket League, avoiding interference with other applications.
- **Auto-Start**: Option to run automatically with Windows and enable blocking on startup.
- **Bilingual Interface**: Supports both Arabic and English seamlessly.

---

## ⏬ Download

- **[Download Standalone EXE (v1.4.0)](https://github.com/Al-fozan/ME6Blocker/releases/download/v1.4.0/rl_ME6blocker.exe)**
- **[Download Source Code (ZIP)](https://github.com/Al-fozan/ME6Blocker/archive/refs/tags/v1.4.0.zip)**
- **[Download Source Code (TAR.GZ)](https://github.com/Al-fozan/ME6Blocker/archive/refs/tags/v1.4.0.tar.gz)**

---

## 🚀 Quick Start Guide (English)

1. **Administrator Privileges (Crucial):** You must launch the application as an administrator (`Run as Administrator`). This allows the app to inject the necessary blocking rules into the Windows Firewall.
2. **Windows SmartScreen Warning:** When running the `.exe` file for the first time, Windows Defender might show a warning. Click on **More info** and then select **Run anyway** to launch it safely. The application is 100% safe and open-source.
3. **Activation:** Once the interface opens, click the large circular button. It will turn neon green (**ON**), and the application will instantly block the specified IP ranges in the background.

---

## 🇸🇦 دليل التشغيل (العربية)

1. **صلاحيات المسؤول (هام جداً):** يجب تشغيل البرنامج كمسؤول (`Run as Administrator`) لكي يتمكن من إضافة قواعد الحظر إلى جدار حماية ويندوز بنجاح.
2. **تنبيه ويندوز الأزرق (SmartScreen):** عند تشغيل ملف الـ `exe` لأول مرة، قد يظهر لك تنبيه حماية من ويندوز. اضغط على **More info** (مزيد من المعلومات) ثم **Run anyway** (التشغيل على أي حال) لتشغيله بأمان (البرنامج آمن ومفتوح المصدر بالكامل).
3. **التفعيل:** بمجرد فتح الواجهة، اضغط على الزر الدائري الكبير ليتغير اللون إلى الأخضر (**ON**) ويتم تفعيل الحظر على نطاقات الآي بي فوراً وبصمت تام في الخلفية.

---

## 🛠️ Building from Source

If you prefer to run the script directly or compile it yourself:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Al-fozan/ME6Blocker.git
   cd ME6Blocker
   ```

2. **Install dependencies:**
   Make sure you have Python 3.8+ installed.
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the script:**
   ```bash
   python rl_server_blocker.py
   ```

4. **Build the EXE:**
   You can use the provided `.spec` file to build a standalone executable with PyInstaller.
   ```bash
   pyinstaller rl_server_blocker.spec
   ```

---

## 💖 Support Me

If this tool helped you avoid high ping and improved your Rocket League experience, consider supporting its future development!

إذا أفادك البرنامج ووفر عليك عناء البنق العالي، يشرفني دعمك للاستمرار في تطويره وتحديثه:

**[👉 creators.sa/fozy1 👈](https://creators.sa/fozy1)**