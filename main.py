import os, re, getpass
from dotenv import load_dotenv
from nutn_api import EcourseClient

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    load_dotenv()
    client = EcourseClient()

    print("🚀 啟動南大課程網自動化工具...")
    
    # 1. 處理驗證碼與登入
    captcha_url = client.get_login_page_and_captcha()
    if captcha_url:
        client.download_captcha(captcha_url)
        print("✅ 驗證碼已儲存為 captcha.png，請打開查看。")
    
    account = os.getenv("NUTN_ACCOUNT") or input("請輸入學號: ")
    password = os.getenv("NUTN_PASSWORD") or getpass.getpass("請輸入密碼: ")
    captcha_code = input("請輸入 4 碼驗證碼: ")

    print("\n-> 正在登入...")
    if not client.login(account, password, captcha_code):
        print("❌ 登入失敗！請檢查帳號密碼或驗證碼。")
        return
    print("🎉 登入成功！")

    # 2. 選擇學期
    semesters = client.get_semesters()
    print("\n=== 📅 選擇學期 ===")
    for i, sem in enumerate(semesters, 1):
        mark = " (*目前學期)" if sem["is_selected"] else ""
        print(f"[{i}] {sem['text']}{mark}")
        
    sem_idx = input("\n請選擇學期編號 (直接 Enter 為預設): ")
    if sem_idx.isdigit() and 0 <= int(sem_idx)-1 < len(semesters):
        selected_sem = semesters[int(sem_idx)-1]
        if not selected_sem["is_selected"]:
            print(f"-> 正在切換至 {selected_sem['text']}...")
            client.switch_semester(selected_sem["value"])

    # 3. 進入課程主迴圈
    while True:
        courses = client.get_courses()
        print("\n=== 📚 課程清單 ===")
        for i, c in enumerate(courses, 1):
            print(f"[{i}] {c['name']}")
        print("[q] 退出程式")
        
        c_choice = input("\n請選擇課程編號: ")
        if c_choice.lower() == 'q': break
        if not c_choice.isdigit() or not (0 <= int(c_choice)-1 < len(courses)):
            print("❌ 無效的選擇")
            continue

        selected_course = courses[int(c_choice)-1]
        safe_folder = re.sub(r'[\\/*?:"<>|]', "", selected_course['name']).strip()
        print(f"\n🚀 正在進入: {selected_course['name']}...")
        client.enter_course(selected_course['action'])

        # 4. 課程內功能子迴圈
        while True:
            print(f"\n=== 🏫 {selected_course['name']} ===")
            print("[1] 📥 查看與下載教材")
            print("[2] 📢 查看教師公告")
            print("[q] 返回課程清單")
            
            action = input("\n請選擇功能: ")
            if action.lower() == 'q': break
            
            # --- 教材下載流程 ---
            elif action == '1':
                print("\n-> 正在掃描教材檔案...")
                textbooks = client.get_textbooks()
                
                if not textbooks:
                    print("⚠️ 這堂課目前沒有教材。")
                    continue
                    
                # 需求實作：先顯示教材列表
                print("\n=== 📄 教材清單 ===")
                for i, tb in enumerate(textbooks, 1):
                    print(f"[{i}] {tb['name']} (檔名: {tb['safe_name']})")
                print("===================")
                
                # 然後才提示下載
                dl_choice = input("\n請輸入要下載的編號 (輸入 a 下載全部，q 取消): ")
                if dl_choice.lower() == 'q': continue
                
                os.makedirs(safe_folder, exist_ok=True)
                
                def do_download(tb_item):
                    path = os.path.join(safe_folder, tb_item['safe_name'])
                    print(f"⏳ 正在下載: {tb_item['safe_name']}...")
                    client.download_file(tb_item['url'], path)
                    print(f"✅ 完成！已儲存於 {path}")

                if dl_choice.lower() == 'a':
                    for tb in textbooks: do_download(tb)
                elif dl_choice.isdigit() and 0 <= int(dl_choice)-1 < len(textbooks):
                    do_download(textbooks[int(dl_choice)-1])
                else:
                    print("❌ 無效的選擇")

            # --- 公告閱讀流程 ---
            elif action == '2':
                print("\n-> 正在獲取公告...")
                bulletins = client.get_bulletins()
                
                while True:
                    print("\n=== 📢 教師公告 ===")
                    if not bulletins:
                        print("📭 目前沒有公告。")
                        break
                    for i, ann in enumerate(bulletins, 1):
                        print(f"[{i}] 📅 {ann['date']} | 📌 {ann['title']}")
                    
                    b_choice = input("\n請輸入要檢視的公告編號 (輸入 q 返回): ")
                    if b_choice.lower() == 'q': break
                    if b_choice.isdigit() and 0 <= int(b_choice)-1 < len(bulletins):
                        detail = client.get_bulletin_detail(bulletins[int(b_choice)-1]['action'])
                        
                        print("\n" + "═" * 50)
                        if detail['title'] and detail['content']:
                            print(f"📌 {detail['title'].text.strip()}")
                            if detail['date']: print(f"📅 {detail['date'].text.strip()}")
                            print("─" * 50)
                            content = detail['content'].get_text(separator="\n").strip()
                            print(re.sub(r'\n{3,}', '\n\n', content))
                        else:
                            print("⚠️ 無法解析此公告內容。")
                        print("═" * 50 + "\n")
                        input("👉 按下 [Enter] 返回公告列表...")

if __name__ == "__main__":
    main()