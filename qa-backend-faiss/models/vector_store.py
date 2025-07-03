import faiss
import numpy as np
import pickle
import os
from typing import List, Tuple, Dict, Any
from pathlib import Path

class FAISSVectorStore:
    def __init__(self, dimension: int, store_path: str = "./data/vectors/"):
        self.dimension = dimension
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        # FAISS 인덱스 초기화 (내적 유사도 사용)
        self.index = faiss.IndexFlatIP(dimension)
        
        # 메타데이터 저장용
        self.metadata: List[Dict[str, Any]] = []
        
        # 저장된 인덱스가 있으면 로드
        self.load_index()
    
    def add_vectors(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]):
        """벡터와 메타데이터 추가"""
        # L2 정규화 (코사인 유사도를 위해)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        
        self.index.add(vectors.astype('float32'))
        self.metadata.extend(metadata)
        
        # 자동 저장
        self.save_index()
    
    def search(self, query_vector: np.ndarray, k: int = 5) -> List[Tuple[float, Dict[str, Any]]]:
        """유사도 검색"""
        if self.index.ntotal == 0:
            return []
        
        # L2 정규화
        query_vector = query_vector / np.linalg.norm(query_vector, axis=1, keepdims=True)
        
        scores, indices = self.index.search(query_vector.astype('float32'), k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:  # 유효한 인덱스인 경우
                results.append((float(score), self.metadata[idx]))
        
        return results
    
    def save_index(self):
        """인덱스와 메타데이터 저장"""
        index_path = self.store_path / "faiss.index"
        metadata_path = self.store_path / "metadata.pkl"
        
        faiss.write_index(self.index, str(index_path))
        
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
    
    def load_index(self):
        """저장된 인덱스와 메타데이터 로드"""
        index_path = self.store_path / "faiss.index"
        metadata_path = self.store_path / "metadata.pkl"
        
        if index_path.exists() and metadata_path.exists():
            self.index = faiss.read_index(str(index_path))
            
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            
            print(f"✅ 기존 인덱스 로드 완료: {self.index.ntotal}개 벡터")
    
    def get_stats(self) -> Dict[str, Any]:
        """인덱스 통계 정보"""
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "metadata_count": len(self.metadata)
        }