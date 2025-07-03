import json
import numpy as np
import os
import pickle
from typing import List, Dict, Any
from pathlib import Path

class JSONSearchService:
    def __init__(self, embedding_model, auto_load: bool = False, data_path: str = "./data/processed/"):
        self.embedding_model = embedding_model
        self.data_path = Path(data_path)
        self.documents = []
        
        # 🚀 임베딩 캐시 관련
        self.section_embeddings = None  # numpy array of embeddings
        self.sections_data = []  # list of section metadata
        self.embeddings_cached = False  # 🔥 중요: 이 플래그가 핵심!
        
        if auto_load:
            self.load_all_documents()
    
    def add_document(self, json_data: Dict[str, Any]):
        """새 JSON 문서 추가 및 임베딩 생성/로드"""
        if "sections" not in json_data:
            print("❌ sections 필드가 없습니다.")
            return
            
        self.documents = [json_data]
        vehicle_name = self._extract_vehicle_name_from_data(json_data)
        sections_count = len(json_data.get("sections", []))
        
        print(f"📄 {vehicle_name} 매뉴얼 추가: {sections_count}개 섹션")
        
        # 캐시 파일 확인 및 로드/생성
        self._precompute_embeddings(json_data, vehicle_name)
    
    def _precompute_embeddings(self, json_data: Dict[str, Any], vehicle_name: str):
        """섹션별 임베딩을 미리 계산하여 캐싱"""
        cache_file = self.data_path / f"{vehicle_name}_embeddings.pkl"
        
        # 🔍 기존 캐시 확인
        if cache_file.exists():
            try:
                print(f"💾 {vehicle_name} 기존 임베딩 캐시 로드 중...")
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.section_embeddings = cache_data['embeddings']
                    self.sections_data = cache_data['sections_data']
                    self.embeddings_cached = True  # 🔥 플래그 설정!
                print(f"✅ {vehicle_name} 캐시된 임베딩 로드 완료 ({len(self.sections_data)}개 섹션)")
                return
            except Exception as e:
                print(f"⚠️ 캐시 로드 실패, 새로 생성: {e}")
        
        # 🚫 캐시가 없으면 에러 (배포 환경에서는 생성하지 않음)
        print(f"❌ {vehicle_name} 임베딩 캐시 파일이 없습니다: {cache_file}")
        print("💡 로컬에서 create_embeddings.py를 실행하여 캐시를 생성해주세요.")
        return
        
    def search_sections(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """🚀 최적화된 검색: 캐시된 임베딩 사용"""
        
        # 🔍 디버깅 로그
        print(f"🔍 [DEBUG] 검색 시작")
        print(f"🔍 [DEBUG] documents 개수: {len(self.documents)}")
        print(f"🔍 [DEBUG] embeddings_cached: {self.embeddings_cached}")
        print(f"🔍 [DEBUG] sections_data 개수: {len(self.sections_data)}")
        print(f"🔍 [DEBUG] section_embeddings 존재: {self.section_embeddings is not None}")
        
        if not self.documents or not self.embeddings_cached:
            print(f"⚠️ 로드된 문서나 임베딩이 없습니다")
            return []
        
        vehicle_name = self._extract_vehicle_name_from_data(self.documents[0])
        print(f"🔍 {vehicle_name} 매뉴얼 검색 시작: '{query}'")
        
        # 🚀 쿼리만 임베딩 계산 (섹션 임베딩은 재사용)
        query_embedding = self.embedding_model.encode_query(query)
        query_norm = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
        
        # 🚀 벡터화된 유사도 계산
        similarities = np.dot(query_norm, self.section_embeddings.T)[0]
        
        search_results = []
        
        # 각 섹션에 대해 점수 계산
        for i, section_data in enumerate(self.sections_data):
            scores = self._calculate_all_scores_optimized(query, section_data, similarities[i])
            total_score = self._calculate_total_score(scores)
            
            if total_score > 0.05:  # 임계값
                search_results.append({
                    "score": total_score,
                    "source": section_data["source"],
                    "section_number": section_data["section_number"],
                    "title": section_data["title"],
                    "page_range": section_data["page_range"],
                    "content": section_data["content"],
                    "keywords": section_data["keywords"],
                    "subsections": section_data["subsections"],
                    "match_details": {
                        "title_score": round(scores["title"], 3),
                        "keyword_score": round(scores["keyword"], 3),
                        "content_score": round(scores["content"], 3),
                        "bonus_score": round(scores["bonus"], 3)
                    }
                })
        
        # 점수순 정렬
        search_results.sort(key=lambda x: x["score"], reverse=True)
        
        print(f"📊 {vehicle_name} 검색 결과: {len(search_results)}개 섹션 (⚡ 캐시 사용)")
        for i, result in enumerate(search_results[:3]):
            print(f"  {i+1}. [{result['score']:.3f}] {result['title']} (페이지 {result['page_range']})")
        
        return search_results[:k]
    
    def _calculate_all_scores_optimized(self, query: str, section_data: Dict, content_similarity: float) -> Dict[str, float]:
        """최적화된 점수 계산: 콘텐츠 유사도는 미리 계산된 값 사용"""
        return {
            "title": self._calculate_title_score(query, section_data["title"]),
            "keyword": self._calculate_keyword_score(query, section_data["keywords"]),
            "content": float(content_similarity),  # 🚀 미리 계산된 유사도 사용
            "bonus": self._calculate_bonus_score(query, section_data)
        }
    
    def _calculate_total_score(self, scores: Dict[str, float]) -> float:
        """종합 점수 계산"""
        return (scores["title"] * 0.6) + (scores["keyword"] * 0.15) + \
               (scores["content"] * 0.15) + (scores["bonus"] * 0.1)
    
    def _calculate_title_score(self, query: str, title: str) -> float:
        """제목 매칭 점수 (간단 버전)"""
        if not title:
            return 0
        
        query_words = set(query.lower().split())
        title_words = set(title.lower().split())
        
        # 기본 매칭
        matches = len(query_words.intersection(title_words))
        return min(matches / max(len(query_words), 1), 1.0)
    
    def _calculate_keyword_score(self, query: str, keywords: List[str]) -> float:
        """키워드 매칭 점수 (간단 버전)"""
        if not keywords:
            return 0
        
        query_lower = query.lower()
        matches = sum(1 for keyword in keywords if keyword.lower() in query_lower)
        return min(matches / 2.0, 1.0)
    
    def _calculate_bonus_score(self, query: str, section: Dict) -> float:
        """보너스 점수 (간단 버전)"""
        content = section.get("content", "").lower()
        query_lower = query.lower()
        
        # 방법, 절차 관련 보너스
        if any(word in query_lower for word in ["방법", "절차", "어떻게"]):
            if any(word in content for word in ["방법", "절차", "단계", "하십시오"]):
                return 0.2
        
        return 0.1
    
    def _extract_vehicle_name_from_data(self, json_data: Dict[str, Any]) -> str:
        """JSON 데이터에서 차량명 추출"""
        file_name = json_data.get("file_name", "").lower()
        
        if "그랜저" in file_name or "granjer" in file_name or "grandeur" in file_name:
            return "그랜저"
        elif "싼타페" in file_name or "santafe" in file_name:
            return "싼타페"
        elif "쏘나타" in file_name or "sonata" in file_name:
            return "쏘나타"
        elif "아반떼" in file_name or "avante" in file_name:
            return "아반떼"
        elif "코나" in file_name or "kona" in file_name:
            return "코나"
        elif "투싼" in file_name or "tucson" in file_name:
            return "투싼"
        elif "펠리세이드" in file_name or "팰리세이드" in file_name or "palisade" in file_name:
            return "펠리세이드"
        
        return "unknown"
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            "documents_count": len(self.documents),
            "total_sections": sum(len(doc.get("sections", [])) for doc in self.documents),
            "embeddings_cached": self.embeddings_cached,
            "cached_sections": len(self.sections_data) if self.embeddings_cached else 0
        }