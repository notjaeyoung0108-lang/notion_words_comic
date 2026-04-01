# 네컷만화 자동 생성 파이프라인

AI로 영어 표현을 자동으로 네컷만화로 만들어 Notion에 업로드하는 시스템

## 📋 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [초기 설정](#초기-설정)
3. [사용 방법](#사용-방법)
4. [스타일 커스터마이징](#스타일-커스터마이징)
5. [문제 해결](#문제-해결)

---

## 🖥️ 시스템 요구사항

### 필수 프로그램
- **Python 3.8 이상**
- **Visual Studio Code**
- **Google Drive for Desktop** (파일 동기화용)
- **Google Colab 계정** (무료 또는 Pro)

### 필수 라이브러리 (로컬)
```bash
pip install openai pandas pillow easyocr requests python-dotenv
```

### Colab에 자동 설치되는 라이브러리
- `diffusers`
- `torch`
- `transformers`

---

## 🔧 초기 설정

### 1. VS Code 설정

#### 1-1. Google Colab 확장 프로그램 설치
1. VS Code 실행
2. `Ctrl+Shift+X` (Mac: `Cmd+Shift+X`) - Extensions 열기
3. "Google Colab" 검색
4. **Google Colab** (by Google) 설치
5. **Jupyter** 확장도 같이 설치 (dependency)

#### 1-2. Colab 계정 연결
1. VS Code에서 아무 `.py` 파일 열기
2. 오른쪽 상단 **"Select Kernel"** 클릭
3. **"Google Colab"** 선택
4. Google 계정으로 로그인
5. GPU 런타임 선택 (T4 무료 or A100 Pro)

### 2. Google Drive 설정

#### 2-1. Google Drive for Desktop 설치
- [다운로드 링크](https://www.google.com/drive/download/)
- 설치 후 Google 계정 로그인
- 파일이 로컬 `~/Google Drive/My Drive`에 동기화됨

#### 2-2. 폴더 구조 생성
Google Drive에 아래 폴더들을 만드세요:
```
Google Drive/
└── My Drive/
    ├── Char/
    │   └── reference.png          # 레퍼런스 얼굴 사진
    ├── Font/
    │   └── Ames-Regular.otf        # 폰트 파일
    └── comics/
        └── (자동 생성됨)
```

### 3. API 키 발급

#### 3-1. OpenAI API
1. https://platform.openai.com/api-keys
2. "Create new secret key" 클릭
3. 키 복사 (sk-proj-...)

#### 3-2. Notion API
1. https://www.notion.so/my-integrations
2. "New integration" 클릭
3. 이름 입력 (예: Comic Generator)
4. "Submit" → Internal Integration Token 복사
5. Notion 페이지에서 "..." → "Add connections" → 방금 만든 integration 연결
6. 페이지 URL에서 ID 복사:
   ```
   https://www.notion.so/workspace/페이지이름-여기가ID
                                          ^^^^^^^^
   ```

#### 3-3. Imgur Client ID
1. https://api.imgur.com/oauth2/addclient
2. Application name: Comic Uploader
3. Authorization type: **Anonymous usage without user authorization**
4. Email: (본인 이메일)
5. Submit → **Client ID** 복사

### 4. 환경 변수 설정

프로젝트 폴더에 `.env` 파일 생성:

```bash
# .env
OPENAI_API_KEY=sk-proj-your-key-here
NOTION_API_KEY=ntn_your-key-here
NOTION_PAGE_ID=your-page-id-here
IMGUR_CLIENT_ID=your-imgur-client-id
```

**⚠️ 주의**: `.env` 파일은 절대 Git에 올리지 마세요!

`.gitignore` 파일에 추가:
```
.env
comics/
*.png
*.json
```

### 5. 프로젝트 파일 다운로드

```bash
# 프로젝트 폴더 생성
mkdir comic-automation
cd comic-automation

# 필수 파일들 생성
touch auto_comic_pipeline.py
touch .env
```

---

## 🚀 사용 방법

### 기본 실행

1. **VS Code에서 파일 열기**
   ```bash
   code auto_comic_pipeline.py
   ```

2. **Colab 커널 선택**
   - 오른쪽 상단 "Select Kernel" 클릭
   - "Google Colab" 선택
   - GPU 런타임 선택

3. **실행**
   ```bash
   python auto_comic_pipeline.py
   ```

4. **자동 진행**
   - ✅ 대본 생성 (로컬 CPU)
   - 🎨 이미지 생성 (Colab GPU) ← 여기서만 1-2분
   - ✍️ 자막 추가 (로컬 CPU)
   - 📝 Notion 업로드 (로컬 CPU)

### 실행 흐름 상세

```
시작
 ↓
📖 CSV에서 영어 표현 랜덤 선택 (로컬)
 ↓
🤖 GPT-4o로 네컷만화 대본 생성 (로컬)
 ↓
[VS Code가 자동으로 Colab 커널로 전환]
 ↓
🎨 Qwen-Image-Edit로 이미지 생성 (Colab GPU)
 ↓
[VS Code가 자동으로 로컬 커널로 복귀]
 ↓
✍️ 자막 자동 추가 (로컬)
 ↓
📤 Imgur 업로드 (로컬)
 ↓
📝 Notion 페이지에 추가 (로컬)
 ↓
완료! 🎉
```

### 컴퓨팅 유닛 사용

- **로컬 작업**: 무료 (대본 생성, 자막, 업로드)
- **Colab GPU**: 1-2분만 사용 (이미지 생성만)
- **Pro 구독 없이도 가능** (T4 GPU 무료)

---

## 🎨 스타일 커스터마이징

### 이미지 스타일 변경

`auto_comic_pipeline.py` 파일에서 `generate_image()` 함수 찾기:

```python
def generate_image(self, script):
    # ... 생략 ...
    
    # 📍 여기서 프롬프트 수정!
    prompt = "Korean beauty, cinematic 4-panel, 2x2 grid, photorealistic, NO text.\n"
```

#### 스타일 프리셋

**1. 웹툰 스타일**
```python
prompt = "Korean webtoon style, 4-panel comic, 2x2 grid, clean lines, vibrant colors, NO text.\n"
negative_prompt = "photorealistic, 3D render, cartoon, text, bubbles"
```

**2. 애니메이션 스타일**
```python
prompt = "Anime style, 4-panel manga, 2x2 grid, detailed cel shading, expressive eyes, NO text.\n"
negative_prompt = "photorealistic, western cartoon, text, bubbles"
```

**3. 일러스트레이션 스타일**
```python
prompt = "Digital illustration, 4-panel story, 2x2 grid, painterly style, soft lighting, NO text.\n"
negative_prompt = "photorealistic, photo, 3D, text, bubbles"
```

**4. 빈티지 스타일**
```python
prompt = "Vintage comic style, 4-panel, 2x2 grid, retro colors, grainy texture, NO text.\n"
negative_prompt = "modern, clean, photorealistic, text, bubbles"
```

**5. 미니멀 스타일**
```python
prompt = "Minimalist style, 4-panel, 2x2 grid, simple shapes, flat colors, clean composition, NO text.\n"
negative_prompt = "detailed, realistic, complex, text, bubbles"
```

### 네거티브 프롬프트 수정

원하지 않는 요소 추가:

```python
negative_prompt = """low quality, cartoon, text, bubbles, 
watermark,           # 워터마크 제거
extra fingers,       # 손가락 이상 방지
deformed face,       # 얼굴 왜곡 방지
multiple heads,      # 머리 여러 개 방지
blurry,             # 흐릿함 방지
your_custom_here    # 원하는 제외 요소 추가
"""
```

### 이미지 생성 파라미터 조정

```python
image = pipeline(
    image=[reference_image],
    prompt=prompt,
    
    # 🎯 프롬프트 충실도 (1.0 ~ 5.0)
    # 낮을수록 자유로움, 높을수록 프롬프트 엄격 준수
    true_cfg_scale=4.0,        # 기본값: 4.0
    
    negative_prompt=negative_prompt,
    
    # 🔄 생성 스텝 (20 ~ 50)
    # 많을수록 디테일 좋지만 느림
    num_inference_steps=40,    # 기본값: 40
    
    guidance_scale=1.0,
    
    # 🎲 시드값 (같은 시드 = 같은 결과)
    generator=torch.Generator(device=device).manual_seed(42)  # 42 변경 가능
).images[0]
```

### 자막 스타일 변경

`add_subtitles()` 함수에서:

```python
# 폰트 크기 변경
font = ImageFont.truetype(self.config['font_path'], 28)  # 숫자 변경

# 외곽선 두께 변경
for dx in range(-3, 4):  # -3 ~ 3 범위 (더 두껍게: -5 ~ 5)
    for dy in range(-3, 4):
        if dx or dy:
            draw.text((x+dx, y+dy), line, fill='black', font=font)

# 텍스트 색상 변경
draw.text((x, y), line, fill='white', font=font)  # 'white' 변경 가능

# 자막 위치 조정
start_y = y2 - 60 - len(lines) * line_height // 2  # 60 변경 (하단 여백)
```

---

## 🐛 문제 해결

### VS Code에서 Colab 커널이 안 보여요
**해결책**:
1. Google Colab 확장 재설치
2. Jupyter 확장도 같이 설치되었는지 확인
3. VS Code 재시작
4. Google 계정 재로그인

### "No module named 'diffusers'" 에러
**원인**: Colab 커널이 아닌 로컬 커널에서 실행됨

**해결책**:
1. 오른쪽 상단 커널 확인
2. "Google Colab" 선택되어 있는지 확인
3. GPU 런타임 선택

### Google Drive 파일이 동기화 안돼요
**해결책**:
1. Google Drive for Desktop이 실행 중인지 확인
2. `~/Google Drive/My Drive` 폴더가 존재하는지 확인
3. Drive 앱 재시작
4. 동기화 완료까지 대기

### Imgur 업로드 실패
**해결책**:
1. Imgur Client ID 재확인
2. 이미지 크기 확인 (10MB 이하)
3. 인터넷 연결 확인

### Notion 업로드 실패
**해결책**:
1. Notion Integration이 페이지에 연결되어 있는지 확인
2. Page ID가 정확한지 확인
3. API 키 재발급

### 이미지 생성이 너무 오래 걸려요
**해결책**:
1. `num_inference_steps`를 30으로 줄이기
2. Colab Pro 구독 (A100 GPU 사용)
3. 이미지 크기 축소 고려

### 메모리 부족 에러
**해결책**:
```python
# generate_image() 함수 마지막에 추가
del pipeline
import gc
gc.collect()
torch.cuda.empty_cache()
```

### 폰트가 적용 안돼요
**해결책**:
1. 폰트 파일 경로 확인
2. 폰트 파일명 정확히 확인
3. 절대 경로로 변경:
```python
'font_path': '/Users/yourname/Google Drive/My Drive/Font/Ames-Regular.otf'
```

---

## 📁 프로젝트 구조

```
comic-automation/
├── auto_comic_pipeline.py    # 메인 스크립트
├── .env                       # API 키 (Git 제외!)
├── .gitignore
├── README.md
├── words/
│   └── structured/
│       └── 25.01/
│           └── 25.01.15_words.csv
└── comics/
    └── 25.01/
        ├── 250115_120000_script.json
        ├── 250115_120000_raw.png
        └── 250115_120000_final.png
```

---

## 🎯 핵심 코드 위치

### 대본 생성 수정
- **위치**: `generate_script()` 함수
- **라인**: ~80-120
- **수정 가능**: GPT 프롬프트, 온도(temperature)

### 이미지 스타일 수정
- **위치**: `generate_image()` 함수
- **라인**: ~150-200
- **수정 가능**: 프롬프트, 네거티브 프롬프트, CFG scale, steps

### 자막 스타일 수정
- **위치**: `add_subtitles()` 함수
- **라인**: ~250-350
- **수정 가능**: 폰트 크기, 색상, 위치, 외곽선

### Notion 레이아웃 수정
- **위치**: `upload_to_notion()` 함수
- **라인**: ~400-450
- **수정 가능**: 블록 구조, 텍스트, 아이콘

---

## 💡 팁

1. **첫 실행은 시간이 좀 걸려요**
   - Colab이 파이프라인 다운로드 (~5GB)
   - 이후부터는 캐시 사용으로 빠름

2. **여러 개 생성할 때**
   - 스크립트를 연속 실행
   - Colab 세션이 유지되면 더 빠름

3. **스타일 실험**
   - `manual_seed(42)` 값을 고정하고
   - 프롬프트만 바꾸면서 테스트

4. **비용 절감**
   - Colab 무료 T4로도 충분
   - Pro는 더 빠르지만 필수 아님

---

## 🆘 도움말

문제가 생기면:
1. 에러 메시지 전체 복사
2. 어느 단계에서 멈췄는지 확인
3. `.env` 파일의 API 키 재확인
4. VS Code Colab 커널 선택 확인

---

**즐거운 만화 제작 되세요! 🎨✨**
