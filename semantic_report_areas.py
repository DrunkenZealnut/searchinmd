"""보고서의 NCS·교과서 4영역 연구상 분류를 한곳에서 관리한다.

영역은 공식 교과 분류가 아니라 이 연구의 비교 집계를 위한 분석 분류다.
특히 『반도체 인프라 일반』은 전기·공조·유틸리티·설비운영·안전을
다루므로 반도체장비 영역에 배정한다.
"""

from __future__ import annotations


AREA_ORDER = ("개발", "제조", "장비", "재료")
AREA_DISPLAY = {
    "개발": "반도체개발",
    "제조": "반도체제조",
    "장비": "반도체장비",
    "재료": "반도체재료",
}

NCS_GROUP_TO_AREA = {
    "반도체개발": "개발",
    "반도체제조": "제조",
    "반도체장비": "장비",
    "반도체재료": "재료",
}

TEXTBOOK_GROUP_TO_AREA = {
    "반도체 기초기술 1": "개발",
    "반도체 기초기술 2": "개발",
    "반도체 기초": "개발",
    "반도체 공정기초": "제조",
    "반도체 포토에칭": "제조",
    "반도체 박막확산": "제조",
    "반도체 조립검사": "제조",
    "반도체 장비 유지보수": "장비",
    "반도체 인프라 일반": "장비",
}

_TEXTBOOK_CLASSIFICATION_REASON = {                        # 제목 → 대응 근거. 영역은 여기서 다시 손으로 적지 않고 TEXTBOOK_GROUP_TO_AREA 에서 그대로 가져온다 —
    "반도체 기초기술 1": "반도체 기본 원리와 개발 기초",           # 두 자리에 같은 영역을 따로 적으면 대응표를 바꿀 때 한쪽만 고쳐 표·근거·집계가 서로 어긋날 수 있다 (ship 리뷰 — Codex 적대적)
    "반도체 기초기술 2": "반도체 기본 원리와 개발 기초",
    "반도체 기초": "반도체 기본 원리와 개발 기초",
    "반도체 공정기초": "웨이퍼 제조 공정",
    "반도체 포토에칭": "포토·식각 제조 공정",
    "반도체 박막확산": "박막·확산 제조 공정",
    "반도체 조립검사": "조립·검사 제조 공정",
    "반도체 장비 유지보수": "장비 운전·유지보수",
    "반도체 인프라 일반": "전기·공조·유틸리티·설비운영·안전",
}
TEXTBOOK_CLASSIFICATION_ROWS = tuple(
    (title, TEXTBOOK_GROUP_TO_AREA[title], reason) for title, reason in _TEXTBOOK_CLASSIFICATION_REASON.items()
)


def area_for(corpus: str, group: str) -> str:
    """말뭉치와 그룹명을 4영역으로 변환하며 미등록 값은 즉시 거부한다."""

    mappings = {"NCS": NCS_GROUP_TO_AREA, "교과서": TEXTBOOK_GROUP_TO_AREA}
    if corpus not in mappings:
        raise ValueError(f"알 수 없는 말뭉치: {corpus}")
    try:
        return mappings[corpus][group]
    except KeyError:
        raise ValueError(f"{corpus}의 미등록 4영역 그룹: {group}") from None
