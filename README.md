# 🎓 NUTN Student Hacker

這是一個基於 Python 開發的命令列工具，讓你能在不開啟瀏覽器的情況下，優雅、快速地瀏覽國立臺南大學的課程網站。透過自動化的 Session 管理與 ASP.NET 狀態破解，讓你輕鬆完成登入、切換學期、下載教材與閱讀公告。

## ✨ Features

- 🔑 自動化登入：支援 `.env` 讀取帳密，只需手動輸入驗證碼即可快速登入。
- 📅 學期與課程管理：自動抓取歷年學期與當學期課程清單，支援一鍵切換。
- 📥 智慧教材下載器：
  - 列出該課程所有教材與真實檔名。
  - 支援單檔下載或「一鍵下載全部」。
  - 自動過濾檔名中的非法字元，並依課程名稱建立專屬資料夾。
- 📢 終端機公告閱讀器：精準萃取公告純文字內容，去除網頁雜訊，支援多段落換行顯示。

## 🚀 Quick Started

### 1. Requirements

- 請確保你的環境已經安裝 `Python 3.10` 以上版本
- 可以用 python 內建的 pip 安裝，可能用飛快的 [uv](https://docs.astral.sh/uv/) 來安裝

```bash
# pip
pip install requests beautifulsoup4 python-dotenv
# uv
uv sync
```

### 2. Environment Variables

在專案根目錄建立一個 .env 檔案，填入你的南大入口帳密，登入時就可以免去手動輸入的麻煩：

```toml
NUTN_ACCOUNT=<student id>
NUTN_PASSWORD=<password>
```

### 3. Run

可以直接用 python 執行，也能用 uv run：

```bash
# Windows
python main.py
# Linux/MacOS
python3 main.py
# General
uv run main.py
```
