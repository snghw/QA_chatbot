import re

def format_response(raw_text: str) -> str:
    """원본 텍스트를 가독성 있게 포맷팅 - 매뉴얼 내용 완전 보존"""
    
    # 0. 중복 단어 정리 (예: **엔진** **오일** -> **엔진 오일**)
    formatted = re.sub(r'\*\*([^*]+)\*\*\s*\*\*([^*]+)\*\*', r'**\1 \2**', raw_text)
    formatted = re.sub(r'\*\*([^*]+)\*\*\s*\*\*\1\*\*', r'**\1**', formatted)
    
    # 1. 단계별 번호 추출 및 구조화 (완전 보존 방식)
    formatted = extract_and_format_steps_complete(formatted)
    
    # 2. 페이지 참조 제거 (하단에 통합 표시)
    formatted = re.sub(r'\(페이지:\s*\d+\)', '', formatted)
    
    # 3. 중요 정보 강조 (주의사항 텍스트 정리 추가)
    formatted = re.sub(r'(F-L선|약 15분|정상 온도|냉각수 온도|규정량|레벨 게이지)', r'**\1**', formatted)
    
    # 주의사항 중복 방지를 위한 전처리
    formatted = re.sub(r'\*\*주의사항:\*\*\s*', '', formatted)
    
    # 4. 온도/시간 관련 강조
    formatted = re.sub(r'(약 \d+분|정상 온도|일정한 정상 온도)', r'**\1**', formatted)
    
    # 5. 주제별 제목 자동 생성
    formatted = add_topic_title(formatted)
    
    # 6. 중요 안내사항 하이라이트
    if '직영 하이테크센터' in formatted or '블루핸즈' in formatted:
        formatted = re.sub(
            r'(.*직영 하이테크센터.*블루핸즈.*)',
            r'\n\n## ⚠️ 중요 안내사항\n**\1**',
            formatted
        )
    
    # 7. 불필요한 공백 정리
    formatted = re.sub(r'\n\s*\n\s*\n', '\n\n', formatted)
    
    # 8. 중복 문장 제거 (완화된 버전)
    formatted = remove_duplicate_sentences_gentle(formatted)
    
    return formatted.strip()


def extract_and_format_steps_complete(text: str) -> str:
    """단계별 절차 추출 및 포맷팅 - 모든 내용 보존"""
    
    # 원본 텍스트를 문장 단위로 더 정확하게 분리
    sentences = re.split(r'\.(?=\s+[A-Z가-힣]|\s*$)', text)
    sentences = [s.strip() + ('.' if not s.strip().endswith('.') and s.strip() else '') for s in sentences if s.strip()]
    
    # 실제 절차적 문장만 선별 (더 엄격한 기준)
    procedure_patterns = [
        r'.*(?:주차하고|예열하여|끄고|뽑아|기다리|닦으|꽂은|확인하십시오|보충하십시오|닫고)',
        r'^\d+\.\s*.*(?:하십시오|하세요)$',
        r'.*(?:먼저|다음에|그 후|마지막으로).*(?:하십시오|하세요)'
    ]
    
    steps = []
    other_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 5:
            continue
            
        # 절차적 문장인지 확인
        is_procedure = any(re.match(pattern, sentence, re.IGNORECASE) for pattern in procedure_patterns)
        
        if is_procedure:
            # 문장 끝의 단독 숫자 제거
            cleaned_sentence = re.sub(r'\.\s*\d+\.\s*$', '.', sentence)
            steps.append(cleaned_sentence)
        else:
            other_sentences.append(sentence)
    
    # 단계별 형식 적용 (실제 절차가 3개 이상일 때만)
    if len(steps) >= 3:
        formatted_steps = []
        for i, step in enumerate(steps, 1):
            # 기존 번호 제거
            step = re.sub(r'^\d+\.\s*', '', step)
            step = re.sub(r'\s*\d+\.\s*$', '', step)
            step = step.strip()
            if not step.endswith('.'):
                step += '.'
            formatted_steps.append(f"**{i}.** {step}")
        
        result = '\n\n'.join(formatted_steps)
        
        # 주의사항과 추가 정보를 하나로 통합
        all_additional_info = []
        seen_info = set()
        
        for sentence in other_sentences:
            # 문장 끝 번호 제거
            cleaned = re.sub(r'\.\s*\d+\.\s*$', '.', sentence)
            
            # 중복 체크
            normalized = re.sub(r'\*\*.*?\*\*', '', cleaned).strip().lower()
            normalized = re.sub(r'주의사항:\s*', '', normalized)
            
            if normalized not in seen_info and len(cleaned) > 10:
                seen_info.add(normalized)
                all_additional_info.append(cleaned)
        
        # 주의사항과 일반 정보 분리
        important_info = []
        remaining_info = []
        
        for info in all_additional_info:
            if any(keyword in info for keyword in ['주의', '경고', '중요', '권장', '추천', '참고', '알아두기', '안전', '주의사항', '경고사항']):
                important_info.append(info)
            else:
                remaining_info.append(info)
        
        if important_info:
            result += '\n\n## ⚠️ 주의사항\n' + '\n'.join([f"• **{info}**" for info in important_info])
        
        if remaining_info:
            result += '\n\n## 📋 추가 정보\n' + '\n'.join([f"• {info}" for info in remaining_info])
        
        return result
    else:
        # 절차가 적으면 간결하게 정리
        all_sentences = steps + other_sentences
        
        main_info = []
        important_info = []
        seen_info = set()
        
        for sentence in all_sentences:
            # 문장 끝 번호 제거
            cleaned = re.sub(r'\.\s*\d+\.\s*$', '.', sentence)
            
            # 중복 체크
            normalized = re.sub(r'\*\*.*?\*\*', '', cleaned).strip().lower()
            normalized = re.sub(r'주의사항:\s*', '', normalized)
            
            if normalized not in seen_info and len(cleaned) > 10:
                seen_info.add(normalized)
                
                if any(keyword in cleaned for keyword in ['주의', '경고', '중요', '권장', '추천', '참고', '알아두기', '안전', '주의사항', '경고사항']):
                    important_info.append(cleaned)
                else:
                    main_info.append(cleaned)
        
        result = '\n\n'.join([f"• {info}" for info in main_info])
        
        if important_info:
            result += '\n\n## ⚠️ 주의사항\n' + '\n'.join([f"• **{info}**" for info in important_info])
                
        return result
    
    # 절차가 없으면 원본 그대로 반환
    return text


def add_topic_title(text: str) -> str:
    """주제와 행동에 따라 자동으로 제목 생성"""
    
    if text.startswith('#'):
        return text
    
    # 주제-행동-이모지 매핑
    topics = {
        '엔진 오일': '🔧', '엔진오일': '🔧', '배터리': '🔋', '타이어': '🚗',
        '브레이크': '🛑', '필터': '🌀', '냉각수': '❄️', '에어컨': '🌬️',
        '히터': '🔥', '전구': '💡', '퓨즈': '⚡', '벨트': '🔗', '와이퍼': '🌧️',
        '시동': '🔑', '변속기': '⚙️', '조향': '🎯', '서스펜션': '🏗️', '배기': '💨'
    }
    
    actions = {
        '점검 주기': '점검 주기', '정기 점검': '정기 점검 주기',
        '점검': '점검 방법', '확인': '확인 방법', '교체': '교체 방법',
        '교환': '교체 방법', '관리': '관리 방법', '정비': '정비 방법',
        '수리': '수리 방법', '조정': '조정 방법', '설정': '설정 방법',
        '사용': '사용 방법', '작동': '작동 방법', '청소': '청소 방법'
    }
    
    # 주제와 행동 찾기
    found_topic = None
    found_emoji = '📖'
    found_action = '사용 방법'
    
    for topic, emoji in topics.items():
        if topic in text:
            found_topic = topic
            found_emoji = emoji
            break
    
    for action, method in actions.items():
        if action in text:
            found_action = method
            break
    
    # 제목 생성
    if found_topic:
        title = f"# {found_emoji} {found_topic} {found_action}\n\n{text}"
    else:
        if any(word in text for word in ['점검', '확인']):
            title = f"# 🔍 점검 방법\n\n{text}"
        elif any(word in text for word in ['교체', '교환']):
            title = f"# 🔧 교체 방법\n\n{text}"
        elif any(word in text for word in ['관리', '정비']):
            title = f"# 🛠️ 관리 방법\n\n{text}"
        else:
            title = f"# 📖 사용 방법\n\n{text}"
    
    return title


def remove_duplicate_sentences_gentle(text: str) -> str:
    """중복 문장 제거 - 완화된 버전"""
    lines = text.split('\n')
    seen = set()
    result = []
    
    for line in lines:
        if line.startswith('#') or line.startswith('---') or line.startswith('>') or line.startswith('*') or line.startswith('**'):
            result.append(line)
            continue
        
        if not line.strip():
            result.append(line)
            continue
        
        normalized = line.strip()
        if normalized not in seen:
            seen.add(normalized)
            result.append(line)
    
    return '\n'.join(result)


def format_manual_response(raw_text: str, section_title: str = "", page_range: tuple = None) -> str:
    """매뉴얼 답변 전용 포맷팅 - 모든 내용 보존"""
    
    formatted = format_response(raw_text)
    
    if section_title and not formatted.startswith('#'):
        formatted = f"# 📖 {section_title}\n\n{formatted}"
    
    if page_range:
        formatted += f"\n\n---\n*참고: 사용자 매뉴얼 {page_range[0]}-{page_range[1]}페이지*"
    
    return formatted


def summarize_long_content(text: str) -> str:
    """긴 내용 요약 - 선택적으로 사용"""
    lines = text.split('\n')
    important_lines = []
    
    for line in lines:
        if (line.startswith('#') or 
            line.startswith('**') and '.**' in line or
            '💡' in line or '⚠️' in line or
            any(keyword in line for keyword in ['주의', '경고', '중요', '권장', '방법'])):
            important_lines.append(line)
    
    return '\n'.join(important_lines)