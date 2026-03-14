import os, re, urllib3, requests
import urllib.parse as urlparse
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EcourseClient:
    def __init__(self, base_url="https://ecourse.nutn.edu.tw/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.hidden_fields = {}  # 自動管理 ASP.NET 的狀態金鑰
        self.current_url = base_url

    def _extract_hidden_fields(self, soup: BeautifulSoup) -> dict:
        """解析 ASP.NET 的隱藏驗證欄位 (__VIEWSTATE 等)"""
        payload = {}
        for hidden in soup.find_all("input", type="hidden"):
            name, value = hidden.get("name"), hidden.get("value", "")
            if name:
                payload[name] = value
        return payload

    def _request_soup(self, url: str, method="GET", data=None) -> BeautifulSoup:
        """統一發送請求並自動更新隱藏欄位與當前網址"""
        if method == "GET":
            res = self.session.get(url, verify=False)
        else:
            res = self.session.post(url, data=data, verify=False, allow_redirects=True)
        
        res.raise_for_status()
        self.current_url = res.url
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 每次請求後，自動把最新的金鑰存起來，這樣外部就不用手動管了！
        new_hidden = self._extract_hidden_fields(soup)
        if new_hidden:
            self.hidden_fields = new_hidden
            
        return soup

    def get_login_page_and_captcha(self) -> str:
        """獲取登入頁面並回傳驗證碼圖片網址"""
        soup = self._request_soup(self.base_url)
        for img in soup.find_all("img"):
            src, img_id = img.get("src", "").lower(), img.get("id", "").lower()
            if "captcha" in src or "code" in src or "code" in img_id:
                return urlparse.urljoin(self.base_url, img.get("src"))
        return None

    def download_captcha(self, captcha_url: str, save_path="captcha.png"):
        """下載驗證碼圖片"""
        res = self.session.get(captcha_url, verify=False)
        with open(save_path, "wb") as f:
            f.write(res.content)

    def login(self, account, password, captcha_code) -> bool:
        """執行登入動作"""
        payload = self.hidden_fields.copy()
        payload.update({
            "ctl00$ContentPlaceHolder1$txtAccount": account,
            "ctl00$ContentPlaceHolder1$txtPassword": password,
            "ctl00$ContentPlaceHolder1$txtCode": captcha_code
        })
        soup = self._request_soup(self.base_url, method="POST", data=payload)
        return "登出" in soup.text or account in soup.text

    def get_semesters(self) -> list:
        """獲取學期清單"""
        soup = self._request_soup(urlparse.urljoin(self.base_url, "course_list.aspx"))
        semesters = []
        dropdown = soup.find("select", {"name": "ctl00$ContentPlaceHolder1$Drop_syear"})
        if dropdown:
            for opt in dropdown.find_all("option"):
                semesters.append({
                    "text": opt.text.strip(),
                    "value": opt.get("value"),
                    "is_selected": opt.has_attr("selected")
                })
        return semesters

    def switch_semester(self, semester_value: str):
        """切換學期 (發送 PostBack)"""
        payload = self.hidden_fields.copy()
        payload.update({
            "__EVENTTARGET": "ctl00$ContentPlaceHolder1$Drop_syear",
            "__EVENTARGUMENT": "",
            "ctl00$ContentPlaceHolder1$Drop_syear": semester_value
        })
        self._request_soup(urlparse.urljoin(self.base_url, "course_list.aspx"), method="POST", data=payload)

    def get_courses(self) -> list:
        """獲取當前學期的課程清單"""
        soup = self._request_soup(urlparse.urljoin(self.base_url, "course_list.aspx"))
        courses = []
        for link in soup.find_all("a"):
            if "進入" in link.text or link.get("title") == "進入":
                row = link.find_parent("tr")
                if row and len(cols := row.find_all("td")) >= 5:
                    name = cols[2].text.strip().replace('\n', '').replace('\r', '')
                    teacher = cols[4].text.strip()
                    courses.append({
                        "name": f"{name} ({teacher})",
                        "action": link.get("href", "")
                    })
        return courses

    def enter_course(self, js_action: str) -> bool:
        """進入課程 (解析 PostBack 並跳轉)"""
        match = re.search(r"__doPostBack\('(.*?)','(.*?)'\)", js_action)
        if match:
            payload = self.hidden_fields.copy()
            payload.update({
                "__EVENTTARGET": match.group(1),
                "__EVENTARGUMENT": match.group(2)
            })
            self._request_soup(urlparse.urljoin(self.base_url, "course_list.aspx"), method="POST", data=payload)
            return True
        return False

    def get_textbooks(self) -> list:
        """獲取教材列表"""
        # 確認先切換到教材頁面
        soup = self._request_soup(urlparse.urljoin(self.base_url, "stu/stu_textbook.aspx"))
        textbooks = []
        for link in soup.find_all("a"):
            href = link.get("href", "")
            if "getfile" in href.lower():
                name = link.text.strip() or "未命名檔案"
                dl_url = urlparse.urljoin(self.current_url, href)
                
                # 智慧解析真實檔名
                qs = urlparse.parse_qs(urlparse.urlparse(dl_url).query)
                org_name = urlparse.unquote(qs.get("org_filename", [name])[0])
                safe_name = "".join([c for c in org_name if c.isalnum() or c in ' ._-()【】']).rstrip()
                
                textbooks.append({"name": name, "safe_name": safe_name or "download.pdf", "url": dl_url})
        return textbooks

    def download_file(self, url: str, save_path: str):
        """下載實體檔案"""
        res = self.session.get(url, verify=False)
        with open(save_path, "wb") as f:
            f.write(res.content)

    def get_bulletins(self) -> list:
        """獲取公告列表"""
        soup = self._request_soup(urlparse.urljoin(self.base_url, "stu/stu_bulletin.aspx"))
        bulletins = []
        for row in soup.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) >= 3:
                texts = [col.text.strip() for col in cols if col.text.strip()]
                if re.search(r'\d{4}-\d{2}-\d{2}', " ".join(texts)):
                    action = cols[0].find("a").get("href", "") if cols[0].find("a") else ""
                    if texts[0] == "檢視": texts = texts[1:]
                    if len(texts) >= 3:
                        bulletins.append({
                            "date": texts[0], "title": texts[1], "valid": texts[2], "action": action
                        })
        return bulletins

    def get_bulletin_detail(self, js_action: str) -> dict:
        """獲取單篇公告詳細內容"""
        bulletin_url = urlparse.urljoin(self.base_url, "stu/stu_bulletin.aspx")
        if "javascript:__doPostBack" in js_action:
            match = re.search(r"__doPostBack\('(.*?)','(.*?)'\)", js_action)
            payload = self.hidden_fields.copy()
            payload.update({"__EVENTTARGET": match.group(1), "__EVENTARGUMENT": match.group(2)})
            soup = self._request_soup(bulletin_url, method="POST", data=payload)
        else:
            soup = self._request_soup(urlparse.urljoin(bulletin_url, js_action))
            
        return {
            "date": soup.find("span", id="ctl00_ContentPlaceHolder1_Label1"),
            "title": soup.find("span", id="ctl00_ContentPlaceHolder1_Label2"),
            "content": soup.find("span", id="ctl00_ContentPlaceHolder1_Label3")
        }