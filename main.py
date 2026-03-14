import requests
from bs4 import BeautifulSoup
import getpass
import os
import urllib3
from urllib.parse import urljoin

# 關閉 urllib3 的 InsecureRequestWarning 警告，保持終端機畫面乾淨
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定目標網址 (如果登入頁有特定路徑如 /Login.aspx 請自行替換)
BASE_URL = "https://ecourse.nutn.edu.tw/"

def main():
    print("🚀 啟動南大課程網登入腳本...")
    
    # 1. 建立 Session 來維持 Cookie
    session = requests.Session()
    # 偽裝成正常的瀏覽器
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    try:
        # 2. GET 請求：獲取登入頁面的 HTML 與 ASP.NET 隱藏參數
        print("-> 正在獲取登入頁面與隱藏參數...")
        # 【修復重點】：加入 verify=False 強制略過 SSL 憑證檢查
        response = session.get(BASE_URL, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # 自動萃取所有 type="hidden" 的 <input> 標籤
        payload = {}
        for hidden_input in soup.find_all("input", type="hidden"):
            name = hidden_input.get("name")
            value = hidden_input.get("value", "")
            if name:
                payload[name] = value

        # 3. 尋找並下載驗證碼圖片
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
            # 【修復重點】：下載圖片一樣要略過 SSL 檢查
            captcha_res = session.get(full_captcha_url, verify=False)
            with open("captcha.png", "wb") as f:
                f.write(captcha_res.content)
            print("   ✅ 驗證碼已儲存為 captcha.png，請在資料夾中打開它！")
        else:
            print("   ⚠️ 找不到驗證碼圖片，可能會登入失敗。")

        # 4. 終端機互動：安全地輸入帳號、密碼與驗證碼
        print("\n--- 🔐 登入資訊 ---")
        account = input("請輸入學號: ")
        password = getpass.getpass("請輸入密碼: ") 
        captcha_code = input("請輸入 4 碼驗證碼: ")

        payload["ctl00$ContentPlaceHolder1$txtAccount"] = account
        payload["ctl00$ContentPlaceHolder1$txtPassword"] = password
        payload["ctl00$ContentPlaceHolder1$txtCode"] = captcha_code

        # 5. POST 請求：送出表單
        print("\n-> 正在送出登入請求...")
        # 【修復重點】：送出資料時也要略過 SSL 檢查
        post_response = session.post(BASE_URL, data=payload, verify=False)

        # 6. 驗證登入是否成功
        if "登出" in post_response.text or "個人設定" in post_response.text or account in post_response.text:
            print("🎉 登入成功！你現在已經擁有合法的 Session Cookie 了。")
        else:
            print("❌ 登入失敗！請檢查帳號密碼，或是驗證碼輸入錯誤。")
            with open("error_page.html", "w", encoding="utf-8") as f:
                f.write(post_response.text)
            print("   (已將錯誤網頁儲存為 error_page.html，可打開查看伺服器錯誤訊息)")

    except Exception as e:
        print(f"發生錯誤: {e}")

if __name__ == "__main__":
    main()