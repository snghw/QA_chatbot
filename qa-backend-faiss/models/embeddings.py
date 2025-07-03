from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
import os

class EmbeddingModel:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """텍스트 리스트를 벡터로 변환"""
        return self.model.encode(texts, convert_to_numpy=True)
    
    def encode_query(self, query: str) -> np.ndarray:
        """단일 쿼리를 벡터로 변환"""
        return self.model.encode([query], convert_to_numpy=True)