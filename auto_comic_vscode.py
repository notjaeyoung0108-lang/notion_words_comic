# auto_comic_vscode.py
# VS Code에서 실행하면 자동으로 Colab GPU 사용!

import openai
import pandas as pd
import json
import requests
import base64
from datetime import datetime
from pathlib import Path
import os
from PIL import Image, ImageDraw, ImageFont

class AutoComicPipeline:
    def __init__(self, config):
        self.config = config
        self.openai_client = openai.OpenAI(api_key=config['openai_api_key'])
        
        # 날짜
        now = datetime.now()
        self.YY_MM_DD = now.strftime("%y.%m.%d")
        self.timestamp = now.strftime("%y%m%d_%H%M%S")
        
        # 경로
        BASE_DIR = Path.cwd()
        STRUCTURED_DIR = BASE_DIR / "words" / "structured" / now.strftime("%y.%m")
        self.CLEAN_CSV = STRUCTURED_DIR / f"{self.YY_MM_DD}_words.csv"
        
        self.COMIC_DIR = BASE_DIR / "comics" / now.strftime("%y.%m")
        self.COMIC_DIR.mkdir(parents=True, exist_ok=True)
        
        # Colab 사용 여부 체크
        try:
            from google.colab import drive
            self.is_colab = True
        except:
            self.is_colab = False
    
    # ===================================
    # STEP 1: 대본 생성 (로컬)
    # ===================================
    def generate_script(self):
        """대본 생성"""
        print("\n📝 STEP 1: 대본 생성")
        
        df = pd.read_csv(self.CLEAN_CSV, encoding="utf-8-sig")
        selected = df.sample(n=1).iloc[0]
        
        entry = {
            'collocation': selected['collocation unit'],
            'meaning': selected['meaning'],
            'nuance': selected['nuance (Korean)'],
            'example_sentence': selected['example sentence']
        }
        
        print(f"✅ 선택: {entry['collocation']}")
        
        # GPT
        prompt = f"""4-panel story capturing nuance.

Expression: {entry['collocation']}
Nuance: {entry['nuance']}

JSON only:
{{
    "collocation": "{entry['collocation']}",
    "example_sentence": "{entry['example_sentence']}",
    "nuance_summary": "Brief",
    "panels": [
        {{"number": 1, "scene": "Detailed scene", "emotion": "determined", "dialogue": ""}},
        {{"number": 2, "scene": "...", "emotion": "...", "dialogue": ""}},
        {{"number": 3, "scene": "...", "emotion": "...", "dialogue": ""}},
        {{"number": 4, "scene": "...", "emotion": "...", "dialogue": ""}}
    ]
}}"""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        
        text = response.choices[0].message.content
        script = json.loads(text[text.find('{'):text.rfind('}')+1])
        
        # 저장
        script_path = self.COMIC_DIR / f"{self.timestamp}_script.json"
        with open(script_path, 'w', encoding='utf-8') as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        
        print("✅ 대본 완료")
        return script
    
    # ===================================
    # STEP 2: 이미지 생성 (Colab GPU)
    # ===================================
    def generate_image(self, script):
        """VS Code Colab 커널에서 GPU 실행"""
        print("\n🎬 STEP 2: 이미지 생성 (Colab GPU)")
        
        # Qwen 파이프라인 로드
        from diffusers import QwenImageEditPlusPipeline
        import torch
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"🔄 파이프라인 로딩... (Device: {device})")
        pipeline = QwenImageEditPlusPipeline.from_pretrained(
            "Qwen/Qwen-Image-Edit-2511",
            torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32
        ).to(device)
        print("✅ 로드 완료!")
        
        # 프롬프트 생성
        prompt = "Korean beauty, cinematic 4-panel, 2x2 grid, photorealistic, NO text.\n"
        pos = {1: "top left", 2: "top right", 3: "bottom left", 4: "bottom right"}
        
        for p in script['panels']:
            prompt += f"Panel {p['number']} ({pos[p['number']]}): {p['scene']} Emotion: {p['emotion']}.\n"
        
        negative_prompt = "low quality, cartoon, text, bubbles"
        
        # 레퍼런스 이미지
        reference_image = Image.open(self.config['reference_image_path'])
        
        # 생성
        print("🎨 이미지 생성 중...")
        image = pipeline(
            image=[reference_image],
            prompt=prompt,
            true_cfg_scale=4.0,
            negative_prompt=negative_prompt,
            num_inference_steps=40,
            guidance_scale=1.0,
            generator=torch.Generator(device=device).manual_seed(42)
        ).images[0]
        
        # 저장
        output_path = self.COMIC_DIR / f"{self.timestamp}_raw.png"
        image.save(output_path)
        print(f"✅ 이미지 완료: {output_path.name}")
        
        # 메모리 해제
        del pipeline
        import gc
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
        print("🗑️ 메모리 해제 완료!")
        
        return output_path
    
    # ===================================
    # STEP 3: 자막 추가 (로컬)
    # ===================================
    def add_subtitles(self, image_path, script):
        """자막 추가"""
        print("\n✍️ STEP 3: 자막 추가")
        
        image = Image.open(image_path)
        width, height = image.size
        half_width, half_height = width // 2, height // 2
        
        panels = [
            {"number": 1, "region": (0, 0, half_width, half_height)},
            {"number": 2, "region": (half_width, 0, width, half_height)},
            {"number": 3, "region": (0, half_height, half_width, height)},
            {"number": 4, "region": (half_width, half_height, width, height)}
        ]
        
        try:
            font = ImageFont.truetype(self.config['font_path'], 28)
        except:
            font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(image)
        
        for panel in panels:
            panel_num = panel['number']
            panel_data = script['panels'][panel_num - 1]
            dialogue = panel_data.get('dialogue', '').strip()
            
            if not dialogue:
                continue
            
            x1, y1, x2, y2 = panel['region']
            center_x = (x1 + x2) // 2
            panel_width = x2 - x1
            max_text_width = panel_width * 0.85
            
            # 줄바꿈
            words = dialogue.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                w = draw.textbbox((0, 0), test_line, font=font)[2]
                
                if w <= max_text_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # 렌더링
            line_height = 36
            start_y = y2 - 60 - len(lines) * line_height // 2
            
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                x = center_x - w // 2
                y = start_y + i * line_height
                
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        if dx or dy:
                            draw.text((x+dx, y+dy), line, fill='black', font=font)
                
                draw.text((x, y), line, fill='white', font=font)
            
            print(f"   ✅ Panel {panel_num}: \"{dialogue}\"")
        
        final_path = self.COMIC_DIR / f"{self.timestamp}_final.png"
        image.save(final_path)
        print(f"✅ 최종: {final_path.name}")
        
        return final_path
    
    # ===================================
    # STEP 4: Notion 업로드 (로컬)
    # ===================================
    def upload_to_notion(self, image_path, script):
        """Notion 업로드"""
        print("\n📝 STEP 4: Notion 업로드")
        
        # Imgur
        with open(image_path, 'rb') as f:
            img_data = base64.b64encode(f.read())
        
        r = requests.post(
            'https://api.imgur.com/3/image',
            headers={'Authorization': f"Client-ID {self.config['imgur_client_id']}"},
            data={'image': img_data}
        )
        
        if r.status_code != 200:
            raise Exception("Imgur failed")
        
        img_url = r.json()['data']['link']
        print("✅ Imgur 완료")
        
        # Notion
        headers = {
            "Authorization": f"Bearer {self.config['notion_token']}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        blocks = [
            {"object": "block", "type": "heading_1", "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": f"📚 {script['collocation']}"}}]
            }},
            {"object": "block", "type": "paragraph", "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": f"📅 {datetime.now().strftime('%Y-%m-%d')}\n💡 {script['nuance_summary']}"}}]
            }},
            {"object": "block", "type": "image", "image": {
                "type": "external", "external": {"url": img_url}
            }},
            {"object": "block", "type": "callout", "callout": {
                "rich_text": [{"type": "text", "text": {"content": script['example_sentence']}}],
                "icon": {"emoji": "💬"}
            }}
        ]
        
        r = requests.patch(
            f"https://api.notion.com/v1/blocks/{self.config['notion_page_id']}/children",
            headers=headers,
            json={"children": blocks}
        )
        
        if r.status_code == 200:
            print("✅ Notion 완료!")
    
    # ===================================
    # 메인 실행
    # ===================================
    def run(self):
        print("=" * 80)
        print("🚀 네컷만화 자동 생성 (VS Code + Colab)")
        print("=" * 80)
        
        try:
            # 1. 대본 생성 (로컬)
            script = self.generate_script()
            
            # 2. 이미지 생성 (Colab GPU - VS Code가 자동으로 Colab 커널 사용!)
            raw_image = self.generate_image(script)
            
            # 3. 자막 추가 (로컬)
            final_image = self.add_subtitles(raw_image, script)
            
            # 4. Notion 업로드 (로컬)
            self.upload_to_notion(final_image, script)
            
            print("\n" + "=" * 80)
            print("🎉 완료!")
            print("=" * 80)
            print(f"📌 {script['collocation']}")
            print(f"📁 {final_image}")
            
        except Exception as e:
            print(f"❌ 오류: {e}")

# ==========================================
# 실행
# ==========================================
if __name__ == "__main__":
    config = {
        'openai_api_key': os.getenv("OPENAI_API_KEY"),
        'notion_token': os.getenv("NOTION_API_KEY"),
        'notion_page_id': os.getenv("NOTION_PAGE_ID"),
        'imgur_client_id': os.getenv("IMGUR_CLIENT_ID"),
        'reference_image_path': "path/to/reference.png",
        'font_path': "path/to/Ames-Regular.otf"
    }
    
    pipeline = AutoComicPipeline(config)
    pipeline.run()