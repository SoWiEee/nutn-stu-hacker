# NUTN Student Hacker

這是一個基於 Python 3.13 開發的懶人爬蟲工具，用於自動登入國立臺南大學課程網站，並為後續下載教材與串接 AI 做準備，後續會開發 AI skills 幫助大家學習。

## 網站資訊與端點分析

* **目標網站**: `https://ecourse.nutn.edu.tw/`
* **架構特徵**: 傳統 ASP.NET WebForms (依賴大量的動態隱藏欄位與 Session Cookie)。

### 1. 登入流程

* **Method**: `GET` -> 獲取表單與隱藏參數
* **Method**: `POST` -> 送出登入資料
* **URL**: `https://ecourse.nutn.edu.tw/Login.aspx` (或首頁預設路徑)
* **Payload 關鍵參數**:
    * `__VIEWSTATE`: ASP.NET 狀態保存字串 (每次 GET 必須重新抓取)
    * `__VIEWSTATEGENERATOR`: 狀態生成器驗證碼
    * `__EVENTVALIDATION`: 事件驗證碼
    * `__RequestVerificationToken`: 防 CSRF 攻擊的 Token
    * `ctl00$ContentPlaceHolder1$txtAccount`: 學號 (帳號)
    * `ctl00$ContentPlaceHolder1$txtPassword`: 密碼
    * `ctl00$ContentPlaceHolder1$txtCode`: 4 碼驗證碼

### 2. 驗證碼處理
* **驗證碼端點**: 通常為一個動態生成的圖片 URL (例如包含 `captcha` 或 `ValidateCode` 的 `img` 標籤)。
* **處理方式**: 透過同一個 `requests.Session()` 下載圖片至本機端 (`captcha.png`)，由使用者肉眼辨識後在 CLI 手動輸入，以保持 Session 狀態連貫。

## 執行方式
本專案使用 `uv` 管理套件。

```bash
# 執行主程式
uv run main.py
