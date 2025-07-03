import os
import re
from typing import Dict, Any

# 텍스트 포맷터 import 추가
from utils.text_formatter import format_manual_response

class AnswerGenerator:
    def __init__(self):
        self.openai_available = bool(os.getenv("OPENAI_API_KEY"))

    async def generate_answer(self, question: str, section_data: Dict[str, Any]) -> str:
        """섹션 데이터로 간결하고 정제된 답변 생성"""

        self._print_debug_info(question, section_data)

        if self.openai_available:
            raw_answer = await self._generate_openai_answer(question, section_data)
        else:
            raw_answer = self._generate_smart_summary_answer(question, section_data)

        # 포맷팅 적용
        formatted_answer = format_manual_response(
            raw_answer,
            section_data.get("title", ""),
            section_data.get("page_range")
        )

        return formatted_answer

    def _print_debug_info(self, question: str, section_data: Dict[str, Any]):
        """디버깅 정보 출력"""
        content_preview = section_data['content'][:200]
        full_content_length = len(section_data['content'])

        print(f"🤖 답변 생성 중 - 섹션: {section_data['title']}")
        print(f"   전체 내용 길이: {full_content_length}자")
        print(f"   내용 미리보기: {content_preview}...")

    async def _generate_openai_answer(self, question: str, section_data: Dict[str, Any]) -> str:
        """OpenAI를 사용한 단계별 구조화된 답변 생성"""

        # 내용 전처리 - 중복 제거
        cleaned_content = self._clean_content(section_data['content'])
        
        # 질문 의도 파악
        question_intent = self._analyze_question_intent(question)

        prompt = f"""
사용자가 "{question}"에 대해 질문했습니다.

질문 의도: {question_intent}

다음 매뉴얼 내용에서 단계별 절차를 찾아 구조화된 답변을 만들어주세요:

{cleaned_content[:1000]}

답변 규칙:
1. 실제 수행할 수 있는 단계들을 번호순으로 나열
2. 각 단계는 구체적이고 명확하게
3. 3-6단계 정도로 구성
4. 중요한 주의사항이 있으면 별도로 언급
5. 중복 표현 절대 금지

답변 형식:
1. 첫 번째 단계
2. 두 번째 단계
3. 세 번째 단계
...

답변:
"""

        try:
            import openai
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"OpenAI 답변 생성 오류: {e}")
            return self._generate_smart_summary_answer(question, section_data)

    def _generate_smart_summary_answer(self, question: str, section_data: Dict[str, Any]) -> str:
        """질문 맞춤형 스마트 요약 (모든 주제 대응)"""
        
        content = self._clean_content(section_data['content'])
        question_intent = self._analyze_question_intent(question)
        
        # 질문 의도에 따른 키워드 필터링 (확장)
        keyword_map = {
            "점검 방법": ["점검", "확인", "체크", "살펴", "검사", "측정"],
            "교체 방법": ["교체", "교환", "갈기", "바꾸기", "설치", "장착"],
            "관리 방법": ["관리", "유지", "보관", "청소", "정비", "손질"],
            "문제 해결": ["고장", "문제", "이상", "오류", "해결", "수리"],
            "실행 방법": ["방법", "절차", "단계", "과정", "순서"],
            "일반 정보": ["하십시오", "하세요", "주의", "경고", "권장"]
        }
        
        target_keywords = keyword_map.get(question_intent, keyword_map["일반 정보"])
        
        # 관련 문장만 추출
        sentences = content.split('.')
        relevant_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if (len(sentence) > 8 and 
                any(keyword in sentence for keyword in target_keywords) and
                not any(avoid in sentence for avoid in ['WL_', '정기 점검', '666', '667', '668', '669', '670', '671'])):
                relevant_sentences.append(sentence)
            
            if len(relevant_sentences) >= 5:  # 최대 5문장
                break
        
        # 폴백: 의미있는 문장들
        if not relevant_sentences:
            for sentence in sentences[:8]:
                sentence = sentence.strip()
                if len(sentence) > 15 and '하십시오' in sentence:
                    relevant_sentences.append(sentence)
                if len(relevant_sentences) >= 4:
                    break
        
        return '. '.join(relevant_sentences[:4]) + '.' if relevant_sentences else content[:200]

    def _analyze_question_intent(self, question: str) -> str:
        """질문 의도 분석"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['점검', '확인', '체크']):
            return "점검 방법"
        elif any(word in question_lower for word in ['교체', '교환', '갈기']):
            return "교체 방법"
        elif any(word in question_lower for word in ['관리', '유지', '보관']):
            return "관리 방법"
        elif any(word in question_lower for word in ['문제', '고장', '이상']):
            return "문제 해결"
        elif any(word in question_lower for word in ['방법', '어떻게', '절차']):
            return "실행 방법"
        else:
            return "일반 정보"

    def _clean_content(self, content: str) -> str:
        """내용 정리 - 강력한 중복 제거"""
        
        # 1. **단어** **단어** 패턴 제거
        content = re.sub(r'\*\*([^*]+)\*\*\s*\*\*\1\*\*', r'**\1**', content)
        
        # 2. 연속된 같은 단어 제거 (배터리 배터리 -> 배터리)
        content = re.sub(r'(\b[가-힣]+)\s+\1', r'\1', content)
        
        # 3. 의미없는 코드 제거
        content = re.sub(r'(WL_\w+)', '', content)
        content = re.sub(r'(정기 점검\s*\d+)', '', content)
        content = re.sub(r'(2C_\w+)', '', content)
        
        # 4. 중복 문장 제거
        sentences = content.split('.')
        seen = set()
        unique_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            normalized = re.sub(r'\s+', ' ', sentence.lower())
            
            if normalized and len(normalized) > 10 and normalized not in seen:
                seen.add(normalized)
                unique_sentences.append(sentence)
        
        # 5. 불필요한 공백 정리
        cleaned = '. '.join(unique_sentences)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()

    def _extract_question_keywords(self, question: str) -> list:
        """질문에서 핵심 키워드 추출"""
        
        # 질문 타입별 키워드 매핑
        keyword_mapping = {
            "점검": ["점검", "확인", "체크", "관리"],
            "교체": ["교체", "교환", "갈기", "바꾸기"],
            "방법": ["방법", "절차", "과정", "어떻게"],
            "주의": ["주의", "경고", "안전", "위험"],
            "관리": ["관리", "유지", "보관", "정비"]
        }
        
        keywords = []
        question_lower = question.lower()
        
        for key, synonyms in keyword_mapping.items():
            if any(syn in question_lower for syn in synonyms):
                keywords.extend(synonyms)
        
        # 질문에서 직접 추출
        words = re.findall(r'[가-힣]{2,}', question)
        keywords.extend(words)
        
        return list(set(keywords))

    def _extract_relevant_sentences(self, content: str, keywords: list) -> list:
        """키워드와 관련성 높은 문장들 추출"""
        
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        relevant = []
        
        for sentence in sentences:
            score = 0
            sentence_lower = sentence.lower()
            
            # 키워드 매칭 점수
            for keyword in keywords:
                if keyword in sentence_lower:
                    score += 2
            
            # 실용적 표현 보너스
            practical_words = ["하십시오", "하세요", "방법", "절차", "주의", "경고", "확인"]
            for word in practical_words:
                if word in sentence:
                    score += 1
            
            # 길이 제한 (너무 길거나 짧은 문장 제외)
            if 10 <= len(sentence) <= 100 and score > 0:
                relevant.append((sentence, score))
        
        # 점수순 정렬
        relevant.sort(key=lambda x: x[1], reverse=True)
        return [sent for sent, score in relevant[:10]]

    def _extract_key_points(self, sentences: list, keywords: list) -> list:
        """핵심 포인트 추출 및 정제"""
        
        key_points = []
        seen_content = set()
        
        for sentence in sentences:
            # 중복 제거
            normalized = re.sub(r'\s+', ' ', sentence.lower())
            if normalized in seen_content:
                continue
            seen_content.add(normalized)
            
            # 문장 정제
            clean_sentence = self._clean_sentence(sentence)
            
            if clean_sentence and len(clean_sentence) > 5:
                key_points.append(clean_sentence)
            
            if len(key_points) >= 5:  # 최대 5개
                break
        
        return key_points

    def _clean_sentence(self, sentence: str) -> str:
        """개별 문장 정제"""
        
        # 불필요한 기호 제거
        sentence = re.sub(r'[^\w\s가-힣.,()/-]', '', sentence)
        
        # 연속 공백 제거
        sentence = re.sub(r'\s+', ' ', sentence)
        
        # 앞뒤 공백 제거
        sentence = sentence.strip()
        
        # 문장 끝 정리
        if sentence and not sentence.endswith(('.', '요', '다', '오')):
            sentence += '.'
        
        return sentence