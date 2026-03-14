import requests
from bs4 import BeautifulSoup
import getpass
import os
import urllib3
import re
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://ecourse.nutn.edu.tw/"

def extract_hidden_fields(soup):
    """小幫手：從 HTML 中萃取所有 ASP.NET 必須的隱藏欄位"""
    payload = {}
    for hidden_input in soup.find_all("input", type="hidden"):
        name = hidden_input.get("name")
        value = hidden_input.get("value", "")
        if name:
            payload[name] = value
    return payload

def main():
    print("🚀 啟動南大課程網登入腳本...")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    try:
        # 1. 獲取登入頁面與隱藏參數
        print("-> 正在獲取登入頁面與隱藏參數...")
        response = session.get(BASE_URL, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        payload = extract_hidden_fields(soup)

        # 2. 處理驗證碼
        captcha_url = None
        for img in soup.find_all("img"):
            src = img.get("src", "").lower()
            img_id = img.get("id", "").lower()
            if "captcha" in src or "code" in src or "code" in img_id:
                captcha_url = img.get("src")
                break

        if captcha_url:
            full_captcha_url = urljoin(BASE_URL, captcha_url)
            print(f"-> 正在下載驗證碼圖片...")
            captcha_res = session.get(full_captcha_url, verify=False)
            with open("captcha.png", "wb") as f:
                f.write(captcha_res.content)
            print("   ✅ 驗證碼已儲存為 captcha.png，請打開它！")
        
        # 3. 讀取帳密與驗證碼
        # 優先從 .env 讀取，如果沒有才要求手動輸入
        account = os.getenv("NUTN_ACCOUNT") or input("請輸入學號: ")
        password = os.getenv("NUTN_PASSWORD") or getpass.getpass("請輸入密碼: ")
        captcha_code = input("請輸入 4 碼驗證碼: ")

        payload["ctl00$ContentPlaceHolder1$txtAccount"] = account
        payload["ctl00$ContentPlaceHolder1$txtPassword"] = password
        payload["ctl00$ContentPlaceHolder1$txtCode"] = captcha_code

        # 4. 送出登入請求
        print("\n-> 正在送出登入請求...")
        post_response = session.post(BASE_URL, data=payload, verify=False)

        # 5. 驗證登入
        if "登出" in post_response.text or account in post_response.text:
            print("🎉 登入成功！")
            
            # --- 獲取預設課程列表與學期清單 ---
            print("\n-> 正在獲取資料...")
            course_list_url = urljoin(BASE_URL, "course_list.aspx")
            course_res = session.get(course_list_url, verify=False)
            course_soup = BeautifulSoup(course_res.text, "html.parser")
            course_page_hidden_fields = extract_hidden_fields(course_soup)
            
            # --- 解析並顯示學期選單 ---
            dropdown = course_soup.find("select", {"name": "ctl00$ContentPlaceHolder1$Drop_syear"})
            semesters = []
            if dropdown:
                for opt in dropdown.find_all("option"):
                    semesters.append({
                        "text": opt.text.strip(),
                        "value": opt.get("value"),
                        "is_selected": opt.has_attr("selected")
                    })
            
            if semesters:
                print("\n=== 📅 選擇學期 ===")
                for i, sem in enumerate(semesters, 1):
                    mark = " (*目前學期)" if sem.get("is_selected") else ""
                    print(f"[{i}] {sem['text']}{mark}")
                print("===================")
                
                sem_choice = input("\n請輸入想查看的學期編號 (直接按 Enter 預設為當前學期): ")
                if sem_choice.isdigit():
                    idx = int(sem_choice) - 1
                    if 0 <= idx < len(semesters):
                        selected_sem = semesters[idx]
                        
                        # 如果選擇的不是預設學期，我們就需要發送 PostBack 請求切換學期
                        if not selected_sem.get("is_selected"):
                            print(f"\n-> 正在切換至 {selected_sem['text']}...")
                            postback_payload = course_page_hidden_fields.copy()
                            postback_payload["__EVENTTARGET"] = "ctl00$ContentPlaceHolder1$Drop_syear"
                            postback_payload["__EVENTARGUMENT"] = ""
                            postback_payload["ctl00$ContentPlaceHolder1$Drop_syear"] = selected_sem["value"]
                            
                            # 發送 POST 要求伺服器回傳該學期的資料
                            course_res = session.post(course_list_url, data=postback_payload, verify=False)
                            course_soup = BeautifulSoup(course_res.text, "html.parser")
                            
                            # 【極度重要】學期切換後，網頁的隱藏驗證碼 (__VIEWSTATE) 會全部更新
                            # 我們必須重新抓取，否則下一步點擊進入課程會失敗！
                            course_page_hidden_fields = extract_hidden_fields(course_soup)
            
            # --- 解析課程列表 (會根據上面選擇的學期而定) ---
            courses = []
            enter_links = course_soup.find_all("a")
            for link in enter_links:
                if "進入" in link.text or link.get("title") == "進入":
                    row = link.find_parent("tr")
                    if row:
                        columns = row.find_all("td")
                        if len(columns) >= 5:
                            course_name = columns[2].text.strip().replace('\n', '').replace('\r', '')
                            teacher = columns[4].text.strip()
                            course_action = link.get("href", "")
                            
                            courses.append({
                                "name": f"{course_name} ({teacher})",
                                "action": course_action
                            })

            if not courses:
                print("⚠️ 這個學期找不到任何課程！")
                return

            print("\n=== 📚 你的課程清單 ===")
            for i, course in enumerate(courses, 1):
                print(f"[{i}] {course['name']}")
            print("========================")
            
            choice = input("\n請輸入想進入的課程編號 (輸入 q 退出): ")
            if choice.lower() != 'q' and choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(courses):
                    selected_course = courses[idx]
                    print(f"\n🚀 正在進入: {selected_course['name']}...")
                    
                    # --- 破解 __doPostBack 進入課程 ---
                    js_code = selected_course['action']
                    match = re.search(r"__doPostBack\('(.*?)','(.*?)'\)", js_code)
                    if match:
                        event_target = match.group(1)
                        event_argument = match.group(2)
                        
                        # 使用「最新」的隱藏欄位組合 Payload
                        postback_payload = course_page_hidden_fields.copy()
                        postback_payload["__EVENTTARGET"] = event_target
                        postback_payload["__EVENTARGUMENT"] = event_argument
                        
                        enter_res = session.post(course_list_url, data=postback_payload, verify=False, allow_redirects=True)
                        
                        print(f"✅ 成功跳轉！你現在位於: {enter_res.url}")
                        
                        # ---------------- 新增：進入課程後的互動選單 ----------------
                        # 處理課程名稱，移除 Windows/Mac 不能當作資料夾名稱的特殊字元
                        safe_course_folder = re.sub(r'[\\/*?:"<>|]', "", selected_course['name']).strip()
                        
                        while True:
                            print(f"\n=== 🏫 課程功能選單 ({safe_course_folder}) ===")
                            print("[1] 📥 下載上課教材")
                            print("[2] 📢 查看教師公告")
                            print("[q] 返回 / 離開")
                            action = input("\n請選擇功能: ")

                            if action.lower() == 'q':
                                print("👋 離開課程...")
                                break

                            elif action == '1':
                                print("\n-> 正在掃描教材檔案...")
                                course_soup = BeautifulSoup(enter_res.text, "html.parser")
                                textbooks = []
                                
                                # 尋找所有包含 'getfile' (教材下載 API) 的超連結
                                for link in course_soup.find_all("a"):
                                    href = link.get("href", "")
                                    if "getfile" in href.lower():
                                        file_name = link.text.strip()
                                        if not file_name:
                                            file_name = "未命名檔案"
                                        textbooks.append({"name": file_name, "link": href})
                                
                                if not textbooks:
                                    print("⚠️ 這堂課目前沒有任何教材檔案。")
                                else:
                                    print("\n=== 📄 教材清單 ===")
                                    for i, tb in enumerate(textbooks, 1):
                                        print(f"[{i}] {tb['name']}")
                                    print("===================")
                                    
                                    dl_choice = input("\n請輸入要下載的教材編號 (輸入 a 下載全部，q 取消): ")
                                    import urllib.parse as urlparse
                                    
                                    # 定義下載檔案的小函式
                                    def download_file(tb):
                                        dl_url = urljoin(enter_res.url, tb["link"])
                                        parsed = urlparse.urlparse(dl_url)
                                        qs = urlparse.parse_qs(parsed.query)
                                        org_filename = qs.get("org_filename", [tb['name']])[0]
                                        org_filename = urlparse.unquote(org_filename)
                                        
                                        safe_filename = "".join([c for c in org_filename if c.isalnum() or c in ' ._-()【】']).rstrip()
                                        if not safe_filename: safe_filename = "download_file.pdf"
                                        
                                        # 建立課程專屬資料夾
                                        if not os.path.exists(safe_course_folder):
                                            os.makedirs(safe_course_folder)
                                            print(f"📁 已建立資料夾: {safe_course_folder}")
                                        
                                        # 組合完整的存檔路徑
                                        file_path = os.path.join(safe_course_folder, safe_filename)
                                        
                                        print(f"正在下載: {safe_filename}...")
                                        dl_res = session.get(dl_url, verify=False)
                                        with open(file_path, "wb") as f:
                                            f.write(dl_res.content)
                                        print(f"✅ 下載完成！已儲存於 {file_path}")
                                    
                                    # 處理使用者的下載選擇
                                    if dl_choice.lower() == 'a':
                                        for tb in textbooks:
                                            download_file(tb)
                                    elif dl_choice.isdigit():
                                        idx = int(dl_choice) - 1
                                        if 0 <= idx < len(textbooks):
                                            download_file(textbooks[idx])
                                        else:
                                            print("❌ 無效的編號。")

                            elif action == '2':
                                print("\n-> 正在獲取教師公告...")
                                bulletin_url = urljoin(BASE_URL, "stu/stu_bulletin.aspx")
                                bulletin_res = session.get(bulletin_url, verify=False)
                                bulletin_soup = BeautifulSoup(bulletin_res.text, "html.parser")
                                
                                announcements = []
                                # 逐列掃描所有的 <tr>
                                for row in bulletin_soup.find_all("tr"):
                                    cols = row.find_all(["td", "th"])
                                    # 如果這列有 3 個以上的欄位，才有可能是真正的公告
                                    if len(cols) >= 3:
                                        # 取出文字並清理空白
                                        col_texts = [col.text.strip() for col in cols if col.text.strip()]
                                        row_string = " | ".join(col_texts)
                                        
                                        # 關鍵過濾：這行文字裡面必須要有 YYYY-MM-DD 的日期格式
                                        if re.search(r'\d{4}-\d{2}-\d{2}', row_string):
                                            # 如果第一個字是「檢視」，我們把它拿掉讓畫面更好看
                                            if col_texts[0] == "檢視":
                                                col_texts = col_texts[1:]
                                            announcements.append(col_texts)

                                print(f"\n=== 📢 教師公告 ({safe_course_folder}) ===")
                                if not announcements:
                                    print("📭 目前沒有任何教師公告。")
                                else:
                                    # 漂亮排版印出公告
                                    for ann in announcements:
                                        # 預期格式: [公告日期, 公告標題, 有效日期]
                                        if len(ann) >= 3:
                                            date = ann[0]
                                            title = ann[1]
                                            valid = ann[2]
                                            print(f"📅 {date} | 📌 {title} (有效至: {valid})")
                                        else:
                                            # 防呆：如果格式不符合預期，就直接印出來
                                            print(" | ".join(ann))
                                print("=========================================")
                        
                else:
                    print("無效的編號。")
        else:
            print("❌ 登入失敗！請檢查帳號密碼或驗證碼。")

    except Exception as e:
        print(f"發生錯誤: {e}")

if __name__ == "__main__":
    main()