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

        # Lazy Loading 상태 저장
        self.section_embeddings = None
        self.sections_data = []
        self.embeddings_cached = False
        self.current_vehicle = None

        if auto_load:
            self.load_all_documents()

    def add_document(self, json_data: Dict[str, Any]):
        self.documents = [json_data]
        vehicle_name = self._extract_vehicle_name_from_data(json_data)
        self._load_cache_for_vehicle(vehicle_name)

    def _load_cache_for_vehicle(self, vehicle_name: str):
        if self.current_vehicle == vehicle_name and self.embeddings_cached:
            return  # 이미 로드됨

        cache_file = self.data_path / f"{vehicle_name.replace(' ', '_')}_embeddings.pkl"
        if not cache_file.exists():
            raise FileNotFoundError(f"❌ 캐시 파일 없음: {cache_file}")

        with open(cache_file, 'rb') as f:
            cache_data = pickle.load(f)
            self.section_embeddings = cache_data['embeddings']
            self.sections_data = cache_data['sections_data']
            self.embeddings_cached = True
            self.current_vehicle = vehicle_name
        print(f"✅ {vehicle_name} 캐시 로드 완료 ({len(self.sections_data)}개 섹션)")

    def search_sections(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if not self.documents or not self.embeddings_cached:
            print("⚠️ 문서 또는 임베딩 미로드")
            return []

        vehicle_name = self._extract_vehicle_name_from_data(self.documents[0])
        self._load_cache_for_vehicle(vehicle_name)

        print(f"🔍 {vehicle_name} 매뉴얼 검색 시작: '{query}'")

        query_embedding = self.embedding_model.encode_query(query)
        query_norm = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
        similarities = np.dot(query_norm, self.section_embeddings.T)[0]

        results = []
        for i, section in enumerate(self.sections_data):
            scores = self._calculate_all_scores(query, section)
            scores["embedding"] = similarities[i]
            total_score = self._calculate_total_score(scores)

            if total_score > 0.05:
                results.append({
                    "score": total_score,
                    "source": section["source"],
                    "section_number": section.get("section_number", 0),
                    "title": section.get("title", ""),
                    "page_range": section.get("page_range", [0, 0]),
                    "content": section.get("content", ""),
                    "keywords": section.get("keywords", []),
                    "subsections": section.get("subsections", []),
                    "match_details": {
                        "title_score": round(scores["title"], 3),
                        "keyword_score": round(scores["keyword"], 3),
                        "content_score": round(scores["embedding"], 3),
                        "bonus_score": round(scores["bonus"], 3)
                    }
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:k]

    def _calculate_all_scores(self, query: str, section: Dict) -> Dict[str, float]:
        return {
            "title": self._calculate_title_score(query, section.get("title", "")),
            "keyword": self._calculate_keyword_score(query, section.get("keywords", [])),
            "content": 0.0,  # deprecated
            "bonus": self._calculate_bonus_score(query, section)
        }

    def _calculate_total_score(self, scores: Dict[str, float]) -> float:
        return (scores["title"] * 0.6 +
                scores["keyword"] * 0.15 +
                scores.get("embedding", 0) * 0.15 +
                scores["bonus"] * 0.1)

    def _calculate_title_score(self, query: str, title: str) -> float:
        return 0.0

    def _calculate_keyword_score(self, query: str, keywords: List[str]) -> float:
        return 0.0

    def _calculate_bonus_score(self, query: str, section: Dict) -> float:
        return 0.0

    def _extract_vehicle_name_from_data(self, json_data: Dict[str, Any]) -> str:
        file_name = json_data.get("file_name", "").lower()
        for name in ["그랜저", "싼타페", "쏘나타", "아반떼", "코나", "투싼", "펠리세이드"]:
            if name in file_name:
                return name
        return "unknown"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "documents_count": len(self.documents),
            "embeddings_cached": self.embeddings_cached,
            "cached_sections": len(self.sections_data) if self.embeddings_cached else 0
        }
