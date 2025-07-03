from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
from dotenv import load_dotenv
from pathlib import Path

# 로컬 모듈 import
from models.embeddings import EmbeddingModel
from services.json_search_service import JSONSearchService
from services.answer_generator import AnswerGenerator

# 환경 변수 로딩
load_dotenv()

# FastAPI 앱 초기화
app = FastAPI(
    title="현대자동차 매뉴얼 QA API",
    description="JSON 기반 매뉴얼 질의응답 시스템",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1234", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프론트엔드와 백엔드 차량명 매핑
VEHICLE_MAPPING = {
    # 프론트엔드 -> 백엔드
    "GRANDEUR": "그랜저",
    "SANTAFE": "싼타페",
    "SONATA": "쏘나타",
    "AVANTE": "아반떼", 
    "KONA": "코나",
    "TUCSON": "투싼",
    "PALISADE": "펠리세이드 hybrid"  # 로그에서 펠리세이드 hybrid가 로드됨
}

# 백엔드 -> 프론트엔드 (역방향 매핑)
REVERSE_VEHICLE_MAPPING = {v: k for k, v in VEHICLE_MAPPING.items()}

# 지원하는 차량 목록 (백엔드 기준)
SUPPORTED_VEHICLES = [
    "그랜저 hybrid",
    "그랜저", 
    "싼타페",
    "쏘나타 hybrid",
    "쏘나타",
    "아반떼",
    "코나 electric",
    "코나",
    "투싼 hybrid",
    "투싼",
    "펠리세이드 hybrid"
]

# 프론트엔드에 보낼 차량 목록 (영문)
FRONTEND_VEHICLES = list(VEHICLE_MAPPING.keys())

# 전역 변수
embedding_model = None
vehicle_search_services = {}  # 차량별 검색 서비스
answer_generator = None

# 요청/응답 모델
class Question(BaseModel):
    q: str
    vehicle: Optional[str] = None  # 선택된 차량 (프론트엔드 형식)

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
    vehicles: List[str]  # 프론트엔드용 영문 차량명
    available_vehicles: List[str]  # 실제로 매뉴얼이 업로드된 차량들 (영문)

def map_vehicle_to_backend(frontend_vehicle: str) -> str:
    """프론트엔드 차량명을 백엔드 차량명으로 매핑"""
    return VEHICLE_MAPPING.get(frontend_vehicle, frontend_vehicle)

def map_vehicle_to_frontend(backend_vehicle: str) -> str:
    """백엔드 차량명을 프론트엔드 차량명으로 매핑"""
    return REVERSE_VEHICLE_MAPPING.get(backend_vehicle, backend_vehicle)

# 초기화 함수
async def initialize_services():
    global embedding_model, answer_generator
    
    try:
        # 디렉토리 생성
        os.makedirs("./data/processed", exist_ok=True)
        
        # 임베딩 모델 초기화
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        embedding_model = EmbeddingModel(model_name)
        print(f"✅ 임베딩 모델 로드 완료: {model_name}")
        
        # 답변 생성기 초기화
        answer_generator = AnswerGenerator()
        print("✅ 답변 생성기 초기화 완료")
        
        # 기존 JSON 파일들 로드
        await load_existing_manuals()
        
        return True
        
    except Exception as e:
        print(f"❌ 서비스 초기화 오류: {e}")
        return False

async def load_existing_manuals():
    """기존에 업로드된 매뉴얼 파일들을 로드 (연식 제거)"""
    global vehicle_search_services
    
    data_dir = Path("./data/processed")
    if not data_dir.exists():
        return
    
    # 차량별로 가장 최신 파일만 선택 (연식 제거)
    vehicle_files = {}
    
    for json_file in data_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # JSON 내용에서 차량명 추출 시도
            vehicle_name = None
            
            # 1. file_name 필드에서 추출
            if 'file_name' in json_data:
                vehicle_name = extract_vehicle_from_content(json_data['file_name'])
            
            # 2. 파일명에서 추출
            if not vehicle_name:
                vehicle_name = extract_vehicle_name(json_file.stem)
            
            if vehicle_name and vehicle_name in SUPPORTED_VEHICLES:
                # 년도 추출해서 최신 파일만 유지
                import re
                year_match = re.search(r'(\d{4})', json_file.name)
                year = int(year_match.group(1)) if year_match else 0
                
                # 차량별로 최신 년도 파일만 유지 (연식 없는 이름으로 저장)
                if vehicle_name not in vehicle_files or year > vehicle_files[vehicle_name]['year']:
                    vehicle_files[vehicle_name] = {
                        'file': json_file,
                        'data': json_data,
                        'year': year
                    }
            else:
                print(f"⚠️ 인식되지 않은 차량: {json_file.name} (추출된 이름: {vehicle_name})")
        
        except Exception as e:
            print(f"❌ {json_file} 로드 실패: {e}")
    
    # 선택된 파일들로 검색 서비스 생성 (연식 없는 이름으로)
    for vehicle_name, file_info in vehicle_files.items():
        try:
            search_service = JSONSearchService(embedding_model, auto_load=False)
            search_service.add_document(file_info['data'])
            vehicle_search_services[vehicle_name] = search_service  # 연식 없는 이름으로 저장
            
            sections_count = len(file_info['data'].get("sections", []))
            print(f"✅ {vehicle_name} 매뉴얼 로드 완료: {file_info['file'].name} ({file_info['year']}년, {sections_count}개 섹션)")
        except Exception as e:
            print(f"❌ {vehicle_name} 검색 서비스 생성 실패: {e}")

def extract_vehicle_from_content(content: str) -> str:
    """파일 내용에서 차량명 추출"""
    content_lower = content.lower()
    
    # 그랜저 확인
    if '그랜저' in content or 'granjer' in content_lower or 'grandeur' in content_lower:
        if 'hybrid' in content_lower or 'hev' in content_lower or '하이브리드' in content:
            return '그랜저 hybrid'
        return '그랜저'
    
    # 싼타페 확인
    if '싼타페' in content or 'santafe' in content_lower or 'santa fe' in content_lower:
        return '싼타페'
    
    # 쏘나타 확인
    if '쏘나타' in content or 'sonata' in content_lower:
        if 'hybrid' in content_lower or 'hev' in content_lower or '하이브리드' in content:
            return '쏘나타 hybrid'
        return '쏘나타'
    
    # 아반떼 확인
    if '아반떼' in content or 'avante' in content_lower or 'elantra' in content_lower:
        return '아반떼'
    
    # 코나 확인
    if '코나' in content or 'kona' in content_lower:
        if 'electric' in content_lower or 'ev' in content_lower or '일렉트릭' in content or '전기' in content:
            return '코나 electric'
        return '코나'
    
    # 투싼 확인
    if '투싼' in content or 'tucson' in content_lower:
        if 'hybrid' in content_lower or 'hev' in content_lower or '하이브리드' in content:
            return '투싼 hybrid'
        return '투싼'
    
    # 펠리세이드 확인 (팰리세이드도 포함)
    if '펠리세이드' in content or '팰리세이드' in content or 'palisade' in content_lower:
        if 'hybrid' in content_lower or 'hev' in content_lower or '하이브리드' in content:
            return '펠리세이드 hybrid'
        return '펠리세이드'
    
    return None

def extract_vehicle_name(filename: str) -> str:
    """파일명에서 차량명 추출"""
    filename_lower = filename.lower()
    
    # 직접 매칭
    if 'granzer' in filename_lower or '그랜저' in filename_lower:
        if 'hybrid' in filename_lower or 'hev' in filename_lower:
            return '그랜저 hybrid'
        return '그랜저'
    
    if 'santafe' in filename_lower or '싼타페' in filename_lower:
        return '싼타페'
    
    if 'sonata' in filename_lower or '쏘나타' in filename_lower:
        if 'hybrid' in filename_lower or 'hev' in filename_lower:
            return '쏘나타 hybrid'
        return '쏘나타'
    
    if 'avante' in filename_lower or '아반떼' in filename_lower:
        return '아반떼'
    
    if 'kona' in filename_lower or '코나' in filename_lower:
        if 'electric' in filename_lower or 'ev' in filename_lower:
            return '코나 electric'
        return '코나'
    
    if 'tucson' in filename_lower or '투싼' in filename_lower:
        if 'hybrid' in filename_lower or 'hev' in filename_lower:
            return '투싼 hybrid'
        return '투싼'
    
    if 'palisade' in filename_lower or '펠리세이드' in filename_lower or '팰리세이드' in filename_lower:
        if 'hybrid' in filename_lower or 'hev' in filename_lower:
            return '펠리세이드 hybrid'
        return '펠리세이드'
    
    # 파일명에서 직접 추출 (한글 파일명 지원)
    for vehicle in SUPPORTED_VEHICLES:
        if vehicle.replace(' ', '').lower() in filename_lower.replace(' ', '').replace('_', ''):
            return vehicle
    
    return filename

def generate_vehicle_filename(vehicle_name: str) -> str:
    """차량명을 파일명으로 변환"""
    name_mapping = {
        '그랜저 hybrid': 'granzer_hybrid_manual.json',
        '그랜저': 'granzer_manual.json',
        '싼타페': 'santafe_manual.json',
        '쏘나타 hybrid': 'sonata_hybrid_manual.json',
        '쏘나타': 'sonata_manual.json',
        '아반떼': 'avante_manual.json',
        '코나 electric': 'kona_electric_manual.json',
        '코나': 'kona_manual.json',
        '투싼 hybrid': 'tucson_hybrid_manual.json',
        '투싼': 'tucson_manual.json',
        '펠리세이드 hybrid': 'palisade_hybrid_manual.json'
    }
    
    return name_mapping.get(vehicle_name, f"{vehicle_name.replace(' ', '_')}_manual.json")

# 앱 시작 이벤트
@app.on_event("startup")
async def startup_event():
    success = await initialize_services()
    if not success:
        print("⚠️ 서비스 초기화 실패")

# API 엔드포인트들
@app.get("/")
def root():
    # 백엔드 차량명을 프론트엔드 형식으로 변환
    available_vehicles_frontend = [
        map_vehicle_to_frontend(vehicle) 
        for vehicle in vehicle_search_services.keys()
    ]
    
    return {
        "message": "현대자동차 매뉴얼 QA 시스템 v2.0",
        "supported_vehicles": FRONTEND_VEHICLES,
        "available_vehicles": available_vehicles_frontend,
        "backend_vehicles": list(vehicle_search_services.keys()),
        "endpoints": {
            "차량 목록": "GET /vehicles",
            "JSON 업로드": "POST /upload_json/{vehicle}",
            "질문하기": "POST /ask", 
            "디버깅 검색": "POST /debug_search",
            "건강상태": "GET /health"
        }
    }

@app.get("/vehicles", response_model=VehicleListResponse)
def get_vehicles():
    """지원하는 차량 목록과 사용 가능한 차량 목록 반환 (프론트엔드 형식)"""
    # 백엔드에서 로드된 차량들을 프론트엔드 형식으로 변환
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
        "embedding_model_ready": embedding_model is not None,
        "answer_generator_ready": answer_generator is not None,
        "supported_vehicles": len(FRONTEND_VEHICLES),
        "available_vehicles": len(available_vehicles_frontend),
        "loaded_manuals": available_vehicles_frontend,
        "backend_vehicles": list(vehicle_search_services.keys())
    }

# JSON 업로드 엔드포인트 (차량별)
@app.post("/upload_json/{vehicle}", response_model=UploadResponse)
async def upload_json(vehicle: str, file: UploadFile = File(...)):
    """특정 차량의 JSON 파일 업로드"""
    
    # 프론트엔드 차량명을 백엔드 형식으로 변환
    backend_vehicle = map_vehicle_to_backend(vehicle)
    
    if backend_vehicle not in SUPPORTED_VEHICLES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 차량입니다. 지원 차량: {FRONTEND_VEHICLES}")
    
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="JSON 파일만 업로드 가능합니다.")
    
    if not embedding_model:
        raise HTTPException(status_code=503, detail="임베딩 모델이 초기화되지 않았습니다.")
    
    try:
        # JSON 파일 읽기
        content = await file.read()
        json_data = json.loads(content.decode('utf-8'))
        
        # JSON 구조 검증
        if not isinstance(json_data, dict) or "sections" not in json_data:
            raise HTTPException(status_code=400, detail="올바른 JSON 구조가 아닙니다. 'sections' 필드가 필요합니다.")
        
        # 차량별 파일명 생성
        filename = generate_vehicle_filename(backend_vehicle)
        save_path = Path("./data/processed") / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # 차량별 검색 서비스 생성/업데이트 (백엔드 차량명으로 저장)
        search_service = JSONSearchService(embedding_model, auto_load=False)
        search_service.add_document(json_data)
        vehicle_search_services[backend_vehicle] = search_service
        
        sections_count = len(json_data.get("sections", []))
        
        print(f"✅ {backend_vehicle} 매뉴얼 업로드 완료: {filename}")
        print(f"   📊 섹션 수: {sections_count}")
        
        return UploadResponse(
            message=f"'{vehicle}' 매뉴얼 업로드 및 인덱싱 완료!",
            filename=filename,
            vehicle=vehicle,  # 프론트엔드 형식으로 반환
            sections_count=sections_count
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="잘못된 JSON 형식입니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JSON 파일 처리 중 오류: {str(e)}")

# 질문 응답 엔드포인트
@app.post("/ask", response_model=QuestionResponse)
async def ask_question(item: Question):
    """선택된 차량의 매뉴얼을 기반으로 질문에 답변"""
    
    if not item.vehicle:
        raise HTTPException(status_code=400, detail="차량을 선택해주세요.")
    
    # 프론트엔드 차량명을 백엔드 형식으로 변환
    backend_vehicle = map_vehicle_to_backend(item.vehicle)
    
    print(f"🔍 {item.vehicle} ({backend_vehicle}) 매뉴얼에서 검색 시작: '{item.q}'")
    
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
        # 선택된 차량의 검색 서비스만 사용
        search_service = vehicle_search_services[backend_vehicle]
        
        print(f"🔍 {backend_vehicle} 매뉴얼 검색 시작: '{item.q}'")
        
        results = search_service.search_sections(item.q, k=3)
        
        if not results:
            return QuestionResponse(
                answer=f"'{item.vehicle}' 매뉴얼에서 관련 정보를 찾을 수 없습니다.",
                vehicle=item.vehicle,
                sources=[]
            )
        
        print(f"📊 {backend_vehicle} 검색 결과: {len(results)}개 섹션 발견")
        for i, result in enumerate(results):
            print(f"  {i+1}. [{result['score']:.3f}] {result['title']} (페이지 {result['page_range']})")
        
        # 최고 점수 섹션으로 답변 생성
        best_section = results[0]
        
        print(f"🤖 답변 생성 중 - 섹션: {best_section['title']}")
        print(f"   전체 내용 길이: {len(best_section['content'])}자")
        print(f"   내용 미리보기: {best_section['content'][:200]}...")
        
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
            vehicle=item.vehicle,  # 프론트엔드 형식으로 반환
            sources=sources
        )
        
    except Exception as e:
        print(f"❌ {backend_vehicle} 질문 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"질문 처리 중 오류: {str(e)}")

# 디버깅 검색 엔드포인트
@app.post("/debug_search")
async def debug_search(item: Question):
    """검색 결과 상세 분석"""
    
    if not item.vehicle:
        raise HTTPException(status_code=400, detail="차량을 선택해주세요.")
    
    # 프론트엔드 차량명을 백엔드 형식으로 변환
    backend_vehicle = map_vehicle_to_backend(item.vehicle)
    
    if backend_vehicle not in vehicle_search_services:
        raise HTTPException(status_code=404, detail=f"'{item.vehicle}' 매뉴얼을 찾을 수 없습니다.")
    
    try:
        search_service = vehicle_search_services[backend_vehicle]
        results = search_service.search_sections(item.q, k=3)
        
        if not results:
            return {"message": f"'{item.vehicle}' 매뉴얼에서 검색 결과가 없습니다."}
        
        # 상위 3개 결과의 전체 내용 반환
        detailed_results = []
        for i, result in enumerate(results):
            detailed_results.append({
                "rank": i + 1,
                "title": result["title"],
                "score": result["score"],
                "page_range": result["page_range"],
                "match_details": result["match_details"],
                "full_content": result["content"],
                "content_length": len(result["content"]),
                "keywords": result.get("keywords", [])
            })
        
        return {
            "query": item.q,
            "vehicle": item.vehicle,
            "backend_vehicle": backend_vehicle,
            "total_results": len(results),
            "detailed_results": detailed_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"디버깅 검색 중 오류: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )