import os
import json
import requests
import base64
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# 환경 변수 로드
load_dotenv()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_VOCA_DATABASE_ID = os.getenv("NOTION_VOCA_DATABASE_ID") # 데이터베이스 ID 사용
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")

now = datetime.now()
YY_MM_DD = now.strftime("%y.%m.%d")
TODAY_DATE = now.strftime('%Y-%m-%d') # 검색을 위한 오늘 날짜

BASE_DIR = Path.cwd()
SCRIPTS_DIR = BASE_DIR / "comic_scripts" / YY_MM_DD
COMIC_DIR = BASE_DIR / "comics" / YY_MM_DD
FONT_PATH = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

# (add_subtitles, upload_to_imgbb 함수는 이전과 동일)
# ... [생략] ...

# ==========================================
# 기능 3: No.와 날짜로 Notion 페이지 찾아 속성 업데이트
# ==========================================
def update_notion_property_by_no(no, img_url):
    print(f"🔍 Notion에서 No.{no} 페이지 검색 중...")
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 1. No. 와 오늘 날짜로 페이지 검색 (TTS 올릴 때와 같은 방식)
    query_data = {
        "filter": {
            "and": [
                {"property": "No.", "rich_text": {"equals": str(no)}},
                {"property": "날짜", "date": {"equals": TODAY_DATE}}
            ]
        }
    }
    
    query_res = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_VOCA_DATABASE_ID}/query",
        headers=headers,
        json=query_data
    )
    
    results = query_res.json().get("results", [])
    if not results:
        print(f"❌ No.{no} 에 해당하는 오늘 날짜의 Notion 페이지를 찾을 수 없습니다.")
        return False
        
    page_id = results[0]["id"]
    
    # 2. 찾은 페이지의 '만화' 속성(파일과 미디어)에 ImgBB 이미지 URL 추가
    print(f"📝 No.{no} 페이지(ID: {page_id[:8]}...)에 만화 등록 중...")
    update_data = {
        "properties": {
            "COMICS": { # 노션의 속성 이름이 '만화'여야 합니다.
                "files": [
                    {
                        "name": f"comic_{no}.png",
                        "type": "external",
                        "external": {"url": img_url}
                    }
                ]
            }
        }
    }
    
    update_res = requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, json=update_data)
    
    if update_res.status_code == 200:
        print(f"✅ No.{no} Notion 속성 업데이트 완료!")
        return True
    else:
        print(f"❌ No.{no} Notion 업데이트 실패: {update_res.text}")
        return False

# ==========================================
# 메인 파이프라인
# ==========================================
def main():
    print("=" * 60)
    print("🚀 3단계: 자막 합성 및 Notion 속성 업로드 시작")
    print("=" * 60)
    
    if not COMIC_DIR.exists():
        print("❌ 오늘 날짜의 만화 폴더가 없습니다.")
        return

    raw_images = list(COMIC_DIR.glob("*_raw.png"))
    
    for raw_image_path in raw_images:
        final_image_path = COMIC_DIR / raw_image_path.name.replace("_raw.png", "_final.png")
        if final_image_path.exists():
            continue
            
        script_name = raw_image_path.name.replace("_raw.png", "_script.json")
        script_path = SCRIPTS_DIR / script_name
        
        if not script_path.exists():
            continue
            
        with open(script_path, 'r', encoding='utf-8') as f:
            script = json.load(f)
            
        no = script.get("no") # 🎯 JSON에서 번호 가져오기
        
        try:
            # 1. 자막 입히기
            # final_img = add_subtitles(raw_image_path, script)
            
            # 2. ImgBB 업로드
            # img_url = upload_to_imgbb(final_img)
            
            # 3. Notion 업로드 (번호 기반 검색 후 업데이트)
            # update_notion_property_by_no(no, img_url)
            
            print("-" * 60)
        except Exception as e:
            print(f"❌ 처리 중 오류 발생 (No.{no}): {e}")

if __name__ == "__main__":
    main()