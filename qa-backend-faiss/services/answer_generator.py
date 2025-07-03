import os
import re
from typing import Dict, Any, List

class AnswerGenerator:
    def __init__(self):
        self.openai_available = bool(os.getenv("OPENAI_API_KEY"))

    async def generate_answer(self, question: str, section_data: Dict[str, Any]) -> str:
        cleaned_content = self._clean_content(section_data['content'])
        question_intent = self._analyze_question_intent(question)

        if self.openai_available:
            raw_answer = await self._generate_openai_answer(question, cleaned_content, question_intent, section_data)
        else:
            keywords = self._extract_question_keywords(question)
            relevant = self._extract_relevant_sentences(cleaned_content, keywords)
            raw_answer = self._fallback_answer(question_intent, relevant, section_data)

        return raw_answer

    async def _generate_openai_answer(self, question: str, cleaned_content: str, question_intent: str, section_data: Dict[str, Any]) -> str:
        prompt = f"""
당신은 현대자동차 매뉴얼을 친근하게 안내하는 AI 도우미입니다.

질문: "{question}"

매뉴얼 내용:
{cleaned_content[:1200]}

---

답변 작성 가이드:
• 마크다운 형식을 활용해서 구조화된 답변 작성
• 단계별 설명이 필요한 경우 번호 목록 (1. 2. 3.) 사용하고 각 단계를 완전하게 설명
• 필요한 모든 단계와 세부사항을 빠짐없이 포함
• 중요한 내용은 **굵게** 강조
• 주의사항은 ⚠️ **주의:** 형태로 명확히 구분
• 적절한 이모티콘(🔧 🚗 ✅ 등) 활용
• 친근하지만 정보 전달이 명확한 톤 유지
• 각 단계마다 구체적인 설명과 실용적인 팁 포함
• 준비물, 과정, 완료 후 확인사항까지 전체 프로세스 포함

답변은 800-1200자 정도로 충분히 상세하고 완전하게 작성해주세요. 
사용자가 실제로 따라할 수 있을 정도로 구체적이고 완전한 가이드를 제공해야 합니다.

답변:
"""

        try:
            import openai
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1200,
                temperature=0.3
            )

            answer = self._make_answer_friendly(response.choices[0].message.content.strip())
            return self._add_source_info(answer, section_data)

        except Exception as e:
            return f"앗, 답변을 생성하는 중에 문제가 생겼어요. 다시 한 번 질문해주시면 도와드릴게요! 😊"

    def _analyze_question_intent(self, question: str) -> str:
        intent_keywords = {
            "점검하고 싶으신가요?": ["점검", "확인", "체크"],
            "교체하려고 하시나요?": ["교체", "교환", "갈기", "바꾸기"],
            "관리 방법을 알고 싶으신가요?": ["관리", "유지", "보관", "정비"],
            "문제가 있으신가요?": ["문제", "고장", "이상", "작동 안함", "이슈"],
            "사용법을 알고 싶으신가요?": ["방법", "어떻게", "절차", "하는 법", "사용"]
        }

        tokens = set(re.findall(r'[가-힣]{2,}', question))
        for intent, keywords in intent_keywords.items():
            if tokens.intersection(keywords):
                return intent

        question_lower = question.lower()
        for intent, keywords in intent_keywords.items():
            if any(kw in question_lower for kw in keywords):
                return intent

        return "궁금하신 내용"

    def _extract_question_keywords(self, question: str) -> List[str]:
        keyword_mapping = {
            "점검": ["점검", "확인", "체크", "관리"],
            "교체": ["교체", "교환", "갈기", "바꾸기"],
            "방법": ["방법", "절차", "과정", "어떻게"],
            "주의": ["주의", "경고", "안전", "위험"],
            "관리": ["관리", "유지", "보관", "정비"]
        }

        question_tokens = re.findall(r'[가-힣]{2,}', question)
        question_set = set(question_tokens)

        extracted_keywords = []
        for key, synonyms in keyword_mapping.items():
            if question_set.intersection(synonyms):
                extracted_keywords.append(key)

        domain_terms = ["타이어", "엔진오일", "배터리", "브레이크", "에어컨", "와이퍼", "냉각수", "전구", "퓨즈"]
        domain_hits = question_set.intersection(domain_terms)

        return list(set(extracted_keywords) | domain_hits)

    def _extract_relevant_sentences(self, content: str, keywords: List[str]) -> List[str]:
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        relevant = []

        for sentence in sentences:
            score = sum(1 for kw in keywords if kw in sentence)
            if 10 <= len(sentence) <= 100 and score > 0:
                relevant.append((sentence, score))

        relevant.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in relevant[:5]]

    def _fallback_answer(self, intent: str, sentences: List[str], section_data: Dict[str, Any]) -> str:
        if not sentences:
            fallback = "🔍 **검색 결과**\n\n관련된 내용을 찾지 못했습니다. 다른 키워드로 다시 검색해보시거나, 질문을 더 구체적으로 해주세요."
            return self._add_source_info(fallback, section_data)

        result = "🔍 **매뉴얼 검색 결과**\n\n"
        
        intent_info = {
            "점검하고 싶으신가요?": ("🔧", "점검 방법"),
            "교체하려고 하시나요?": ("🔄", "교체 방법"),
            "관리 방법을 알고 싶으신가요?": ("🛠️", "관리 방법"),
            "문제가 있으신가요?": ("⚠️", "문제 해결"),
            "사용법을 알고 싶으신가요?": ("📖", "사용 방법")
        }
        
        icon, title = intent_info.get(intent, ("📝", "관련 정보"))
        result += f"{icon} **{title}**\n\n"
        
        if len(sentences) == 1:
            result += f"**주요 내용:**\n{sentences[0]}\n\n"
        else:
            for i, sentence in enumerate(sentences[:8], 1):
                clean_sentence = sentence.strip()
                if len(clean_sentence) > 200:
                    clean_sentence = clean_sentence[:200]
                    if '.' in clean_sentence:
                        clean_sentence = clean_sentence.rsplit('.', 1)[0] + '.'
                    else:
                        clean_sentence += "..."
                result += f"{i}. {clean_sentence}\n"
        
        warning_sentences = [s for s in sentences if any(keyword in s for keyword in ['주의', '위험', '경고', '안전', '금지'])]
        if warning_sentences:
            result += f"\n⚠️ **주의사항**\n"
            for warning in warning_sentences[:3]:
                result += f"• {warning.strip()}\n"
        
        tip_sentences = [s for s in sentences if any(keyword in s for keyword in ['팁', '권장', '추천', '효과적', '좋은'])]
        if tip_sentences:
            result += f"\n💡 **유용한 팁**\n"
            for tip in tip_sentences[:2]:
                result += f"• {tip.strip()}\n"
        
        result += f"\n📞 **추가 도움**\n더 자세한 내용이 필요하시면 언제든 말씀해주세요!"
        
        return self._add_source_info(result, section_data)

    def _make_answer_friendly(self, text: str) -> str:
        friendly_replacements = {
            r'해야 합니다': '해주세요',
            r'하십시오': '해보세요',
            r'하시기 바랍니다': '하시면 됩니다',
            r'주의하십시오': '주의해주세요',
            r'확인하십시오': '확인해보세요',
            r'반드시': '꼭',
            r'필수적으로': '꼭'
        }
        
        result = text
        for pattern, replacement in friendly_replacements.items():
            result = re.sub(pattern, replacement, result)
        
        # 주의사항 강조 패턴 - 이미 강조된 것은 제외하고 처리
        warning_patterns = [
            (r'(?<!⚠️ \*\*)(주의[^.]*\.)', r'⚠️ **주의:** \1'),
            (r'(?<!⚠️ \*\*)(위험[^.]*\.)', r'⚠️ **위험:** \1'),
            (r'(?<!⚠️ \*\*)(경고[^.]*\.)', r'⚠️ **경고:** \1'),
            (r'(?<!🛡️ \*\*)(안전[^.]*\.)', r'🛡️ **안전:** \1'),
            (r'(?<!🚫 \*\*)(금지[^.]*\.)', r'🚫 **금지:** \1')
        ]
        
        for pattern, replacement in warning_patterns:
            result = re.sub(pattern, replacement, result)
        
        # 중복된 경고 표시 정리
        cleanup_patterns = [
            (r'⚠️ \*\*주의:\*\* ⚠️ \*\*주의:\*\*', r'⚠️ **주의:**'),
            (r'⚠️ \*\*위험:\*\* ⚠️ \*\*위험:\*\*', r'⚠️ **위험:**'),
            (r'⚠️ \*\*경고:\*\* ⚠️ \*\*경고:\*\*', r'⚠️ **경고:**'),
            (r'🛡️ \*\*안전:\*\* 🛡️ \*\*안전:\*\*', r'🛡️ **안전:**'),
            (r'🚫 \*\*금지:\*\* 🚫 \*\*금지:\*\*', r'🚫 **금지:**'),
            # 추가 중복 패턴들
            (r'⚠️ \*\*⚠️ \*\*주의: 주의:\*\*', r'⚠️ **주의:**'),
            (r'⚠️ \*\*⚠️ \*\*경고: 경고:\*\*', r'⚠️ **경고:**'),
            (r'⚠️ \*\*⚠️ \*\*위험: 위험:\*\*', r'⚠️ **위험:**')
        ]
        
        for pattern, replacement in cleanup_patterns:
            result = re.sub(pattern, replacement, result)
        
        important_keywords = [
            r'(적정\s*공기압)', r'(엔진\s*오일)', r'(브레이크\s*패드)', 
            r'(배터리)', r'(타이어)', r'(냉각수)', r'(필터)',
            r'(점검\s*주기)', r'(교체\s*시기)', r'(정기\s*점검)',
            r'(준비물)', r'(도구)', r'(작업)', r'(절차)',
            r'(드레인\s*볼트)', r'(오일\s*팬)', r'(토크)', r'(규정량)',
            r'(오일\s*레벨)', r'(딥스틱)', r'(점성도)', r'(등급)'
        ]
        
        for keyword in important_keywords:
            result = re.sub(keyword, r'**\1**', result, flags=re.IGNORECASE)
        
        if len(result) > 1500:
            sentences = result.split('.')
            if len(sentences) > 12:
                result = '. '.join(sentences[:12]) + '.'
        
        return result

    def _add_source_info(self, answer: str, section_data: Dict[str, Any]) -> str:
        # 기존 문구 제거
        answer = re.sub(r'\n\n💡 더 자세한 내용은[^\n]*', '', answer)
        answer = re.sub(r'\n💡 더 자세한 내용은[^\n]*', '', answer)
        
        # section_data에서 가능한 모든 페이지 관련 필드 확인
        manual_title = section_data.get('manual_title', section_data.get('title', '사용자 매뉴얼'))
        
        # page_range에서 페이지 정보 추출
        page_range = section_data.get('page_range', [])
        page = ''
        
        if page_range and isinstance(page_range, list) and len(page_range) > 0:
            start_page = page_range[0]
            if len(page_range) > 1:
                end_page = page_range[1]
                if start_page == end_page:
                    page = str(start_page)  # 단일 페이지
                else:
                    page = f"{start_page}-{end_page}"  # 페이지 범위
            else:
                page = str(start_page)
        
        # 다른 페이지 필드도 시도 (fallback)
        if not page:
            page = (section_data.get('page') or 
                    section_data.get('page_number') or 
                    section_data.get('page_num') or 
                    section_data.get('pg') or 
                    section_data.get('pages') or '')
        
        chapter = (section_data.get('chapter') or 
                  section_data.get('chapter_title') or 
                  section_data.get('section') or 
                  section_data.get('section_number') or '')
        
        section_title = (section_data.get('section_title') or 
                        section_data.get('title') or
                        section_data.get('heading') or 
                        section_data.get('subtitle') or '')
        
        source_info = "\n\n**참고:** " + str(manual_title)
        
        # 페이지 정보 처리
        if page:
            page_str = str(page).strip()
            if page_str and page_str != 'None' and page_str != '':
                # 숫자만 있는 경우
                if page_str.isdigit():
                    source_info += " " + page_str + "페이지"
                # 범위인 경우 (예: 1-5)
                elif '-' in page_str:
                    source_info += " " + page_str + "페이지"
                # 이미 '페이지'가 포함된 경우
                elif '페이지' in page_str or 'p' in page_str.lower():
                    source_info += " " + page_str
                # 기타 페이지 정보
                else:
                    source_info += " " + page_str + "페이지"
        # 페이지가 없으면 다른 정보라도 표시
        elif chapter:
            chapter_str = str(chapter).strip()
            if chapter_str and chapter_str != 'None':
                source_info += " (섹션 " + chapter_str + ")"
        elif section_title and section_title != manual_title:
            section_str = str(section_title).strip()
            if section_str and section_str != 'None':
                source_info += " (" + section_str + ")"
        
        source_info += "\n\n💡 더 자세한 내용은 공식 매뉴얼에서 확인하세요."
        
        return answer + source_info

    def _clean_content(self, content: str) -> str:
        content = re.sub(r'\*\*([^*]+)\*\*\s*\*\*\1\*\*', r'**\1**', content)
        content = re.sub(r'(\b[가-힣]+)\s+\1', r'\1', content)
        content = re.sub(r'(WL_\w+|정기 점검\s*\d+|2C_\w+)', '', content)

        sentences = content.split('.')
        seen = set()
        unique_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            normalized = re.sub(r'\s+', ' ', sentence.lower())
            if normalized and len(normalized) > 10 and normalized not in seen:
                seen.add(normalized)
                unique_sentences.append(sentence)

        return '. '.join(unique_sentences).strip()