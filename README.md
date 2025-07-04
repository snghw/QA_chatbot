# 차량 매뉴얼 QA 챗봇 서비스

## 🚗 현대자동차 매뉴얼 QA 챗봇

### 1. 프로젝트 소개

- 현대자동차 차량 매뉴얼을 기반으로 사용자의 질문에 친근하고 유용한 답변을 제공하는 **AI 챗봇 서비스**  

- OpenAI 또는 키워드 기반 문장 추출 방식으로, 차량 관리와 관련된 질문에 빠르게 답변

### 2. 기획 의도

- 방대한 양의 차량 매뉴얼을 직접 읽지 않고 필요할 때 신속하게 정확한 정보를 얻을 수 있도록 하기 위함

### 🔗 배포 링크

https://qa-chatbot-git-main-songhwas-projects.vercel.app/

> - 초기 진입 시 차량 모델을 선택하고 질문을 입력하면 AI가 답변합니다.  
> - OpenAI API 키가 없는 경우에도 키워드 기반 답변이 제공됩니다.

### 3. 사용법

1. 웹사이트에 접속
2. 보유 중인 차량 모델 선택
3. 차량 관련 질문 입력 (예: "엔진오일 교체 주기는?", "타이어 점검 방법은?")
4. 챗봇이 매뉴얼 내용을 기반으로 상세하고 친근한 답변 제공
5. 답변 하단에서 참고한 매뉴얼 페이지 정보 확인 가능

### 4. 로컬 실행 방법

#### 1. 환경 설정
```bash
# 프로젝트 다운로드
git clone https://github.com/your-username/qa-backend.git

# 경로 이동
cd qa-backend

# 가상환경 생성
python -m venv venv

# 가상환경 실행
source venv/bin/activate  
# (Windows: venv\Scripts\activate)

# 필수 라이브러리 설치
pip install --no-cache-dir -r requirements.txt
```

#### 2. 서버 실행
```bash
python main.py
```

#### 3. 디렉토리 구조 요약
```bash
qa-backend/
├── main.py               # FastAPI 엔트리 포인트
├── service/              # AnswerGenerator 클래스 포함
├── data/                 # 매뉴얼 JSON 데이터
├── requirements.txt
└── .env                  # (옵션) 환경 변수 파일
```
### 주요 기술 스택

- Frontend : React

- Backend: FastAPI, Uvicorn

- NLP/AI: OpenAI GPT (1.6.1), LangChain

- Search: 키워드 기반 유사 문서 검색 

- Deployment: Vercel, Fly.io