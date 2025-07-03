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

# 데이터 디렉토리 생성 (먼저)
RUN mkdir -p /app/data/processed

# 데이터 파일 복사 (있으면)
COPY data/processed/ ./data/processed/

# 앱 코드 복사 (나중에)
COPY . .

# ✅ 캐시 파일 포함
RUN mkdir -p /app/data/processed
COPY data/processed/*.pkl /app/data/processed/

# 포트 노출
EXPOSE 8080

# 환경 변수 설정
ENV HOST=0.0.0.0
ENV PORT=8080

# 앱 실행
CMD ["python", "main.py"]