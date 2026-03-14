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
            
            # --- 開始課程列表邏輯 ---
            print("\n-> 正在獲取課程列表...")
            course_list_url = urljoin(BASE_URL, "course_list.aspx")
            course_res = session.get(course_list_url, verify=False)
            course_soup = BeautifulSoup(course_res.text, "html.parser")
            
            # 準備等一下 PostBack 需要的當前頁面隱藏欄位
            course_page_hidden_fields = extract_hidden_fields(course_soup)
            
            courses = []
            enter_links = course_soup.find_all("a")
            for link in enter_links:
                if "進入" in link.text or link.get("title") == "進入":
                    row = link.find_parent("tr")
                    if row:
                        columns = row.find_all("td")
                        # 修正：[2]才是課程名稱，[4]是老師
                        if len(columns) >= 5:
                            course_name = columns[2].text.strip().replace('\n', '').replace('\r', '')
                            teacher = columns[4].text.strip()
                            course_action = link.get("href", "")
                            
                            courses.append({
                                "name": f"{course_name} ({teacher})",
                                "action": course_action
                            })

            if not courses:
                print("⚠️ 找不到課程列表！")
                return

            print("\n=== 📚 你的這學期課程 ===")
            for i, course in enumerate(courses, 1):
                print(f"[{i}] {course['name']}")
            print("========================")
            
            choice = input("\n請輸入想進入的課程編號 (輸入 q 退出): ")
            if choice.lower() != 'q' and choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(courses):
                    selected_course = courses[idx]
                    print(f"\n🚀 正在進入: {selected_course['name']}...")
                    
                    # --- 破解 __doPostBack ---
                    js_code = selected_course['action']
                    # 利用正則表達式抽出 'ctl00$ContentPlaceHolder1$ListView1$ctrl4$LinkButton1'
                    match = re.search(r"__doPostBack\('(.*?)','(.*?)'\)", js_code)
                    if match:
                        event_target = match.group(1)
                        event_argument = match.group(2)
                        
                        # 組合進入課程的 Payload
                        postback_payload = course_page_hidden_fields.copy()
                        postback_payload["__EVENTTARGET"] = event_target
                        postback_payload["__EVENTARGUMENT"] = event_argument
                        
                        # 向 course_list.aspx 發送 POST 來觸發進入課程
                        # ASP.NET 驗證成功後通常會 302 重新導向到該課程的獨立網頁
                        enter_res = session.post(course_list_url, data=postback_payload, verify=False, allow_redirects=True)
                        
                        print(f"✅ 成功跳轉！你現在位於: {enter_res.url}")
                        
                        # ---------------- 新增：進入課程後的互動選單 ----------------
                        while True:
                            print("\n=== 🏫 課程功能選單 ===")
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
                                        # 嘗試從網址中解析出原始檔名 (org_filename)
                                        parsed = urlparse.urlparse(dl_url)
                                        qs = urlparse.parse_qs(parsed.query)
                                        # 如果網址裡有 org_filename 就用它，沒有就用網頁上顯示的字
                                        org_filename = qs.get("org_filename", [tb['name']])[0]
                                        # 處理 URL 編碼 (把 %E5%B9%B3... 轉回中文)
                                        org_filename = urlparse.unquote(org_filename)
                                        
                                        # 移除檔名中可能導致存檔失敗的特殊字元
                                        safe_filename = "".join([c for c in org_filename if c.isalnum() or c in ' ._-()【】']).rstrip()
                                        if not safe_filename: safe_filename = "download_file.pdf"
                                        
                                        print(f"正在下載: {safe_filename}...")
                                        dl_res = session.get(dl_url, verify=False)
                                        with open(safe_filename, "wb") as f:
                                            f.write(dl_res.content)
                                        print(f"✅ 下載完成！")
                                    
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
                                # 直接帶著同一個 Session 去要公告頁面
                                bulletin_url = urljoin(BASE_URL, "stu/stu_bulletin.aspx")
                                bulletin_res = session.get(bulletin_url, verify=False)
                                bulletin_soup = BeautifulSoup(bulletin_res.text, "html.parser")
                                
                                # 將公告 HTML 存下來，方便我們後續解析
                                with open("bulletin_page.html", "w", encoding="utf-8") as f:
                                    f.write(bulletin_soup.prettify())
                                
                                print("👉 已經將公告頁面下載並儲存為 bulletin_page.html。")
                                print("你可以打開這個檔案看看裡面的表格結構，這樣我們下一階段就可以直接把公告標題跟內容印在終端機上了！")

                        # -----------------------------------------------------------
                        
                else:
                    print("無效的編號。")
        else:
            print("❌ 登入失敗！請檢查帳號密碼或驗證碼。")

    except Exception as e:
        print(f"發生錯誤: {e}")

if __name__ == "__main__":
    main()