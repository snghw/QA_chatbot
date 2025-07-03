from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import logging
from dotenv import load_dotenv
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🚀 간단한 모듈 import (임베딩 모델 제거)
try:
    from services.simple_search import SimpleSearchService
    from services.answer_generator import AnswerGenerator
    logger.info("✅ 모든 모듈 임포트 성공")
except ImportError as e:
    logger.error(f"❌ 모듈 임포트 실패: {e}")
    raise

# 환경 변수 로딩
load_dotenv()

# 환경 변수에서 포트 정보 가져오기
PORT = int(os.getenv("PORT", "8080"))
HOST = os.getenv("HOST", "0.0.0.0")

logger.info(f"🚀 서버 설정: {HOST}:{PORT}")

# FastAPI 앱 초기화
app = FastAPI(
    title="현대자동차 매뉴얼 QA API (Simple)",
    description="키워드 기반 매뉴얼 질의응답 시스템",
    version="3.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1234",
        "https://qa-chatbot-pink.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프론트엔드와 백엔드 차량명 매핑
VEHICLE_MAPPING = {
    "GRANDEUR": "그랜저",
    "SANTAFE": "싼타페",
    "SONATA": "쏘나타",
    "AVANTE": "아반떼", 
    "KONA": "코나",
    "TUCSON": "투싼",
    "PALISADE": "펠리세이드"
}

# 백엔드 -> 프론트엔드 (역방향 매핑)
REVERSE_VEHICLE_MAPPING = {v: k for k, v in VEHICLE_MAPPING.items()}

# 지원하는 차량 목록 (백엔드 기준)
SUPPORTED_VEHICLES = [
    "그랜저", "싼타페", "쏘나타", "아반떼", "코나", "투싼", "펠리세이드"
]

# 프론트엔드에 보낼 차량 목록 (영문)
FRONTEND_VEHICLES = list(VEHICLE_MAPPING.keys())

# 전역 변수 (임베딩 모델 제거)
vehicle_search_services = {}  # 차량별 검색 서비스
answer_generator = None

# 요청/응답 모델
class Question(BaseModel):
    q: str
    vehicle: Optional[str] = None

class QuestionResponse(BaseModel):
    answer: str
    vehicle: str
    sources: List[Dict[str, Any]] = []

class UploadResponse(BaseModel):
    message: str
    filename: str
    vehicle: str
    sections_count: int

class VehicleListResponse(BaseModel):
    vehicles: List[str]
    available_vehicles: List[str]

def map_vehicle_to_backend(frontend_vehicle: str) -> str:
    """프론트엔드 차량명을 백엔드 차량명으로 매핑"""
    return VEHICLE_MAPPING.get(frontend_vehicle, frontend_vehicle)

def map_vehicle_to_frontend(backend_vehicle: str) -> str:
    """백엔드 차량명을 프론트엔드 차량명으로 매핑"""
    return REVERSE_VEHICLE_MAPPING.get(backend_vehicle, backend_vehicle)

# 초기화 함수 (매우 간단)
async def initialize_services():
    global answer_generator
    
    try:
        # 데이터 디렉토리 생성
        data_dir = Path("./data/processed")
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ 데이터 디렉토리 생성: {data_dir.absolute()}")
        
        # 답변 생성기만 초기화 (임베딩 모델 제거)
        answer_generator = AnswerGenerator()
        logger.info("✅ 답변 생성기 초기화 완료")
        
        # 기존 JSON 파일들 로드
        await load_existing_manuals()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 서비스 초기화 오류: {e}")
        return False

async def load_existing_manuals():
    """기존에 업로드된 JSON 파일들을 간단하게 로드"""
    global vehicle_search_services
    
    data_dir = Path("./data/processed")
    if not data_dir.exists():
        logger.warning(f"⚠️ 데이터 디렉토리가 존재하지 않음: {data_dir}")
        return
    
    # JSON 파일들 로드
    for json_file in data_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # 차량명 추출
            vehicle_name = extract_vehicle_name(json_file.stem)
            
            if vehicle_name and vehicle_name in SUPPORTED_VEHICLES:
                # 🚀 간단한 검색 서비스 생성
                search_service = SimpleSearchService()
                search_service.add_document(json_data)
                vehicle_search_services[vehicle_name] = search_service
                
                sections_count = len(json_data.get("sections", []))
                logger.info(f"✅ {vehicle_name} 매뉴얼 로드 완료: {json_file.name} ({sections_count}개 섹션)")
            else:
                logger.warning(f"⚠️ 인식되지 않은 차량: {json_file.name}")
        
        except Exception as e:
            logger.error(f"❌ {json_file} 로드 실패: {e}")

def extract_vehicle_name(filename: str) -> str:
    """파일명에서 차량명 추출 (간단 버전)"""
    filename_lower = filename.lower()
    
    for vehicle in SUPPORTED_VEHICLES:
        if vehicle in filename_lower:
            return vehicle
        
        # 영문명도 확인
        english_names = {
            "그랜저": ["grandeur", "granzer"],
            "싼타페": ["santafe", "santa"],
            "쏘나타": ["sonata"],
            "아반떼": ["avante", "elantra"],
            "코나": ["kona"],
            "투싼": ["tucson"],
            "펠리세이드": ["palisade"]
        }
        
        for eng_name in english_names.get(vehicle, []):
            if eng_name in filename_lower:
                return vehicle
    
    return None

def generate_vehicle_filename(vehicle_name: str) -> str:
    """차량명을 파일명으로 변환"""
    return f"{vehicle_name.replace(' ', '_')}_manual.json"

# 앱 시작 이벤트
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 앱 시작 이벤트 시작 (Simple Mode)")
    success = await initialize_services()
    if not success:
        logger.error("⚠️ 서비스 초기화 실패")
    else:
        logger.info("✅ 서비스 초기화 완료")

# API 엔드포인트들
@app.get("/")
def root():
    available_vehicles_frontend = [
        map_vehicle_to_frontend(vehicle) 
        for vehicle in vehicle_search_services.keys()
    ]
    
    return {
        "message": "현대자동차 매뉴얼 QA 시스템 v3.0 (Simple)",
        "status": "healthy",
        "search_method": "keyword_matching",
        "server_info": {
            "host": HOST,
            "port": PORT
        },
        "supported_vehicles": FRONTEND_VEHICLES,
        "available_vehicles": available_vehicles_frontend,
        "backend_vehicles": list(vehicle_search_services.keys()),
        "endpoints": {
            "차량 목록": "GET /vehicles",
            "JSON 업로드": "POST /upload_json/{vehicle}",
            "질문하기": "POST /ask", 
            "건강상태": "GET /health"
        }
    }

@app.get("/vehicles", response_model=VehicleListResponse)
def get_vehicles():
    """지원하는 차량 목록과 사용 가능한 차량 목록 반환"""
    available_vehicles_frontend = [
        map_vehicle_to_frontend(vehicle) 
        for vehicle in vehicle_search_services.keys()
    ]
    
    return VehicleListResponse(
        vehicles=FRONTEND_VEHICLES,
        available_vehicles=available_vehicles_frontend
    )

@app.get("/health")
def health_check():
    available_vehicles_frontend = [
        map_vehicle_to_frontend(vehicle) 
        for vehicle in vehicle_search_services.keys()
    ]
    
    return {
        "status": "healthy",
        "search_method": "keyword_matching",
        "answer_generator_ready": answer_generator is not None,
        "supported_vehicles": len(FRONTEND_VEHICLES),
        "available_vehicles": len(available_vehicles_frontend),
        "loaded_manuals": available_vehicles_frontend,
        "backend_vehicles": list(vehicle_search_services.keys()),
        "server_info": {
            "host": HOST,
            "port": PORT
        }
    }

# JSON 업로드 엔드포인트
@app.post("/upload_json/{vehicle}", response_model=UploadResponse)
async def upload_json(vehicle: str, file: UploadFile = File(...)):
    """특정 차량의 JSON 파일 업로드 (간단 버전)"""
    
    backend_vehicle = map_vehicle_to_backend(vehicle)
    
    if backend_vehicle not in SUPPORTED_VEHICLES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 차량입니다. 지원 차량: {FRONTEND_VEHICLES}")
    
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="JSON 파일만 업로드 가능합니다.")
    
    try:
        # JSON 파일 읽기
        content = await file.read()
        json_data = json.loads(content.decode('utf-8'))
        
        # JSON 구조 검증
        if not isinstance(json_data, dict) or "sections" not in json_data:
            raise HTTPException(status_code=400, detail="올바른 JSON 구조가 아닙니다. 'sections' 필드가 필요합니다.")
        
        # 파일 저장
        filename = generate_vehicle_filename(backend_vehicle)
        save_path = Path("./data/processed") / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # 🚀 간단한 검색 서비스 생성
        search_service = SimpleSearchService()
        search_service.add_document(json_data)
        vehicle_search_services[backend_vehicle] = search_service
        
        sections_count = len(json_data.get("sections", []))
        
        logger.info(f"✅ {backend_vehicle} 매뉴얼 업로드 완료: {filename}")
        logger.info(f"   📊 섹션 수: {sections_count}")
        
        return UploadResponse(
            message=f"'{vehicle}' 매뉴얼 업로드 완료! (키워드 검색 방식)",
            filename=filename,
            vehicle=vehicle,
            sections_count=sections_count
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="잘못된 JSON 형식입니다.")
    except Exception as e:
        logger.error(f"❌ JSON 파일 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"JSON 파일 처리 중 오류: {str(e)}")

# 질문 응답 엔드포인트
@app.post("/ask", response_model=QuestionResponse)
async def ask_question(item: Question):
    """키워드 기반 질문 응답"""
    
    if not item.vehicle:
        raise HTTPException(status_code=400, detail="차량을 선택해주세요.")
    
    backend_vehicle = map_vehicle_to_backend(item.vehicle)
    
    logger.info(f"🔍 {item.vehicle} ({backend_vehicle}) 매뉴얼에서 키워드 검색 시작: '{item.q}'")
    
    if backend_vehicle not in vehicle_search_services:
        available_vehicles_frontend = [
            map_vehicle_to_frontend(vehicle) 
            for vehicle in vehicle_search_services.keys()
        ]
        raise HTTPException(
            status_code=404, 
            detail=f"'{item.vehicle}' 매뉴얼을 찾을 수 없습니다. 사용 가능한 차량: {available_vehicles_frontend}"
        )
    
    if not answer_generator:
        raise HTTPException(status_code=503, detail="답변 생성기가 초기화되지 않았습니다.")
    
    try:
        # 🚀 키워드 기반 검색
        search_service = vehicle_search_services[backend_vehicle]
        results = search_service.search_sections(item.q, k=3)
        
        if not results:
            return QuestionResponse(
                answer=f"'{item.vehicle}' 매뉴얼에서 관련 정보를 찾을 수 없습니다.",
                vehicle=item.vehicle,
                sources=[]
            )
        
        logger.info(f"📊 {backend_vehicle} 검색 결과: {len(results)}개 섹션 발견")
        
        # 최고 점수 섹션으로 답변 생성
        best_section = results[0]
        
        logger.info(f"🤖 답변 생성 중 - 섹션: {best_section['title']}")
        
        answer = await answer_generator.generate_answer(item.q, best_section)
        
        # 소스 정보 구성
        sources = [
            {
                "source": result["source"],
                "section_title": result["title"],
                "page_range": result["page_range"],
                "score": result["score"],
                "match_details": result["match_details"]
            }
            for result in results
        ]
        
        return QuestionResponse(
            answer=answer,
            vehicle=item.vehicle,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"❌ {backend_vehicle} 질문 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"질문 처리 중 오류: {str(e)}")

# 메인 실행 부분
if __name__ == "__main__":
    import uvicorn
    logger.info(f"🚀 서버 시작: {HOST}:{PORT} (Simple Mode)")
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info"
    )