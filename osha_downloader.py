#!/usr/bin/env python3
"""US OSHA Publications 일괄 다운로드 스크립트 (2020년 이후)"""

import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.osha.gov/publications/all"
SITE_BASE = "https://www.osha.gov"
# 저장 위치. 공개 저장소에 로컬 경로를 박지 않도록 환경변수로 받는다.
#   export DOWNLOAD_ROOT="/path/to/안전보건공단"   # 한 번만 설정
# 미설정 시 저장소 안의 downloads/ 아래에 받는다(.gitignore 대상).
DOWNLOAD_ROOT = os.environ.get(
    "DOWNLOAD_ROOT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads"))
SAVE_DIR = os.path.join(DOWNLOAD_ROOT, "OSHA_Publications")
PROGRESS_FILE = os.path.join(SAVE_DIR, "_download_progress.json")
DELAY = 1.0
TOTAL_PAGES = 26  # 0~25
MIN_YEAR = 2020
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"downloaded": [], "failed": [], "articles": []}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def sanitize_filename(name, max_len=200):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    if len(name) > max_len:
        name = name[:max_len]
    return name


def extract_year(text):
    """텍스트에서 연도 추출 (예: '- 2024)' 또는 '(2024)')"""
    # "- YYYY)" 패턴 우선
    m = re.search(r'-\s*(\d{4})\s*\)', text)
    if m:
        return int(m.group(1))
    # "(YYYY)" 패턴
    m = re.search(r'\((\d{4})\)', text)
    if m:
        return int(m.group(1))
    # 단독 4자리 연도
    m = re.search(r'\b(20[2-9]\d)\b', text)
    if m:
        return int(m.group(1))
    return None


def collect_articles(session):
    """모든 페이지를 순회하며 2020년 이후 자료 수집"""
    articles = []
    all_count = 0

    print(f"[수집] OSHA Publications 목록 수집 시작 (2020년 이후)...")

    for page in range(TOTAL_PAGES):
        url = f"{BASE_URL}?page={page}"

        try:
            resp = session.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [오류] page={page} 요청 실패: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # 메인 콘텐츠 영역에서 PDF 링크 찾기
        main = soup.find("main") or soup
        pdf_links = main.find_all("a", href=re.compile(r"/sites/default/files/publications/.*\.(pdf|PDF)", re.I))

        page_found = 0
        for link in pdf_links:
            href = link.get("href", "")
            if not href:
                continue

            # 전체 URL 구성
            if href.startswith("/"):
                download_url = SITE_BASE + href
            else:
                download_url = href

            # 링크 주변 텍스트에서 제목과 연도 추출
            parent = link.find_parent("div") or link.find_parent("li") or link.find_parent("td")
            context_text = ""
            title = ""

            if parent:
                context_text = parent.get_text(" ", strip=True)

            # 제목 찾기: 이전 h5 태그
            title_tag = link.find_previous("h5")
            if title_tag:
                title = title_tag.get_text(strip=True)

            if not title:
                if parent:
                    t = parent.find("strong") or parent.find("h4")
                    if t:
                        title = t.get_text(strip=True)

            if not title or title.lower() in ("pdf", "html", "epub", "mobi", ""):
                title = os.path.basename(href)

            # 연도 추출
            year = extract_year(context_text)

            if not year:
                year = extract_year(href)

            all_count += 1

            # 2020년 이후만 필터링
            if year and year >= MIN_YEAR:
                filename_from_url = os.path.basename(href)

                article = {
                    "title": title,
                    "year": year,
                    "url": download_url,
                    "filename": filename_from_url,
                }

                # 중복 체크 (같은 URL)
                if not any(a["url"] == download_url for a in articles):
                    articles.append(article)
                    page_found += 1

        print(f"  [수집] page={page}: PDF {len(pdf_links)}개 중 2020년 이후 {page_found}건 (누적: {len(articles)}건)")
        time.sleep(DELAY)

    print(f"[수집 완료] 전체 PDF {all_count}개 중 2020년 이후: {len(articles)}건")
    return articles


def download_articles(session, articles, progress):
    """수집된 PDF 다운로드"""
    total = len(articles)
    downloaded_set = set(progress["downloaded"])
    new_downloads = 0
    new_failures = 0

    print(f"\n[다운로드] 총 {total}건 중 {len(downloaded_set)}건 완료됨, {total - len(downloaded_set)}건 남음")

    for i, article in enumerate(articles):
        url = article["url"]
        key = article["filename"]

        if key in downloaded_set:
            continue

        title = article["title"]
        year = article["year"]
        original_filename = article["filename"]

        # 파일명: 제목_원본파일명.pdf
        ext = os.path.splitext(original_filename)[1] or ".pdf"
        if title and title != original_filename:
            filename = sanitize_filename(f"[{year}] {title} ({os.path.splitext(original_filename)[0]}){ext}")
        else:
            filename = sanitize_filename(f"[{year}] {original_filename}")

        filepath = os.path.join(SAVE_DIR, filename)

        # 이미 존재하면 스킵
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            progress["downloaded"].append(key)
            downloaded_set.add(key)
            print(f"  [{i+1}/{total}] 이미 존재: {filename}")
            continue

        try:
            resp = session.get(url, headers=HEADERS, timeout=120, stream=True)
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "")
            if "html" in content_type.lower() and "pdf" not in content_type.lower():
                # HTML 페이지가 반환된 경우 (파일 없음)
                progress["failed"].append({"key": key, "title": title, "error": "HTML returned instead of PDF"})
                new_failures += 1
                print(f"  [{i+1}/{total}] 스킵 (HTML): {title}")
                continue

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

        if (new_downloads + new_failures) % 10 == 0:
            save_progress(progress)

        time.sleep(DELAY)

    save_progress(progress)
    print(f"\n[다운로드 완료] 신규 다운로드: {new_downloads}건, 실패: {new_failures}건")
    print(f"  전체 완료: {len(progress['downloaded'])}건 / {total}건")

    if progress["failed"]:
        print(f"\n[실패 목록]")
        for f in progress["failed"][-10:]:
            print(f"  - {f['title']}: {f['error']}")


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    progress = load_progress()
    session = requests.Session()

    # 1단계: 자료 목록 수집
    if progress.get("articles"):
        articles = progress["articles"]
        print(f"[재개] 이전에 수집된 {len(articles)}건의 목록 사용")
    else:
        articles = collect_articles(session)
        progress["articles"] = articles
        save_progress(progress)

    if not articles:
        print("[오류] 수집된 자료가 없습니다.")
        return

    # 연도별 통계
    year_counts = {}
    for a in articles:
        y = a.get("year", "unknown")
        year_counts[y] = year_counts.get(y, 0) + 1
    print(f"\n[연도별 분포]")
    for y in sorted(year_counts.keys()):
        print(f"  {y}: {year_counts[y]}건")

    # 2단계: PDF 다운로드
    download_articles(session, articles, progress)

    print(f"\n[완료] 저장 위치: {SAVE_DIR}")


if __name__ == "__main__":
    main()
