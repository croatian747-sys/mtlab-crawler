import sys
import io
import os
import json
import time
import random
from urllib.parse import urljoin, parse_qs, urlparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime

# 일본 서버 한글 깨짐 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

from crawler_supabase import insert_promo_post 
from crawl_pato import crawl_post

BOARD_URL = "https://www.pato114.com/bbs/board.php?bo_table=ad"
STATE_FILE = "pato_state.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {"urls": []}

def save_state(state):
    if "_crawled_data" in state: del state["_crawled_data"]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def extract_wr_id(url):
    try:
        qs = parse_qs(urlparse(url).query)
        if "wr_id" in qs: return int(qs["wr_id"][0])
    except: pass
    return 0

def crawl_once():
    print(f"\n[{time.strftime('%H:%M:%S')}] 🔍 파토114 스캔 시작 (GitHub Actions 1회 실행)...", flush=True)
    
    try:
        res = requests.get(BOARD_URL, headers=HEADERS, timeout=15)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print(f"❌ 접속 실패 (에러 원인: {e})", flush=True)
        return

    candidates = []
    rows = soup.find_all("tr")
    
    for tr in rows:
        subject_td = tr.select_one("td.list-subject")
        if not subject_td: continue
        
        title_text = subject_td.get_text()
        
        if "공지" in title_text or "필독" in title_text or "파토" in title_text:
            continue

        a_tag = subject_td.select_one("a")
        if not a_tag or "href" not in a_tag.attrs: continue
        
        href = a_tag["href"]
        if "wr_id=" not in href or "#" in href: continue
        
        full_url = urljoin(BOARD_URL, href)
        
        author = "익명"
        member_tag = tr.select_one(".member") or tr.select_one(".sv_member")
        if member_tag:
            author = member_tag.get_text(strip=True)
            
        candidates.append({
            "url": full_url,
            "author": author,
            "id": extract_wr_id(full_url)
        })
    
    unique_candidates = {c['url']: c for c in candidates}.values()
    candidates = sorted(list(unique_candidates), key=lambda x: x['id'], reverse=True)
    
    print(f"   👉 발견된 일반 글: {len(candidates)}개", flush=True)
    
    state = load_state()
    known = set(state.get("urls") or [])
    new_found = False

    for item in candidates[:15]:
        url = item['url']
        author_from_list = item['author']
        
        if url in known: continue
        
        print(f"   ⚡ 분석: {author_from_list}님의 글 (ID: {item['id']})...", flush=True)
        
        data = crawl_post(url, author_override=author_from_list)
        
        if not data:
            print("      ❌ 실패", flush=True)
            continue
            
        if "파토" in data.get('content_html', ''):
            print("      ⏩ 본문에 '파토' 포함됨. 수집 제외", flush=True)
            state["urls"].append(url)
            save_state(state)
            continue
        
        print(f"      ✨ 제목: {data['title']}", flush=True)
        print(f"      ✨ 시간: {data['created_at'].strftime('%H:%M:%S')} (한국시간)", flush=True)
        
        try:
            insert_promo_post(data['title'], data['content_html'], data['author'], data['created_at'])
            print(f"      🎉 업로드 성공!", flush=True)
            
            state["urls"].append(url)
            state["urls"] = state["urls"][-50:]
            save_state(state)
            
            new_found = True
            print("      ✅ 완료. 깃허브 액션 종료.", flush=True)
            break
            
        except Exception as e:
            print(f"      ❌ DB 에러: {e}", flush=True)

    if not new_found:
        print("   ✅ 새 글 없음.", flush=True)

if __name__ == "__main__":
   
    
    # 랜덤한 대기 시간이 끝난 비로소 크롤링을 시작합니다.
    crawl_once()
