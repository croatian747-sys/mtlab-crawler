import os
import requests
import uuid
from datetime import datetime, timezone, timedelta

# Supabase 설정 (환경변수에서 가져옴)
SUPABASE_URL = "https://vssngmkwyzifxpiavoja.supabase.co"

# 🔥 핵심 수정: strip()을 사용해 복사 과정에서 묻은 띄어쓰기/줄바꿈 강제 제거
raw_key = os.environ.get("SUPABASE_SERVICE_ROLE")
SERVICE_ROLE_KEY = raw_key.strip() if raw_key else None

TABLE = "community_posts"
BUCKET = "images" 

KR_TZ = timezone(timedelta(hours=9))

def upload_image_to_supabase(image_url: str) -> str:
    """이미지를 다운받아 내 Supabase Storage에 저장"""
    if not image_url or not image_url.startswith("http"):
        return image_url

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        img_res = requests.get(image_url, headers=headers, timeout=10)
        if img_res.status_code != 200: return image_url

        content_type = img_res.headers.get("Content-Type", "image/jpeg")
        ext = "jpg"
        if "png" in content_type: ext = "png"
        elif "gif" in content_type: ext = "gif"
        elif "webp" in content_type: ext = "webp"
        
        filename = f"crawled/{uuid.uuid4().hex[:12]}.{ext}"
        upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{filename}"
        upload_headers = {
            "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
            "Content-Type": content_type
        }
        
        up_res = requests.post(upload_url, data=img_res.content, headers=upload_headers)
        
        if up_res.status_code in [200, 201]:
            return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{filename}"
        return image_url

    except:
        return image_url

def insert_promo_post(title, content_html, author_name="익명", created_at=None):
    if not SERVICE_ROLE_KEY: print("⚠ .env 파일에 키가 없습니다.")

    if created_at is None: created_at = datetime.now(KR_TZ)
    if isinstance(created_at, str):
        try: created_at = datetime.fromisoformat(created_at)
        except: created_at = datetime.now(KR_TZ)
    if created_at.tzinfo is None: created_at = created_at.replace(tzinfo=KR_TZ)

    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    payload = {
        "title": title,
        "content": content_html,
        "category": "promote", 
        "author_name": author_name,
        "author_id": None,
        "view_count": 0,
        "created_at": created_at.isoformat()
    }
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    res = requests.post(url, json=payload, headers=headers, timeout=20)
    res.raise_for_status()
    return res.json()[0]
