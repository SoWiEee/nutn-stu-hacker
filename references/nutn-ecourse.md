# NUTN Ecourse Reference

Base URL: `https://ecourse.nutn.edu.tw/`
Architecture: ASP.NET WebForms (Server-side rendered, no REST APIs).

## 1. Login Page Detection
- URL: `https://ecourse.nutn.edu.tw/`
- To check if logged in, run `evaluate_script`:

```javascript
document.body.innerText.includes("登出") || document.querySelector("#ctl00_ContentPlaceHolder1_txtAccount") === null;
```

If false, ask the user to log in manually due to CAPTCHA.

## 2. Course List (課程清單)
- URL: https://ecourse.nutn.edu.tw/course_list.aspx
- Extraction via evaluate_script:

```JavaScript
Array.from(document.querySelectorAll("a")).filter(a => a.innerText.includes("進入") || a.title === "進入").map(a => {
    const tr = a.closest("tr");
    const tds = tr.querySelectorAll("td");
    return {
        name: tds[2].innerText.trim(),
        teacher: tds[4].innerText.trim(),
        action: a.getAttribute("href") // usually "javascript:__doPostBack(...)"
    };
});
```

To enter a course: Use evaluate_script to execute the exact javascript:__doPostBack(...) string found in the action property. Wait for the page to load.

## 3. Bulletins (教師公告)

- URL: https://ecourse.nutn.edu.tw/stu/stu_bulletin.aspx (Must be inside a course)
- Extraction: Find the table rows. The first column usually contains a "檢視" link with a href containing either a direct link (stu_bulletin_dt.aspx?no=...) or a PostBack.
- Reading Details (stu_bulletin_dt.aspx): Once navigated to the detail page, extract data using these precise IDs:

```JavaScript

    ({
        date: document.querySelector("span#ctl00_ContentPlaceHolder1_Label1")?.innerText.trim(),
        title: document.querySelector("span#ctl00_ContentPlaceHolder1_Label2")?.innerText.trim(),
        content: document.querySelector("span#ctl00_ContentPlaceHolder1_Label3")?.innerText.trim()
    });
```

## 4. Textbooks (教材下載)

- URL: https://ecourse.nutn.edu.tw/stu/stu_textbook.aspx
- Extraction:

```JavaScript
Array.from(document.querySelectorAll("a")).filter(a => a.href.toLowerCase().includes("getfile")).map(a => {
    const url = new URL(a.href);
    const params = new URLSearchParams(url.search);
    return {
        name: a.innerText.trim(),
        downloadUrl: a.href,
        originalFilename: params.get("org_filename")
    };
});
```