import json
import re
from typing import List, Dict, Any
from pathlib import Path

class SimpleSearchService:
    def __init__(self, data_path: str = "./data/processed/"):
        self.data_path = Path(data_path)
        self.documents = []
        self.sections_data = []
        
    def add_document(self, json_data: Dict[str, Any]):
        """새 JSON 문서 추가"""
        if "sections" not in json_data:
            print("❌ sections 필드가 없습니다.")
            return
            
        self.documents = [json_data]
        vehicle_name = self._extract_vehicle_name_from_data(json_data)
        sections_count = len(json_data.get("sections", []))
        
        print(f"📄 {vehicle_name} 매뉴얼 추가: {sections_count}개 섹션")
        
        # 섹션 데이터 준비
        self._prepare_sections_data(json_data)
    
    def _prepare_sections_data(self, json_data: Dict[str, Any]):
        """섹션 데이터를 검색 가능한 형태로 준비"""
        self.sections_data = []
        
        for section in json_data.get("sections", []):
            section_data = {
                "source": json_data.get("file_name", "unknown"),
                "section_number": section.get("section_number", ""),
                "title": section.get("title", ""),
                "page_range": section.get("page_range", ""),
                "content": section.get("content", ""),
                "keywords": section.get("keywords", []),
                "subsections": section.get("subsections", [])
            }
            self.sections_data.append(section_data)
        
        print(f"✅ {len(self.sections_data)}개 섹션 데이터 준비 완료")
    
    def search_sections(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """키워드 기반 섹션 검색"""
        
        if not self.documents or not self.sections_data:
            print("⚠️ 로드된 문서나 섹션 데이터가 없습니다")
            return []
        
        vehicle_name = self._extract_vehicle_name_from_data(self.documents[0])
        print(f"🔍 {vehicle_name} 매뉴얼 키워드 검색 시작: '{query}'")
        
        search_results = []
        
        # 각 섹션에 대해 점수 계산
        for section_data in self.sections_data:
            scores = self._calculate_all_scores(query, section_data)
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
        
        print(f"📊 {vehicle_name} 검색 결과: {len(search_results)}개 섹션 (키워드 매칭)")
        for i, result in enumerate(search_results[:3]):
            print(f"  {i+1}. [{result['score']:.3f}] {result['title']} (페이지 {result['page_range']})")
        
        return search_results[:k]
    
    def _calculate_all_scores(self, query: str, section_data: Dict) -> Dict[str, float]:
        """모든 점수 계산"""
        return {
            "title": self._calculate_title_score(query, section_data["title"]),
            "keyword": self._calculate_keyword_score(query, section_data["keywords"]),
            "content": self._calculate_content_score(query, section_data["content"]),
            "bonus": self._calculate_bonus_score(query, section_data)
        }
    
    def _calculate_total_score(self, scores: Dict[str, float]) -> float:
        """종합 점수 계산"""
        return (scores["title"] * 0.4) + (scores["keyword"] * 0.3) + \
               (scores["content"] * 0.2) + (scores["bonus"] * 0.1)
    
    def _calculate_title_score(self, query: str, title: str) -> float:
        """제목 매칭 점수"""
        if not title:
            return 0
        
        query_words = set(self._tokenize(query))
        title_words = set(self._tokenize(title))
        
        # 완전 매칭
        exact_matches = len(query_words.intersection(title_words))
        
        # 부분 매칭
        partial_matches = 0
        for q_word in query_words:
            for t_word in title_words:
                if q_word in t_word or t_word in q_word:
                    partial_matches += 0.5
                    break
        
        total_matches = exact_matches + partial_matches
        return min(total_matches / max(len(query_words), 1), 1.0)
    
    def _calculate_keyword_score(self, query: str, keywords: List[str]) -> float:
        """키워드 매칭 점수"""
        if not keywords:
            return 0
        
        query_lower = query.lower()
        matches = 0
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in query_lower:
                matches += 1
            elif any(word in keyword_lower for word in self._tokenize(query)):
                matches += 0.5
        
        return min(matches / max(len(keywords), 1), 1.0)
    
    def _calculate_content_score(self, query: str, content: str) -> float:
        """콘텐츠 매칭 점수"""
        if not content:
            return 0
        
        content_lower = content.lower()
        query_words = self._tokenize(query)
        
        # 단어별 매칭 횟수 계산
        total_matches = 0
        for word in query_words:
            # 완전 매칭
            exact_count = content_lower.count(word.lower())
            total_matches += exact_count
            
            # 부분 매칭 (길이 3 이상인 단어만)
            if len(word) >= 3:
                partial_count = len(re.findall(rf'{re.escape(word.lower())}', content_lower))
                total_matches += partial_count * 0.5
        
        # 콘텐츠 길이로 정규화
        content_length = len(content)
        if content_length > 0:
            return min(total_matches / (content_length / 100), 1.0)
        
        return 0
    
    def _calculate_bonus_score(self, query: str, section: Dict) -> float:
        """보너스 점수"""
        content = section.get("content", "").lower()
        title = section.get("title", "").lower()
        query_lower = query.lower()
        bonus = 0
        
        # 방법, 절차 관련 보너스
        if any(word in query_lower for word in ["방법", "절차", "어떻게", "how"]):
            if any(word in content for word in ["방법", "절차", "단계", "하십시오", "순서"]):
                bonus += 0.3
        
        # 문제 해결 관련 보너스
        if any(word in query_lower for word in ["문제", "오류", "고장", "안됨", "작동"]):
            if any(word in content for word in ["점검", "확인", "교체", "정비", "수리"]):
                bonus += 0.2
        
        # 제목에 중요 키워드가 있는 경우
        if any(word in title for word in ["안전", "주의", "경고", "중요"]):
            bonus += 0.1
        
        return min(bonus, 1.0)
    
    def _tokenize(self, text: str) -> List[str]:
        """텍스트를 토큰으로 분리"""
        if not text:
            return []
        
        # 한글, 영문, 숫자만 추출
        tokens = re.findall(r'[가-힣a-zA-Z0-9]+', text.lower())
        
        # 길이 1인 토큰 제거 (단, 숫자는 유지)
        tokens = [token for token in tokens if len(token) > 1 or token.isdigit()]
        
        return tokens
    
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
            "total_sections": len(self.sections_data),
            "search_method": "keyword_matching"
        }