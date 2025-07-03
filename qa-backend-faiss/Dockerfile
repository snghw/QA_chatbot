FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 📦 JSON 파일과 pickle 파일들 복사
# COPY data/processed/*.json ./data/processed/
# COPY data/processed/*.pkl ./data/processed/

# 나머지 코드 복사
COPY . .

# ✅ 포트 노출
EXPOSE 8080

# ✅ 환경 변수
ENV HOST=0.0.0.0
ENV PORT=8080

# ✅ 앱 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
