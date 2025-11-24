---
## 🧠 Automatic-Knowledge-Acquisition (aka ToSecondBrain)

> **"내 손안의 정보를 가장 간편하게 제2의 뇌(Second Brain)로 연결하는 파이프라인"**

스마트폰에서 발견한 유용한 정보(텍스트, 이미지, 뉴스 기사 등)를 공유 버튼 한 번으로 AI가 분석하여, PC에 있는 로컬 Obsidian Vault에 자동으로 정리해 주는 개인화된 자동화 시스템입니다.

### 🚀 주요 기능 (Key Features)

* **📱 간편한 모바일 수집:** 안드로이드 공유 메뉴를 통해 텍스트, 이미지(단일/다중)를 즉시 전송합니다.
* **🤖 5가지 AI 페르소나 분석:** 상황에 맞는 프롬프트 모드를 선택하여 데이터를 원하는 관점으로 분석합니다.
  * 📝 **학습 노트:** 대학원생 조교 스타일의 꼼꼼한 개념 정리.
  * 💻 **기술 뉴스:** IT 전문 기자가 분석하는 신기술 트렌드 및 인사이트.
  * 🎨 **아이디어:** 기획자 관점의 창의적 응용 및 브레인스토밍.
  * 📈 **경제 공부:** 친절한 멘토가 설명하는 시장 원리와 경제 지식.
  * 📂 **일반/기타:** 유능한 사서가 정리해 주는 깔끔한 요약 및 아카이빙.
* **⚡ 실시간 처리 & 알림:** PC가 켜져 있으면 즉시 처리되며, 완료 시 스마트폰으로 푸시 알림을 받습니다.
* **💎 Obsidian 완벽 연동:** 분석 결과가 태그가 포함된 Markdown 파일로 내 Obsidian Inbox 폴더에 자동 저장됩니다.
* **🧹 유지비용 제로(Zero Maintenance):** 처리가 완료되면 클라우드(Firebase)의 원본 데이터는 자동으로 삭제되어 비용이 발생하지 않습니다.
* **🪟 윈도우 자동 실행:** PC 부팅 시 백그라운드에서 Python 엔진이 자동으로 시작됩니다.
---
### 🛠️ 시스템 아키텍처 (How it Works)

이 시스템은  **안드로이드 앱(Client)** ,  **Firebase(Middleware)** , **Python 스크립트(Server/Engine)**의 3박자로 작동합니다.

**코드 스니펫**

```
sequenceDiagram
    participant Phone as 📱 Android App
    participant Firebase as 🔥 Firebase (DB/Storage)
    participant PC as 💻 Python Brain (PC)
    participant Gemini as 🤖 Google Gemini API
    participant Obsidian as 💎 Local Obsidian Vault

    Note over Phone, PC: 1. 데이터 수집 단계
    Phone->>Phone: 콘텐츠 공유 & 모드 선택
    Phone->>Firebase: 데이터 업로드 (Waiting 상태)

    Note over Firebase, Obsidian: 2. 처리 및 저장 단계
    loop 실시간 감시 (Real-time Listener)
        PC->>Firebase: 새로운 작업 감지!
    end
    PC->>Firebase: 데이터 다운로드 & 상태 변경 (Processing)
    PC->>Gemini: 선택된 모드의 프롬프트로 분석 요청
    Gemini-->>PC: Markdown 결과 반환
    PC->>Obsidian: .md 파일로 로컬 저장

    Note over PC, Phone: 3. 마무리 단계
    PC->>Firebase: 원본 데이터 삭제 (Cleanup)
    Firebase-->>Phone: FCM 푸시 알림 전송 (완료 신호)
```

---

### 🏗️ 기술 스택 (Tech Stack)

| **영역**         | **기술**     | **설명**                                         |
| ---------------------- | ------------------ | ------------------------------------------------------ |
| **Client (App)** | Java, Android SDK  | 데이터 전송, 모드 선택 UI, FCM 알림 수신               |
| **Middleware**   | Firebase Firestore | 실시간 작업 큐(Queue) 데이터베이스                     |
|                        | Firebase Storage   | 이미지 파일 임시 저장소                                |
|                        | Firebase FCM       | 처리 완료 푸시 알림 서비스                             |
| **Engine (PC)**  | Python 3.x         | 메인 컨트롤 타워. Firebase 리스닝 및 로직 처리         |
| **AI Model**     | Google Gemini Pro  | (`google.generativeai`) 콘텐츠 분석 및 마크다운 생성 |
| **Destination**  | Obsidian           | 최종 결과물이 저장되는 로컬 지식 관리 도구             |

---

### 📂 프로젝트 구조 (Directory Structure)

```
Automatic-Knowledge-Acquisition/  (프로젝트 루트)
├── 📜 brain.py               # 🌟 핵심 엔진: Python 메인 스크립트
├── 📜 run_brain.bat          # 윈도우 자동 실행용 배치 파일
├── 🔑 serviceAccountKey.json # Firebase 관리자 인증키 (보안 주의!)
└── 📜 README.md              # 프로젝트 설명서
```

*(안드로이드 앱 프로젝트는 별도 폴더에서 관리)*

---

### ⚙️ 설치 및 환경 설정 (Setup Guide)

*이 프로젝트는 개인화된 환경 설정이 필요합니다.*

#### 1. 필수 요구사항

* Python 3.x 설치
* Firebase 프로젝트 생성 (Firestore, Storage, FCM 활성화)
* Google Cloud Platform에서 Gemini API Key 발급
* 사용하려면 `GEMINI_API_KEY`라는 환경 변수를 설정해야 합니다.

#### 2. Python 엔진 설정

1. 필요한 라이브러리 설치:
   **Bash**

   ```
   pip install firebase-admin google-generativeai requests
   ```
2. Firebase 콘솔에서 `serviceAccountKey.json`을 다운로드하여 프로젝트 루트에 배치.
3. `brain.py` 상단의 환경 변수 수정:

   * `OBSIDIAN_PATH`: 내 Obsidian Inbox 로컬 절대 경로 설정.
   * `GEMINI_API_KEY`: 발급받은 API Key 입력.

#### 3. 윈도우 자동 실행 등록

1. `run_brain.bat` 파일의 바로 가기 생성.
2. 실행 창(`Win + R`)에 `shell:startup` 입력 후 열리는 폴더에 바로 가기 이동.

#### 4. 안드로이드 앱 설정

1. Firebase 콘솔에서 `google-services.json`을 다운로드하여 안드로이드 프로젝트 `app/` 폴더에 배치.
2. 앱 빌드 및 스마트폰 설치.

---

### 📝 사용 방법 (Usage)

1. PC가 켜져 있는지 확인합니다. (부팅 시 자동으로 검은색 커맨드 창이 실행되어 있어야 함)
2. 스마트폰의 갤러리, 브라우저 등에서 공유 버튼을 누릅니다.
3. 앱 목록에서 **ToSecondBrain**을 선택합니다.
4. 나타나는 팝업에서 원하는 **분석 모드**를 선택합니다.
5. 잠시 후 PC 처리가 완료되면 스마트폰으로 알림이 오고, Obsidian에 파일이 생성됩니다.

---

<div align="center">

Made by HoKyoung Cha for a better knowledge workflow. 🧠

</div>
