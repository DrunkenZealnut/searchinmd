#!/usr/bin/env python3
"""CDC/NIOSH Publications 일괄 다운로드 스크립트 (2000년 이후)"""

import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.cdc.gov"
LIST_URL = "https://www.cdc.gov/niosh/pubs/all_niosh_desc.html"
# 저장 위치. 공개 저장소에 로컬 경로를 박지 않도록 환경변수로 받는다.
#   export DOWNLOAD_ROOT="/path/to/안전보건공단"   # 한 번만 설정
# 미설정 시 저장소 안의 downloads/ 아래에 받는다(.gitignore 대상).
DOWNLOAD_ROOT = os.environ.get(
    "DOWNLOAD_ROOT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads"))
SAVE_DIR = os.path.join(DOWNLOAD_ROOT, "NIOSH_Publications")
PROGRESS_FILE = os.path.join(SAVE_DIR, "_download_progress.json")
DELAY = 0.8
MIN_YEAR = 2000
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


def collect_articles(session):
    """출판물 목록 페이지에서 2000년 이후 자료 수집"""
    articles = []

    print("[수집] NIOSH 출판물 목록 수집 시작...")

    resp = session.get(LIST_URL, headers=HEADERS, timeout=60)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # /niosh/docs/ 링크 수집
    doc_links = soup.find_all("a", href=re.compile(r"/niosh/docs/\d{4}-\d+"))

    print(f"  전체 문서 링크: {len(doc_links)}개")

    for link in doc_links:
        href = link.get("href", "")
        title = link.get_text(strip=True)

        if not title or len(title) < 5:
            continue

        # 연도 추출: /niosh/docs/YYYY-NNN/
        m = re.search(r"/niosh/docs/(\d{4})-(\d+)", href)
        if not m:
            continue

        year = int(m.group(1))
        doc_num = f"{m.group(1)}-{m.group(2)}"

        if year < MIN_YEAR:
            continue

        # PDF URL 구성
        pdf_url = f"{BASE_URL}/niosh/docs/{doc_num}/pdfs/{doc_num}.pdf"

        article = {
            "title": title,
            "year": year,
            "doc_num": doc_num,
            "pdf_url": pdf_url,
            "page_url": BASE_URL + href if href.startswith("/") else href,
        }

        if not any(a["doc_num"] == doc_num for a in articles):
            articles.append(article)

    # 연도별 정렬 (최신순)
    articles.sort(key=lambda x: x["year"], reverse=True)

    print(f"[수집 완료] 2000년 이후: {len(articles)}건")
    return articles


def download_articles(session, articles, progress):
    """PDF 다운로드"""
    total = len(articles)
    downloaded_set = set(progress["downloaded"])
    new_downloads = 0
    new_failures = 0

    print(f"\n[다운로드] 총 {total}건 중 {len(downloaded_set)}건 완료됨, {total - len(downloaded_set)}건 남음")

    for i, article in enumerate(articles):
        key = article["doc_num"]

        if key in downloaded_set:
            continue

        title = article["title"]
        year = article["year"]
        doc_num = article["doc_num"]
        pdf_url = article["pdf_url"]

        filename = sanitize_filename(f"[{year}] {doc_num} - {title}.pdf")
        filepath = os.path.join(SAVE_DIR, filename)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            progress["downloaded"].append(key)
            downloaded_set.add(key)
            continue

        try:
            resp = session.get(pdf_url, headers=HEADERS, timeout=120, stream=True)

            if resp.status_code == 404:
                # PDF URL이 다를 수 있음 - 문서 페이지에서 PDF 링크 찾기
                page_resp = session.get(article["page_url"], headers=HEADERS, timeout=15)
                if page_resp.status_code == 200:
                    page_soup = BeautifulSoup(page_resp.text, "html.parser")
                    pdf_link = page_soup.find("a", href=re.compile(r"\.pdf$", re.I))
                    if pdf_link:
                        alt_href = pdf_link.get("href", "")
                        if alt_href.startswith("/"):
                            alt_href = BASE_URL + alt_href
                        resp = session.get(alt_href, headers=HEADERS, timeout=120, stream=True)

            if resp.status_code != 200:
                progress["failed"].append({"key": key, "title": title, "error": f"HTTP {resp.status_code}"})
                new_failures += 1
                print(f"  [{i+1}/{total}] 실패 ({resp.status_code}): {doc_num}")
                time.sleep(DELAY)
                continue

            content_type = resp.headers.get("Content-Type", "")
            if "html" in content_type.lower() and "pdf" not in content_type.lower():
                progress["failed"].append({"key": key, "title": title, "error": "HTML returned"})
                new_failures += 1
                print(f"  [{i+1}/{total}] 스킵 (HTML): {doc_num}")
                time.sleep(DELAY)
                continue

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = os.path.getsize(filepath)
            size_str = f"{file_size/1024/1024:.1f}MB" if file_size > 1024*1024 else f"{file_size/1024:.0f}KB"

            progress["downloaded"].append(key)
            downloaded_set.add(key)
            new_downloads += 1
            print(f"  [{i+1}/{total}] 완료 ({size_str}): [{year}] {doc_num} - {title[:50]}")

        except Exception as e:
            progress["failed"].append({"key": key, "title": title, "error": str(e)})
            new_failures += 1
            print(f"  [{i+1}/{total}] 실패: {doc_num} - {e}")

        if (new_downloads + new_failures) % 20 == 0:
            save_progress(progress)

        time.sleep(DELAY)

    save_progress(progress)
    print(f"\n[다운로드 완료] 신규: {new_downloads}건, 실패: {new_failures}건")
    print(f"  전체: {len(progress['downloaded'])}건 / {total}건")


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    progress = load_progress()
    session = requests.Session()

    if progress.get("articles"):
        articles = progress["articles"]
        print(f"[재개] 이전 목록 {len(articles)}건 사용")
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
        y = a["year"]
        year_counts[y] = year_counts.get(y, 0) + 1
    print("\n[연도별 분포]")
    for y in sorted(year_counts.keys()):
        print(f"  {y}: {year_counts[y]}건")

    download_articles(session, articles, progress)
    print(f"\n[완료] 저장 위치: {SAVE_DIR}")


if __name__ == "__main__":
    main()
