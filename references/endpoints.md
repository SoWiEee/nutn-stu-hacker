# 🔌 NUTN Ecourse API Endpoints

由於南大課程網 (eCourse) 是傳統的伺服器渲染 (SSR) ASP.NET WebForms 架構，並未提供標準的 RESTful API。
本專案透過 `requests` 與 `BeautifulSoup` 模擬瀏覽器行為，並由 `EcourseClient` 類別自動管理連線狀態。

## 🛡️ ASP.NET 狀態管理策略

網站高度依賴隱藏欄位 (`<input type="hidden">`) 來維持狀態，特別是：

- `__VIEWSTATE`
- `__EVENTTARGET` (觸發事件的元件 ID)
- `__EVENTARGUMENT` (事件參數)


實作機制：`EcourseClient._request_soup()` 會在每一次 GET/POST 請求後，自動攔截並更新最新的隱藏欄位金鑰，確保後續發送的 PostBack 請求不會發生 "Invalid ViewState" 錯誤。

---

## 📍 主要路由與端點解析

### 1. 登入系統 (Login)
* **URL**: `GET /` -> `POST /`
* **驗證碼機制**: 每次進入首頁時動態生成驗證碼圖片 (如 `<img id="ctl00_Image1" src="ImageCode.aspx?...">`)。
* **Payload**:
  * `ctl00$ContentPlaceHolder1$txtAccount`: 學號
  * `ctl00$ContentPlaceHolder1$txtPassword`: 密碼
  * `ctl00$ContentPlaceHolder1$txtCode`: 驗證碼
* **判斷成功**: 伺服器回傳的 HTML 中包含 "登出" 字眼或使用者學號。

### 2. 學期與課程列表 (Course & Semester List)
* **URL**: `GET /course_list.aspx`
* **資料結構**: 
  * **學期**: 抓取 `<select name="ctl00$ContentPlaceHolder1$Drop_syear">` 內的 `<option>`。
  * **課程**: 抓取表格內標題為 "進入" 的 `<a>` 標籤及其對應的表格列。
* **切換學期**: 
  * 發送 `POST /course_list.aspx`。
  * `__EVENTTARGET`: `ctl00$ContentPlaceHolder1$Drop_syear`
  * `ctl00$ContentPlaceHolder1$Drop_syear`: 該學期的 Value (例如 `114-1`)。

### 3. 進入課程 (Enter Course)
* **URL**: `POST /course_list.aspx`
* **機制**: 列表中的進入按鈕通常是一個 JavaScript PostBack (例如 `javascript:__doPostBack('ctl00$ContentPlaceHolder1$GridView1','Select$0')`)。
* **實作**: 解析字串並將 `__EVENTTARGET` 與 `__EVENTARGUMENT` 帶入 POST 請求，伺服器驗證後會將 Session 狀態切換至該課程。

### 4. 取得與下載教材 (Textbooks)
* **URL**: `GET /stu/stu_textbook.aspx`
* **資料結構**: 尋找 `href` 中包含 `getfile` 的超連結。
* **實體檔案下載**: 解析 URL Query String 中的 `org_filename` 以取得未經系統亂碼化的真實檔案名稱，直接對該連結發送 GET 請求取得二進位內容 (`res.content`)。

### 5. 教師公告列表與詳細內容 (Bulletins)
* **列表 URL**: `GET /stu/stu_bulletin.aspx`
* **詳細內容 URL**:
  * 若為純連結：直接 `GET /stu/stu_bulletin_dt.aspx?no=...`
  * 若為 PostBack：發送 `POST /stu/stu_bulletin.aspx`，帶入對應的 Target/Argument。
* **內文解析座標**:
  * 日期: `span#ctl00_ContentPlaceHolder1_Label1`
  * 標題: `span#ctl00_ContentPlaceHolder1_Label2`
  * 內文: `span#ctl00_ContentPlaceHolder1_Label3` (需使用 `get_text(separator="\n")` 解析 HTML `<br/>` 換行)。