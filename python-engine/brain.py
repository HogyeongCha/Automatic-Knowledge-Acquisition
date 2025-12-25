import firebase_admin
from firebase_admin import credentials, firestore, messaging
from firebase_admin import storage as admin_storage

# [NEW] 새로운 Gemini SDK Import
from google import genai
from google.genai.types import Tool, GenerateContentConfig, Part

import os
import time
import requests
from datetime import datetime
import sys

# ==========================================
# ⚙️ 설정 및 초기화
# ==========================================

# 1. 내 Obsidian 저장소의 'Inbox' 폴더 경로
OBSIDIAN_PATH = "C:/Users/ChaHogyeong/Second_brain"

# 2. Gemini API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

# 3. Firebase 서비스 계정 키 파일 이름
FIREBASE_KEY_FILE = "serviceAccountKey.json"
FIREBASE_CONFIG = {
    'storageBucket': 'autoknowledgeacquisition.firebasestorage.app' 
}

# [NEW] Gemini Client 초기화 (v2 방식)
client = genai.Client(api_key=GEMINI_API_KEY)

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_FILE)
    firebase_admin.initialize_app(cred, FIREBASE_CONFIG)

db = firestore.client()

print("🧠 Brain is Active (v2.0 with URL Context)! Waiting for signals...")
print(f"📂 Saving notes to: {OBSIDIAN_PATH}")

# ==========================================
# 🛠️ 핵심 기능 함수
# ==========================================

def generate_markdown(content_type, content_data, image_path=None, mode="study"):
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 🌟 프롬프트 정의
    prompts = {
        "study": """
            Role: Meticulous graduate student teaching assistant.
            Task: Organize the input into study materials.
            Focus: Core concept definitions, logical structure, summaries, key points to memorize.
            Output: Clean Markdown lecture note format.
        """,
        "tech": """
            Role: IT Technology Trends Specialist Journalist.
            Task: Analyze development news, release notes, and technical articles.
            Focus: Core features, context, trade-offs, and industry impact.
            Output: Technical blog post format (Insight-focused).
        """,
        "idea": """
            Role: Creative Planner (PM).
            Task: Derive business/creative ideas from this content.
            Focus: Application methods, related service ideas, brainstorming.
            Output: Idea note format.
        """,
        "economy": """
            Role: Friendly Economic/Investment Mentor.
            Task: Provide commentary on charts or news for 'investment knowledge'.
            Focus: Market principles, causal relationships, macroeconomy impact.
            Output: Economic learning notes format.
        """,
        "general": """
            Role: Competent knowledge archiving specialist.
            Task: Identify subject and context, organize for retrieval.
            Focus: Topic identification, 3-line summarization, structuring, tags.
            Output: Easy-to-read Markdown format.
        """
    }
    
    base_prompt = prompts.get(mode, prompts["study"])
    
    # [NEW] 도구(Tool) 설정
    tools = []
    final_input_content = ""

    # 1. URL 타입일 경우: URL Context 도구 활성화
    if content_type == "url":
        tools = [{"url_context": {}}]
        # 프롬프트에 URL을 명시적으로 포함
        final_input_content = f"Please analyze the content of this URL: {content_data}"
    else:
        # 텍스트/이미지일 경우
        final_input_content = content_data

    full_prompt = f"""
    {base_prompt}
    
    Language: Korean (Translate insights into Korean).
    Input Type: {content_type}
    Input Context: {final_input_content}
    Capture Time: {current_time}
    
    Output Requirements:
    - Use Obsidian Markdown format.
    - Start with a clear # Title at the very first line.
    - Add tags: #{mode} #Inbox #{content_type}
    """
    
    try:
        # [NEW] 설정 객체 생성
        config = GenerateContentConfig(
            tools=tools,
            response_mime_type="text/plain" 
        )
        
        # 모델 선택 (Flash 모델이 도구 사용 속도가 빠름)
        model_id = "gemini-2.5-pro"

        response = None

        # A. 이미지 처리
        if content_type == "image" and image_path:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            # 이미지 바이트와 텍스트 프롬프트를 함께 전송
            response = client.models.generate_content(
                model=model_id,
                contents=[full_prompt, Part.from_bytes(data=image_bytes, mime_type="image/jpeg")],
                config=config
            )
            
        # B. 텍스트 또는 URL 처리
        else:
            response = client.models.generate_content(
                model=model_id,
                contents=full_prompt,
                config=config
            )
        
        if not response.text:
            raise Exception("Gemini로부터 빈 응답을 받았습니다.")
            
        # [디버깅] URL 메타데이터 확인 (URL이 제대로 읽혔는지 콘솔 출력)
        if content_type == "url" and response.candidates[0].url_context_metadata:
             print(f"🔗 URL Metadata: {response.candidates[0].url_context_metadata}")

        return response.text

    except Exception as e:
        print(f"🔥 Gemini Generation Error: {e}")
        raise e

def save_to_obsidian(title, content):
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    # 파일명이 너무 길어지는 것 방지
    if len(safe_title) > 50: 
        safe_title = safe_title[:50]
        
    filename = f"{safe_title}_{int(time.time())}.md"
    full_path = os.path.join(OBSIDIAN_PATH, filename)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✨ Saved to Obsidian: {filename}")

def send_push_notification(title, body):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            topic='updates',
        )
        response = messaging.send(message)
        print(f"📲 Push sent: {response}")
    except Exception as e:
        print(f"❌ Push failed: {e}")

# ==========================================
# 📡 Firebase 리스너
# ==========================================

def on_snapshot(col_snapshot, changes, read_time):
    for change in changes:
        if change.type.name == 'ADDED':
            doc = change.document
            data = doc.to_dict()
            doc_id = doc.id
            
            if data.get('status') == 'waiting':
                print(f"\n⚡ Signal Detected! Type: {data.get('type')}")
                
                # 중복 처리 방지를 위해 즉시 상태 변경
                doc.reference.update({'status': 'processing'})
                
                temp_image_path = None
                try:
                    content = ""
                    input_type = data.get('type')
                    
                    # 1. 이미지 다운로드 처리
                    if input_type == 'image':
                        image_url = data.get('url')
                        print("Downloading image...")
                        img_data = requests.get(image_url).content
                        temp_image_path = "temp_image.jpg"
                        with open(temp_image_path, 'wb') as handler:
                            handler.write(img_data)
                        content = "User uploaded an image."
                    
                    # 2. 텍스트 처리
                    elif input_type == 'text':
                        content = data.get('content')
                        
                    # 3. [NEW] URL 처리
                    elif input_type == 'url':
                        content = data.get('url') # 앱에서 'url' 필드에 링크를 담아 보내야 함
                        print(f"🔗 Processing Link: {content}")
                    
                    # Gemini 호출
                    mode = data.get('mode', 'study')
                    md_result = generate_markdown(input_type, content, temp_image_path, mode)
                    
                    # 제목 추출
                    title_line = md_result.split('\n')[0].replace('#', '').strip()
                    if not title_line: title_line = "Untitled Note"
                    
                    # 저장
                    save_to_obsidian(title_line, md_result)
                    
                    # 푸시 알림
                    send_push_notification(
                        title="✅ Obsidian 저장 완료",
                        body=f"{title_line}"
                    )
                    
                    # 정리 (이미지)
                    if temp_image_path and os.path.exists(temp_image_path):
                        os.remove(temp_image_path)

                    # 정리 (Firebase 데이터 삭제)
                    print("🧹 Cleaning up Firebase data...")
                    
                    # Storage 이미지 삭제
                    if input_type == 'image':
                        storage_path = data.get('storagePath')
                        if storage_path:
                            try:
                                bucket = admin_storage.bucket()
                                blob = bucket.blob(storage_path)
                                blob.delete()
                                print(f"🗑️ Storage image deleted: {storage_path}")
                            except Exception as e:
                                print(f"⚠️ Storage delete failed: {e}")

                    # Firestore 문서 삭제
                    db.collection('queue').document(doc_id).delete()
                    print("✅ Workflow Completed!")
                    
                except Exception as e:
                    error_message = str(e)
                    print(f"❌ Critical Error: {error_message}")
                    
                    doc.reference.update({
                        'status': 'error',
                        'error_msg': error_message,
                        'processedAt': firestore.SERVER_TIMESTAMP
                    })

                    send_push_notification(
                        title="🚨 시스템 에러",
                        body=f"오류 발생: {error_message[:50]}..."
                    )
                    
                    if temp_image_path and os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
                    
                    if "400" in error_message or "API key" in error_message:
                        print("🛑 Fatal error. Shutting down.")
                        sys.exit(1)

# 리스너 시작
queue_ref = db.collection('queue')
query_watch = queue_ref.where(filter=firestore.FieldFilter('status', '==', 'waiting'))
query_watch.on_snapshot(on_snapshot)

while True:
    time.sleep(1)