import firebase_admin
from firebase_admin import credentials, firestore, messaging
from firebase_admin import storage as admin_storage
import google.generativeai as genai
import os
import time
import requests
from datetime import datetime
import sys

# 1. 내 Obsidian 저장소의 'Inbox' 폴더 경로
# 예: "C:/Users/User1/Documents/Obsidian Vault/Inbox"
OBSIDIAN_PATH = "C:/Users/ChaHogyeong/Second_brain"

# 2. Gemini API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

# 3. Firebase 서비스 계정 키 파일 이름
FIREBASE_KEY_FILE = "serviceAccountKey.json"

# ==========================================

# 1. Gemini 초기화
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-pro')

# 2. Firebase 초기화
cred = credentials.Certificate(FIREBASE_KEY_FILE)
firebase_admin.initialize_app(cred)
db = firestore.client()

print("🧠 Brain is Active! Waiting for signals from Firebase...")
print(f"📂 Saving notes to: {OBSIDIAN_PATH}")

def generate_markdown(content_type, content_data, image_path=None, mode="study"):
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 🌟 프롬프트
    prompts = {
        # 1. 📝 학습/요약 모드
        "study": """
            Role: Meticulous graduate student teaching assistant.
            Task: Organize the input into study materials.
            Focus: Core concept definitions, logical structure, summaries, key points to memorize.
            Output: Clean Markdown lecture note format.
        """,
        
        # 2. 💻 기술 뉴스/동향 모드
        "tech": """
            Role: IT Technology Trends Specialist Journalist (Tech Journalist).
            Task: Analyze development news, release notes, and technical articles.
            Focus:
            - Core features and emergence context of new technologies.
            - Advantages and disadvantages compared to existing technologies (Trade-offs).
            - Impact on the industry and key points developers should note.
            Output: Technical blog post format (Insight-focused).
        """,
        
        # 3. 🎨 영감/아이디어 모드
        "idea": """
            Role: Creative Planner (Product Manager).
            Task: Derive business/creative ideas from this content.
            Focus: Application methods, related service ideas, brainstorming.
            Output: Idea note format.
        """,
        
        # 4. 📈 경제/투자 공부 모드
        "economy": """
            Role: Friendly Economic/Investment Mentor (Economic Educator).
            Task: Provide commentary on charts or news to enable learning through 'investment knowledge'.
            Focus:
            - Analyze 'market principles' and 'causal relationships' rather than simple buy/sell signals.
            - Explain economic terms that appear and compare them to historical analogies.
            - The impact of this phenomenon on the macroeconomy.
            - Derive the mindset or insights an investor should possess.
            Output: Economic learning notes format.
*** Translated with www.DeepL.com/Translator (free version) ***


        """,

        # 5. 📂 일반/보편적 모드
        "general": """
            Role: Competent knowledge archiving specialist.
            Task: Identify the subject and context of input information, then organize it for easy future retrieval.
            Focus: Topic identification, 3-line summarization, structuring, tag suggestions.
            Output: Easy-to-read Markdown format.
        """
    }
    
    # 선택된 모드의 프롬프트 가져오기 (없으면 study가 기본)
    selected_prompt = prompts.get(mode, prompts["study"])
    
    full_prompt = f"""
    {selected_prompt}
    
    Language: (English).
    Input Type: {content_type}
    Input Context: {content_data}
    Capture Time: {current_time}
    
    Output Requirements:
    - Use Obsidian Markdown format.
    - Add tags: #{mode} #Inbox
    """
    
    try:
        if content_type == "image" and image_path:
            with open(image_path, "rb") as f:
                image_data = f.read()
            response = model.generate_content([full_prompt, {"mime_type": "image/jpeg", "data": image_data}])
        else:
            response = model.generate_content(full_prompt)
        
        # 응답이 제대로 왔는지 확인
        if not response.text:
            raise Exception("Gemini로부터 빈 응답을 받았습니다.")
            
        return response.text

    except Exception as e:
        # 예외를 상위(on_snapshot)로 던져버림
        print(f"🔥 Gemini Generation Error: {e}")
        raise e  # 에러를 호출한 쪽으로 그대로 전달

def save_to_obsidian(title, content):
    # Obsidian 폴더에 .md 파일로 저장
    # 파일명에 사용할 수 없는 특수문자 제거
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"{safe_title}_{int(time.time())}.md"
    full_path = os.path.join(OBSIDIAN_PATH, filename)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✨ Saved to Obsidian: {filename}")

def send_push_notification(title, body):
    # 안드로이드 폰으로 푸시 알림
    try:
        # 'updates'라는 주제를 구독한 기기들에게 메시지 전송
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

def on_snapshot(col_snapshot, changes, read_time):
    """Firebase 변경사항을 실시간으로 감지하는 리스너"""
    for change in changes:
        if change.type.name == 'ADDED':
            doc = change.document
            data = doc.to_dict()
            doc_id = doc.id # 문서 ID 저장
            
            # 상태가 'waiting'인 것만 처리
            if data.get('status') == 'waiting':
                print(f"\n⚡ Signal Detected! Type: {data.get('type')}")
                
                # 처리 상태를 'processing'으로 변경
                doc.reference.update({'status': 'processing'})
                
                temp_image_path = None
                try:
                    content = ""
                    
                    # 1. 이미지 처리
                    if data.get('type') == 'image':
                        image_url = data.get('url')
                        print("Downloading image...")
                        # 이미지 임시 다운로드
                        img_data = requests.get(image_url).content
                        temp_image_path = "temp_image.jpg"
                        with open(temp_image_path, 'wb') as handler:
                            handler.write(img_data)
                        content = "User uploaded an image."
                    
                    # 2. 텍스트 처리
                    elif data.get('type') == 'text':
                        content = data.get('content')
                    
                    # 3. Gemini 분석 요청
                    mode = data.get('mode', 'study')
                    md_result = generate_markdown(data.get('type'), content, temp_image_path, mode)
                    
                    # 4. Obsidian 저장 (제목 추출)
                    # 첫 줄(# Title)에서 제목만 따오기
                    title_line = md_result.split('\n')[0].replace('#', '').strip()
                    if not title_line: title_line = "Untitled Note"
                    
                    save_to_obsidian(title_line, md_result)

                    # 5. 푸시 알림 전송
                    send_push_notification(
                        title="✅ Obsidian 저장 완료",
                        body=f"{title_line}\n(내용이 안전하게 보관되었습니다.)" # 미리보기 내용
                    )
                    
                    # 6. 임시 파일 삭제
                    if temp_image_path and os.path.exists(temp_image_path):
                        os.remove(temp_image_path)

                    # 데이터 청소
                    print("🧹 Cleaning up Firebase data...")
                    # (1) Storage 이미지 삭제 (이미지 타입인 경우만)
                    if data.get('type') == 'image':
                        storage_path = data.get('storagePath') # 안드로이드에서 저장한 경로
                        if storage_path:
                            try:
                                bucket = admin_storage.bucket()
                                blob = bucket.blob(storage_path)
                                blob.delete()
                                print(f"🗑️ Storage image deleted: {storage_path}")
                            except Exception as e:
                                print(f"⚠️ Storage delete failed (might already be gone): {e}")

                    # (2) Firestore 문서 삭제
                    db.collection('queue').document(doc_id).delete()
                    print(f"🗑️ Firestore document deleted: {doc_id}")
                    
                    print("✅ Workflow & Cleanup Completed!")
                    
                except Exception as e:
                    error_message = str(e)
                    print(f"❌ Critical Error: {error_message}")
                    
                    # 1. Firebase에 에러 상태 기록
                    doc.reference.update({
                        'status': 'error',
                        'error_msg': error_message,
                        'processedAt': firestore.SERVER_TIMESTAMP
                    })

                    # 2. 폰으로 긴급 알림 전송
                    send_push_notification(
                        title="🚨 시스템 긴급 정지!",
                        body=f"오류 발생: {error_message[:100]}...\n(관리자 확인이 필요합니다.)"
                    )
                    
                    # 3. 임시 파일 정리
                    if temp_image_path and os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
                        
                    # 치명적인 에러면 프로그램 종료
                    # "400" (잘못된 요청)이나 "API key" 관련 에러 메시지가 포함되어 있는지 확인
                    if "400" in error_message or "API key" in error_message or "PermissionDenied" in error_message:
                        print("🛑 Fatal error detected. Shutting down system for maintenance.")
                        sys.exit(1) # 프로그램 강제 종료

# queue 컬렉션 감시 시작
queue_ref = db.collection('queue')
query_watch = queue_ref.where(filter=firestore.FieldFilter('status', '==', 'waiting'))
query_watch.on_snapshot(on_snapshot)

# 스크립트가 꺼지지 않게 유지
while True:
    time.sleep(1)