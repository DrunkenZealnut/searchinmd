#!/usr/bin/env python3
"""Australia SafeWork Publications 일괄 다운로드 스크립트"""

import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.safeworkaustralia.gov.au"
LIST_URL = "https://www.safeworkaustralia.gov.au/resources-and-publications"
# 저장 위치. 공개 저장소에 로컬 경로를 박지 않도록 환경변수로 받는다.
#   export DOWNLOAD_ROOT="/path/to/안전보건공단"   # 한 번만 설정
# 미설정 시 저장소 안의 downloads/ 아래에 받는다(.gitignore 대상).
DOWNLOAD_ROOT = os.environ.get(
    "DOWNLOAD_ROOT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads"))
SAVE_DIR = os.path.join(DOWNLOAD_ROOT, "SafeWork_AU")
PROGRESS_FILE = os.path.join(SAVE_DIR, "_download_progress.json")
DELAY = 1.0
TOTAL_PAGES = 105  # 0~104
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
    """모든 페이지 순회하며 자료 수집"""
    articles = []

    print(f"[수집] SafeWork Australia 자료 목록 수집 시작 ({TOTAL_PAGES} 페이지)...")

    for page in range(TOTAL_PAGES):
        url = f"{LIST_URL}?page={page}"

        try:
            resp = session.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [오류] page={page} 요청 실패: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # /doc/ 링크 수집
        doc_links = soup.find_all("a", href=re.compile(r"^/doc/"))
        page_found = 0

        for link in doc_links:
            href = link.get("href", "")
            title = link.get_text(strip=True)

            if not title or len(title) < 3:
                continue

            doc_url = BASE_URL + href

            if not any(a["doc_url"] == doc_url for a in articles):
                articles.append({
                    "title": title,
                    "doc_url": doc_url,
                    "slug": href.replace("/doc/", ""),
                })
                page_found += 1

        print(f"  [수집] page={page}: {page_found}건 (누적: {len(articles)}건)")
        time.sleep(DELAY)

    print(f"[수집 완료] 총 {len(articles)}건")
    return articles


def download_articles(session, articles, progress):
    """각 문서 페이지에서 PDF 찾아 다운로드"""
    total = len(articles)
    downloaded_set = set(progress["downloaded"])
    new_downloads = 0
    new_failures = 0

    print(f"\n[다운로드] 총 {total}건 중 {len(downloaded_set)}건 완료됨, {total - len(downloaded_set)}건 남음")

    for i, article in enumerate(articles):
        key = article["slug"]

        if key in downloaded_set:
            continue

        title = article["title"]
        doc_url = article["doc_url"]

        try:
            # 문서 페이지에서 PDF 링크 찾기
            resp = session.get(doc_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                progress["failed"].append({"key": key, "title": title, "error": f"HTTP {resp.status_code}"})
                new_failures += 1
                print(f"  [{i+1}/{total}] 페이지 오류 ({resp.status_code}): {title[:50]}")
                time.sleep(DELAY)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            pdf_link = soup.find("a", href=re.compile(r"\.pdf", re.I))

            if not pdf_link:
                # PDF 없는 문서 (HTML만)
                progress["downloaded"].append(key)
                downloaded_set.add(key)
                print(f"  [{i+1}/{total}] PDF 없음 (스킵): {title[:50]}")
                time.sleep(DELAY)
                continue

            pdf_href = pdf_link.get("href", "")
            if pdf_href.startswith("/"):
                pdf_url = BASE_URL + pdf_href
            else:
                pdf_url = pdf_href

            # PDF 다운로드
            pdf_resp = session.get(pdf_url, headers=HEADERS, timeout=120, stream=True)
            pdf_resp.raise_for_status()

            filename = sanitize_filename(f"{title}.pdf")
            filepath = os.path.join(SAVE_DIR, filename)

            with open(filepath, "wb") as f:
                for chunk in pdf_resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = os.path.getsize(filepath)
            size_str = f"{file_size/1024/1024:.1f}MB" if file_size > 1024*1024 else f"{file_size/1024:.0f}KB"

            progress["downloaded"].append(key)
            downloaded_set.add(key)
            new_downloads += 1
            print(f"  [{i+1}/{total}] 완료 ({size_str}): {title[:60]}")

        except Exception as e:
            progress["failed"].append({"key": key, "title": title, "error": str(e)})
            new_failures += 1
            print(f"  [{i+1}/{total}] 실패: {title[:50]} - {e}")

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

    download_articles(session, articles, progress)
    print(f"\n[완료] 저장 위치: {SAVE_DIR}")


if __name__ == "__main__":
    main()
