import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import re
from crawler_supabase import insert_promo_post, upload_image_to_supabase

KST = timezone(timedelta(hours=9))

def crawl_post(url: str, author_override: str = None) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "lxml")
    except Exception as e:
        print(f"❌ 접속 실패: {e}")
        return None

    title = ""
    h1 = soup.select_one("h1") or soup.select_one("#bo_v_title .bo_v_tit")
    if h1: title = h1.get_text(strip=True)
    if not title: return None

    author = "익명"
    if author_override and author_override != "익명":
        author = author_override
    else:
        nick_tag = soup.select_one(".view-info .member") or soup.select_one("#bo_v_info .member")
        if nick_tag: author = nick_tag.get_text(strip=True)

    if "파토" in author or "관리자" in author: author = "관리자"

    content_div = soup.select_one(".view-content") or soup.select_one("#bo_v_con")
    if not content_div: return None

    for tag in content_div.find_all(True):
        attrs = ['style', 'class', 'width', 'height', 'bgcolor', 'face']
        for attr in attrs:
            if tag.has_attr(attr): del tag[attr]
        if tag.name == 'font': tag.unwrap()

    for img in content_div.find_all("img"):
        src = img.get("src", "")
        if src:
            if not src.startswith("http"):
                src = "https://www.pato114.com" + src if src.startswith("/") else "https://www.pato114.com/bbs/" + src
            
            new_src = upload_image_to_supabase(src)
            img["src"] = new_src
            img['style'] = "max-width:100%; height:auto; display:block; margin: 15px auto; border-radius: 8px;"
            if img.has_attr('onclick'): del img['onclick']

    content_html = str(content_div)
    created_at = datetime.now(KST)

    return {
        "title": title,
        "author": author,
        "content_html": content_html,
        "created_at": created_at,
    }