import re

def format_response(raw_text: str) -> str:
    """원본 텍스트를 가독성 있게 포맷팅 - 매뉴얼 내용 완전 보존"""

    # 중복 강조 제거
    formatted = re.sub(r'\*\*([^*]+)\*\*\s*\*\*\1\*\*', r'**\1**', raw_text)
    formatted = re.sub(r'\*\*([^*]+)\*\*\s*\*\*([^*]+)\*\*', r'**\1 \2**', formatted)

    # 절차적 문장 구조화
    formatted = extract_and_format_steps_complete(formatted)

    # 페이지 정보 제거
    formatted = re.sub(r'\(페이지:\s*\d+\)', '', formatted)

    # 강조할 키워드 정리
    emphasis_terms = ['F-L선', '약 15분', '정상 온도', '냉각수 온도', '규정량', '레벨 게이지']
    for term in emphasis_terms:
        formatted = formatted.replace(term, f'**{term}**')

    # 제목 생성
    formatted = add_topic_title(formatted)

    # 중요 안내사항 강조
    if '직영 하이테크센터' in formatted or '블루핸즈' in formatted:
        formatted = re.sub(
            r'(.*직영 하이테크센터.*블루핸즈.*)',
            r'\n\n## ⚠️ 중요 안내사항\n**\1**',
            formatted
        )

    # 줄바꿈 정리 및 중복 제거
    formatted = re.sub(r'\n\s*\n\s*\n', '\n\n', formatted)
    formatted = remove_duplicate_sentences_gentle(formatted)

    return formatted.strip()


def extract_and_format_steps_complete(text: str) -> str:
    """단계별 절차 추출 및 포맷팅 - 모든 내용 보존"""

    # 문장 단위 분리
    sentences = re.split(r'\.(?=\s+[A-Z가-힣]|\s*$)', text)
    sentences = [s.strip() + ('.' if not s.endswith('.') else '') for s in sentences if s.strip()]

    steps, others = [], []
    procedure_keywords = ['먼저', '다음', '그 후', '마지막으로', '이후', '그다음', '이어서']
    imperative_ending = ['십시오', '하세요']

    for sentence in sentences:
        if any(k in sentence for k in procedure_keywords) or any(sentence.endswith(k) for k in imperative_ending):
            steps.append(sentence)
        else:
            others.append(sentence)

    numbered_steps = [f"**{i+1}.** {s}" for i, s in enumerate(steps)]
    content = '\n\n'.join(numbered_steps)

    # 주의사항 및 추가 정보 분리
    important, additional = [], []
    for s in others:
        target = important if any(k in s for k in ['주의', '경고', '중요', '참고', '안전']) else additional
        if s not in steps:
            target.append(s)

    if important:
        content += '\n\n## ⚠️ 주의사항\n' + '\n'.join(f"• **{i}**" for i in important)
    if additional:
        content += '\n\n## 📋 추가 정보\n' + '\n'.join(f"• {i}" for i in additional)

    return content


def add_topic_title(text: str) -> str:
    if text.startswith('#'):
        return text

    topics = {
        '엔진오일': '🔧', '배터리': '🔋', '타이어': '🚗',
        '브레이크': '🛑', '필터': '🌀', '냉각수': '❄️', '에어컨': '🌬️',
        '히터': '🔥', '전구': '💡', '퓨즈': '⚡', '벨트': '🔗', '와이퍼': '🌧️',
        '시동': '🔑', '변속기': '⚙️', '조향': '🎯', '서스펜션': '🏗️', '배기': '💨'
    }

    actions = {
        '점검': '점검 방법', '확인': '확인 방법', '교체': '교체 방법',
        '교환': '교체 방법', '관리': '관리 방법', '정비': '정비 방법',
        '수리': '수리 방법', '조정': '조정 방법', '설정': '설정 방법',
        '사용': '사용 방법', '작동': '작동 방법', '청소': '청소 방법'
    }

    topic = next((t for t in topics if t in text), None)
    emoji = topics.get(topic, '📖')
    action = next((actions[a] for a in actions if a in text), '사용 방법')

    return f"# {emoji} {topic or ''} {action}".strip() + "\n\n" + text


def remove_duplicate_sentences_gentle(text: str) -> str:
    lines, seen, result = text.split('\n'), set(), []
    for line in lines:
        norm = line.strip().lower()
        if line.startswith('#') or norm not in seen:
            result.append(line)
            seen.add(norm)
    return '\n'.join(result)


def format_manual_response(raw_text: str, section_title: str = "", page_range: tuple = None) -> str:
    formatted = format_response(raw_text)
    if section_title and not formatted.startswith('#'):
        formatted = f"# 📖 {section_title}\n\n" + formatted
    if page_range:
        formatted += f"\n\n---\n*참고: 사용자 매뉴얼 {page_range[0]}-{page_range[1]}페이지*"
    return formatted


def summarize_long_content(text: str) -> str:
    lines = text.split('\n')
    return '\n'.join(line for line in lines if line.startswith('#') or '⚠️' in line or any(k in line for k in ['주의', '경고', '중요', '방법']))
