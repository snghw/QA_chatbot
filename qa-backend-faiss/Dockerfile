FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
# ✅ openai만 먼저 명시적으로 강제 설치
RUN pip install --no-cache-dir openai==1.6.1 && pip show openai

# 나머지 의존성 설치 (순서가 중요)
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 코드 복사
COPY . /app

# ✅ 포트 노출
EXPOSE 8080

# ✅ 환경 변수
ENV HOST=0.0.0.0
ENV PORT=8080

# ✅ 앱 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
