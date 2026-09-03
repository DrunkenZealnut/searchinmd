#!/usr/bin/env python3
"""KOSHA 산업안전보건연구원 연구보고서 일괄 다운로드 스크립트"""

import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
from pathlib import Path

BASE_URL = "https://oshri.kosha.or.kr/oshri/publication/researchReportSearch.do"
# 저장 위치. 공개 저장소에 로컬 경로를 박지 않도록 환경변수로 받는다.
#   export DOWNLOAD_ROOT="/path/to/안전보건공단"   # 한 번만 설정
# 미설정 시 저장소 안의 downloads/ 아래에 받는다(.gitignore 대상).
DOWNLOAD_ROOT = os.environ.get(
    "DOWNLOAD_ROOT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads"))
SAVE_DIR = os.path.join(DOWNLOAD_ROOT, "연구보고서")
PROGRESS_FILE = os.path.join(SAVE_DIR, "_download_progress.json")
DELAY = 1.0  # 요청 간 딜레이 (초)
ARTICLE_LIMIT = 100  # 페이지당 항목 수
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": BASE_URL,
}


def load_progress():
    """이전 진행 상태 로드 (이어받기 지원)"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"downloaded": [], "failed": [], "articles": []}


def save_progress(progress):
    """진행 상태 저장"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def sanitize_filename(name, max_len=150):
    """파일명에 사용할 수 없는 문자 제거"""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    if len(name) > max_len:
        name = name[:max_len]
    return name


def collect_articles(session, start_year=2000, end_year=2026):
    """모든 페이지를 순회하며 보고서 목록 수집"""
    articles = []
    offset = 0

    print(f"[수집] {start_year}~{end_year}년 연구보고서 목록 수집 시작...")

    while True:
        params = {
            "mode": "list",
            "articleLimit": ARTICLE_LIMIT,
            "article.offset": offset,
            "srchBgnYr": start_year,
            "srchEndYr": end_year,
        }

        try:
            resp = session.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [오류] offset={offset} 페이지 요청 실패: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # 다운로드 링크 찾기: mode=download 패턴
        download_links = soup.find_all("a", href=re.compile(r"mode=download"))
        # 상세보기 링크 찾기: mode=view 패턴
        view_links = soup.find_all("a", href=re.compile(r"mode=view"))

        if not download_links and not view_links:
            # 결과가 없으면 종료
            print(f"  [완료] offset={offset}에서 더 이상 결과 없음")
            break

        # 다운로드 링크에서 articleNo, attachNo 추출
        page_articles = []
        for link in download_links:
            href = link.get("href", "")
            # articleNo, attachNo 추출
            article_match = re.search(r"articleNo=(\d+)", href)
            attach_match = re.search(r"attachNo=(\d+)", href)

            if article_match and attach_match:
                article_no = article_match.group(1)
                attach_no = attach_match.group(1)

                # 제목 찾기: 같은 articleNo를 가진 view 링크에서
                title = ""
                for vlink in view_links:
                    vhref = vlink.get("href", "")
                    if f"articleNo={article_no}" in vhref:
                        title = vlink.get_text(strip=True)
                        break

                if not title:
                    # 링크 주변 텍스트에서 제목 추출 시도
                    parent = link.find_parent("li") or link.find_parent("div")
                    if parent:
                        title_tag = parent.find("a", href=re.compile(r"mode=view"))
                        if title_tag:
                            title = title_tag.get_text(strip=True)

                if not title:
                    title = f"report_{article_no}"

                article = {
                    "articleNo": article_no,
                    "attachNo": attach_no,
                    "title": title,
                }

                # 중복 체크
                if not any(a["articleNo"] == article_no and a["attachNo"] == attach_no for a in articles):
                    page_articles.append(article)
                    articles.append(article)

        found = len(page_articles)
        print(f"  [수집] offset={offset}: {found}건 발견 (누적: {len(articles)}건)")

        if found == 0 and not download_links:
            break

        offset += ARTICLE_LIMIT
        time.sleep(DELAY)

    print(f"[수집 완료] 총 {len(articles)}건 발견")
    return articles


def download_articles(session, articles, progress):
    """수집된 보고서 PDF 다운로드"""
    total = len(articles)
    downloaded_set = set(progress["downloaded"])
    new_downloads = 0
    new_failures = 0

    print(f"\n[다운로드] 총 {total}건 중 {len(downloaded_set)}건 완료됨, {total - len(downloaded_set)}건 남음")

    for i, article in enumerate(articles):
        key = f"{article['articleNo']}_{article['attachNo']}"

        if key in downloaded_set:
            continue

        title = article["title"]
        article_no = article["articleNo"]
        attach_no = article["attachNo"]

        filename = sanitize_filename(f"{title}.pdf")
        filepath = os.path.join(SAVE_DIR, filename)

        # 파일이 이미 존재하면 스킵
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            progress["downloaded"].append(key)
            downloaded_set.add(key)
            print(f"  [{i+1}/{total}] 이미 존재: {filename}")
            continue

        download_url = f"{BASE_URL}?mode=download&articleNo={article_no}&attachNo={attach_no}"

        try:
            resp = session.get(download_url, headers=HEADERS, timeout=120, stream=True)
            resp.raise_for_status()

            # Content-Type 확인
            content_type = resp.headers.get("Content-Type", "")

            # Content-Disposition에서 파일명 추출 시도
            cd = resp.headers.get("Content-Disposition", "")
            if cd:
                fname_match = re.search(r"filename[*]?=['\"]?(?:UTF-8'')?(.+?)(?:['\"]|;|$)", cd)
                if fname_match:
                    original_name = requests.utils.unquote(fname_match.group(1).strip("'\""))
                    if original_name:
                        ext = os.path.splitext(original_name)[1] or ".pdf"
                        filename = sanitize_filename(f"{title}{ext}")
                        filepath = os.path.join(SAVE_DIR, filename)

            # 파일 저장
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = os.path.getsize(filepath)
            size_str = f"{file_size/1024/1024:.1f}MB" if file_size > 1024*1024 else f"{file_size/1024:.0f}KB"

            progress["downloaded"].append(key)
            downloaded_set.add(key)
            new_downloads += 1
            print(f"  [{i+1}/{total}] 완료 ({size_str}): {filename}")

        except Exception as e:
            progress["failed"].append({"key": key, "title": title, "error": str(e)})
            new_failures += 1
            print(f"  [{i+1}/{total}] 실패: {title} - {e}")

        # 진행 상태 주기적 저장 (10건마다)
        if (new_downloads + new_failures) % 10 == 0:
            save_progress(progress)

        time.sleep(DELAY)

    save_progress(progress)
    print(f"\n[다운로드 완료] 신규 다운로드: {new_downloads}건, 실패: {new_failures}건")
    print(f"  전체 완료: {len(progress['downloaded'])}건 / {total}건")

    if progress["failed"]:
        print(f"\n[실패 목록]")
        for f in progress["failed"]:
            print(f"  - {f['title']}: {f['error']}")


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    progress = load_progress()
    session = requests.Session()

    # 1단계: 보고서 목록 수집
    if progress.get("articles"):
        articles = progress["articles"]
        print(f"[재개] 이전에 수집된 {len(articles)}건의 목록 사용")
    else:
        articles = collect_articles(session, start_year=2000, end_year=2026)
        progress["articles"] = articles
        save_progress(progress)

    if not articles:
        print("[오류] 수집된 보고서가 없습니다.")
        return

    # 2단계: PDF 다운로드
    download_articles(session, articles, progress)

    print(f"\n[완료] 저장 위치: {SAVE_DIR}")


if __name__ == "__main__":
    main()
