import json
import numpy as np
import os
from typing import List, Dict, Any
from pathlib import Path

class JSONSearchService:
    def __init__(self, embedding_model, auto_load: bool = False, data_path: str = "./data/processed/"):
        self.embedding_model = embedding_model
        self.data_path = Path(data_path)
        self.documents = []
        
        # 👈 핵심 변경: auto_load=False로 자동 로딩 비활성화
        if auto_load:
            self.load_all_documents()
    
    def load_all_documents(self):
        """모든 JSON 문서 로드 (기존 방식 - 사용하지 않음)"""
        json_files = list(self.data_path.glob("*.json"))
        print(f"📚 JSON 문서 로드 중: {len(json_files)}개 파일")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    if "sections" in json_data:
                        self.documents.append(json_data)
                        sections_count = len(json_data.get("sections", []))
                        print(f"  ✅ {json_file.name}: {sections_count}개 섹션 로드")
            except Exception as e:
                print(f"  ❌ {json_file.name} 로드 실패: {e}")
        
        total_sections = sum(len(doc.get("sections", [])) for doc in self.documents)
        print(f"📖 총 {total_sections}개 섹션 로드 완료")
    
    def add_document(self, json_data: Dict[str, Any]):
        """새 JSON 문서 추가 (차량별 단일 문서)"""
        if "sections" in json_data:
            # 👈 중요: 기존 문서를 대체 (차량별로 하나의 문서만 유지)
            self.documents = [json_data]
            sections_count = len(json_data.get("sections", []))
            vehicle_name = self._extract_vehicle_name_from_data(json_data)
            print(f"📄 {vehicle_name} 매뉴얼 추가: {sections_count}개 섹션")
    
    def _extract_vehicle_name_from_data(self, json_data: Dict[str, Any]) -> str:
        """JSON 데이터에서 차량명 추출"""
        file_name = json_data.get("file_name", "")
        file_name_lower = file_name.lower()
        
        # 그랜저 확인
        if "그랜저" in file_name or "granjer" in file_name_lower or "grandeur" in file_name_lower:
            if "hybrid" in file_name_lower or "하이브리드" in file_name:
                return "그랜저 hybrid"
            return "그랜저"
        
        # 싼타페 확인
        elif "싼타페" in file_name or "santafe" in file_name_lower:
            return "싼타페"
        
        # 쏘나타 확인
        elif "쏘나타" in file_name or "sonata" in file_name_lower:
            if "hybrid" in file_name_lower or "하이브리드" in file_name:
                return "쏘나타 hybrid"
            return "쏘나타"
        
        # 아반떼 확인
        elif "아반떼" in file_name or "avante" in file_name_lower or "elantra" in file_name_lower:
            return "아반떼"
        
        # 코나 확인
        elif "코나" in file_name or "kona" in file_name_lower:
            if "electric" in file_name_lower or "일렉트릭" in file_name or "ev" in file_name_lower:
                return "코나 electric"
            return "코나"
        
        # 투싼 확인
        elif "투싼" in file_name or "tucson" in file_name_lower:
            if "hybrid" in file_name_lower or "하이브리드" in file_name:
                return "투싼 hybrid"
            return "투싼"
        
        # 펠리세이드 확인 (팰리세이드도 포함)
        elif "펠리세이드" in file_name or "팰리세이드" in file_name or "palisade" in file_name_lower:
            if "hybrid" in file_name_lower or "하이브리드" in file_name:
                return "펠리세이드 hybrid"
            return "펠리세이드"
        
        return f"알 수 없는 차량 ({file_name})"
    
    def search_sections(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """JSON 섹션 기반 검색 (단일 차량 문서에서만)"""
        if not self.documents:
            print(f"⚠️ 로드된 문서가 없습니다")
            return []
        
        vehicle_name = self._extract_vehicle_name_from_data(self.documents[0])
        print(f"🔍 {vehicle_name} 매뉴얼 검색 시작: '{query}'")
        
        search_results = []
        
        # 👈 단일 문서(선택된 차량)에서만 검색
        doc = self.documents[0]
        filename = doc.get("file_name", "unknown.json")
        sections = doc.get("sections", [])
        
        for section in sections:
            scores = self._calculate_all_scores(query, section)
            total_score = self._calculate_total_score(scores)
            
            if total_score > 0.05:  # 임계값
                search_results.append({
                    "score": total_score,
                    "source": filename,
                    "section_number": section.get("section_number", 0),
                    "title": section.get("title", ""),
                    "page_range": section.get("page_range", [0, 0]),
                    "content": section.get("content", ""),
                    "keywords": section.get("keywords", []),
                    "subsections": section.get("subsections", []),
                    "match_details": {
                        "title_score": round(scores["title"], 3),
                        "keyword_score": round(scores["keyword"], 3),
                        "content_score": round(scores["content"], 3),
                        "bonus_score": round(scores["bonus"], 3)
                    }
                })
        
        # 점수순 정렬
        search_results.sort(key=lambda x: x["score"], reverse=True)
        
        print(f"📊 {vehicle_name} 검색 결과: {len(search_results)}개 섹션")
        for i, result in enumerate(search_results[:3]):
            print(f"  {i+1}. [{result['score']:.3f}] {result['title']} (페이지 {result['page_range']})")
        
        return search_results[:k]
    
    def _calculate_all_scores(self, query: str, section: Dict) -> Dict[str, float]:
        """모든 점수 계산"""
        return {
            "title": self._calculate_title_score(query, section.get("title", "")),
            "keyword": self._calculate_keyword_score(query, section.get("keywords", [])),
            "content": self._calculate_content_score(query, section.get("content", "")),
            "bonus": self._calculate_bonus_score(query, section)
        }
    
    def _calculate_total_score(self, scores: Dict[str, float]) -> float:
        """종합 점수 계산"""
        return (scores["title"] * 0.6) + (scores["keyword"] * 0.15) + \
               (scores["content"] * 0.15) + (scores["bonus"] * 0.1)
    
    def _calculate_title_score(self, query: str, title: str) -> float:
        """제목 매칭 점수"""
        if not title:
            return 0
            
        query_words = set(query.lower().replace('?', '').replace('!', '').split())
        title_words = set(title.lower().split())
        
        if not query_words:
            return 0
        
        # 1. 정확한 매칭
        exact_matches = len(query_words.intersection(title_words))
        exact_score = exact_matches * 1.0
        
        # 2. 부분 매칭
        partial_matches = 0
        for q_word in query_words:
            for t_word in title_words:
                if len(q_word) >= 2 and len(t_word) >= 2:
                    if q_word in t_word or t_word in q_word:
                        partial_matches += 0.6
        
        # 3. 핵심 키워드 매칭
        core_keywords = {
            "엔진": ["엔진", "engine", "모터"],
            "오일": ["오일", "oil", "윤활유", "윤활"],
            "타이어": ["타이어", "tire", "바퀴", "wheel"],
            "브레이크": ["브레이크", "brake", "제동"],
            "배터리": ["배터리", "battery", "전지"],
            "필터": ["필터", "filter", "여과기"],
            "벨트": ["벨트", "belt", "타이밍"],
            "퓨즈": ["퓨즈", "fuse", "휴즈"],
            "전구": ["전구", "lamp", "light", "전등"],
            "냉각수": ["냉각수", "냉각액", "쿨런트", "coolant"],
            "교체": ["교체", "교환", "갈기", "바꾸기", "replace", "change"],
            "점검": ["점검", "확인", "체크", "검사", "check", "inspect"],
            "정비": ["정비", "수리", "관리", "maintenance", "service"],
            "보충": ["보충", "추가", "충전", "refill", "add"],
            "방법": ["방법", "절차", "과정", "순서", "단계", "매뉴얼", "procedure", "how"],
            "고장": ["고장", "문제", "오류", "이상", "trouble", "problem", "fault"],
            "시동": ["시동", "시작", "start", "ignition"]
        }
        
        direct_matches = 0
        for q_word in query_words:
            for core_key, synonyms in core_keywords.items():
                if q_word in synonyms or q_word == core_key:
                    for t_word in title_words:
                        if t_word in synonyms or t_word == core_key:
                            direct_matches += 1.0
        
        # 4. 주제-작업 조합 매칭
        topic_action_combinations = {
            "엔진": ["교체", "교환", "점검", "확인", "정비", "수리", "오일", "윤활"],
            "오일": ["교체", "교환", "점검", "확인", "보충", "게이지", "레벨", "주입"],
            "타이어": ["교체", "교환", "점검", "확인", "공기압", "마모", "회전", "정렬"],
            "브레이크": ["점검", "확인", "교체", "패드", "디스크", "액", "오일", "정비"],
            "배터리": ["교체", "충전", "점검", "확인", "방전", "단자", "청소"],
            "필터": ["교체", "교환", "청소", "점검", "에어", "오일", "연료"],
            "벨트": ["교체", "교환", "점검", "확인", "장력", "타이밍"],
            "퓨즈": ["교체", "교환", "점검", "확인", "단선", "차단"],
            "전구": ["교체", "교환", "점검", "확인", "램프", "라이트"],
            "냉각수": ["교체", "보충", "점검", "확인", "온도", "레벨"],
            "시동": ["방법", "걸기", "끄기", "문제", "고장", "키", "버튼"]
        }
        
        combination_bonus = 0
        title_lower = title.lower()
        query_lower = query.lower()
        
        for topic, related_actions in topic_action_combinations.items():
            if topic in title_lower:
                matching_actions = sum(1 for action in related_actions if action in query_lower)
                if matching_actions > 0:
                    combination_bonus += min(matching_actions * 0.5, 2.0)
        
        # 5. 최종 점수 계산
        total_matches = exact_score + partial_matches + direct_matches + combination_bonus
        base_score = total_matches / max(len(query_words), 1)
        
        # 제목 품질 보너스
        if 2 <= len(title.split()) <= 4 and base_score > 0.5:
            base_score *= 1.2
        
        # 완전 일치 보너스
        if len(query_words.intersection(title_words)) >= max(len(query_words) - 1, 1):
            base_score *= 1.3
        
        return min(base_score, 2.5)
    
    def _calculate_keyword_score(self, query: str, keywords: List[str]) -> float:
        """키워드 매칭 점수"""
        if not keywords:
            return 0
        
        query_lower = query.lower()
        query_words = query_lower.split()
        matches = 0
        
        # 직접 키워드 매칭
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in query_lower:
                matches += 1.0
            elif any(word in keyword_lower or keyword_lower in word for word in query_words if len(word) >= 2):
                matches += 0.5
        
        # 동의어 기반 매칭
        synonym_dict = self._get_synonyms()
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for query_word in query_words:
                for syn_key, syn_values in synonym_dict.items():
                    if (keyword_lower == syn_key or keyword_lower in syn_values) and \
                       (query_word == syn_key or query_word in syn_values):
                        matches += 0.7
        
        return min(matches / 1.5, 1.0)
    
    def _calculate_content_score(self, query: str, content: str) -> float:
        """내용 유사도 점수"""
        try:
            if not content or len(content.strip()) < 20:
                return 0
            
            # 너무 긴 내용은 샘플링
            if len(content) > 1000:
                content_sample = content[:500] + content[-500:]
            else:
                content_sample = content
            
            query_vector = self.embedding_model.encode_query(query)
            content_vector = self.embedding_model.encode_texts([content_sample])
            
            # 코사인 유사도
            query_norm = query_vector / np.linalg.norm(query_vector, axis=1, keepdims=True)
            content_norm = content_vector / np.linalg.norm(content_vector, axis=1, keepdims=True)
            
            similarity = np.dot(query_norm, content_norm.T)[0][0]
            return max(float(similarity), 0)
            
        except Exception as e:
            print(f"내용 점수 계산 오류: {e}")
            return 0
    
    def _calculate_bonus_score(self, query: str, section: Dict) -> float:
        """특별 보너스 점수"""
        bonus = 0
        content = section.get("content", "").lower()
        title = section.get("title", "").lower()
        query_lower = query.lower()
        
        # 주제별 관련성 보너스
        topic_bonuses = {
            ("엔진", "오일"): ["교체", "교환", "방법", "절차", "점검"],
            ("타이어",): ["교체", "교환", "점검", "공기압", "마모"],
            ("브레이크",): ["점검", "확인", "교체", "패드", "액"],
            ("배터리",): ["교체", "충전", "점검", "확인", "방전"],
            ("시동",): ["방법", "걸기", "끄기", "문제", "고장"],
            ("정비", "수리"): ["방법", "절차", "점검", "교체"],
            ("필터",): ["교체", "교환", "청소", "점검"],
            ("냉각수", "쿨런트"): ["교체", "보충", "점검", "확인"],
            ("오일",): ["교체", "교환", "보충", "점검", "게이지"]
        }
        
        for title_keywords, action_keywords in topic_bonuses.items():
            if any(kw in title for kw in title_keywords):
                matching_actions = sum(1 for action in action_keywords if action in query_lower)
                if matching_actions > 0:
                    bonus += min(matching_actions * 0.15, 0.3)
        
        # 절차적 내용 보너스
        if any(word in query_lower for word in ["방법", "절차", "단계", "과정"]):
            import re
            steps = len(re.findall(r'\d+\.\s', content))
            if steps >= 3:
                bonus += 0.2
            elif steps >= 1:
                bonus += 0.1
        
        # 관련 키워드 밀도 보너스
        important_words = [
            "교체", "교환", "점검", "확인", "보충", "게이지", "주입구",
            "방법", "절차", "단계", "과정", "주의", "경고", "안전"
        ]
        word_count = sum(1 for word in important_words if word in content)
        bonus += min(word_count * 0.03, 0.15)
        
        # 제목 품질 보너스
        if 2 <= len(title.split()) <= 5:
            bonus += 0.1
        
        # 내용 길이 적정성 보너스
        content_length = len(section.get("content", ""))
        if 200 <= content_length <= 2000:
            bonus += 0.1
        elif content_length > 2000:
            bonus -= 0.05
        
        return min(bonus, 1.0)
    
    def _get_synonyms(self) -> Dict[str, List[str]]:
        """동의어 사전"""
        return {
            "엔진": ["엔진", "모터", "engine"],
            "오일": ["오일", "윤활유", "윤활", "oil", "lubricant"],
            "엔진오일": ["엔진오일", "엔진 오일", "모터오일", "윤활유"],
            "교체": ["교환", "갈기", "변경", "바꾸기", "수리", "replace", "change"],
            "점검": ["확인", "체크", "검사", "측정", "check", "inspect"],
            "정비": ["수리", "관리", "maintenance", "service"],
            "보충": ["추가", "충전", "refill", "add"],
            "방법": ["절차", "과정", "순서", "단계", "매뉴얼", "안내", "procedure"],
            "단계": ["절차", "과정", "순서", "step"],
            "타이어": ["타이어", "바퀴", "tire", "wheel"],
            "브레이크": ["브레이크", "제동", "brake"],
            "배터리": ["배터리", "전지", "battery"],
            "필터": ["필터", "여과기", "filter"],
            "벨트": ["벨트", "타이밍벨트", "belt"],
            "호스": ["호스", "파이프", "hose", "pipe"],
            "냉각수": ["냉각액", "쿨런트", "coolant", "antifreeze"],
            "브레이크액": ["브레이크오일", "브레이크액", "brake fluid"],
            "워셔액": ["세정액", "washer fluid"],
            "고장": ["문제", "오류", "이상", "trouble", "problem"],
            "경고": ["주의", "warning", "caution"],
            "안전": ["safety", "보안"],
            "시동": ["시작", "start", "ignition"],
            "정지": ["중지", "stop", "turn off"],
            "계기판": ["대시보드", "dashboard", "cluster"],
            "게이지": ["측정기", "gauge", "meter"],
            "표시등": ["램프", "light", "indicator"],
            "엔진룸": ["보닛", "hood", "engine bay"],
            "트렁크": ["적재함", "trunk", "cargo"],
            "실내": ["cabin", "interior"],
            "에어컨": ["냉방", "air conditioning", "A/C"],
            "히터": ["난방", "heating"],
            "와이퍼": ["와이셔", "wiper"],
            "연료": ["기름", "가솔린", "fuel", "gasoline"],
            "주유": ["급유", "fueling", "refueling"]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            "documents_count": len(self.documents),
            "total_sections": sum(len(doc.get("sections", [])) for doc in self.documents)
        }