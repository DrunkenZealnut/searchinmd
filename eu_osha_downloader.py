#!/usr/bin/env python3
"""EU-OSHA Publications 일괄 다운로드 스크립트 (2000년 이후)"""

import os, re, time, json, sys
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://osha.europa.eu"
# 저장 위치. 공개 저장소에 로컬 경로를 박지 않도록 환경변수로 받는다.
#   export DOWNLOAD_ROOT="/path/to/안전보건공단"   # 한 번만 설정
# 미설정 시 저장소 안의 downloads/ 아래에 받는다(.gitignore 대상).
DOWNLOAD_ROOT = os.environ.get(
    "DOWNLOAD_ROOT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads"))
SAVE_DIR = os.path.join(DOWNLOAD_ROOT, "EU-OSHA_Publications")
PROGRESS_FILE = os.path.join(SAVE_DIR, "_download_progress.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Connection": "close",
}
TOTAL_PAGES = 334
MIN_YEAR = 2000

# 즉시 출력
sys.stdout.reconfigure(line_buffering=True)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"downloaded": [], "failed": [], "articles": []}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def sanitize_filename(name, max_len=200):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:max_len]


def fetch(url, retries=3):
    for i in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return resp
        except Exception as e:
            if i == retries - 1:
                print(f"  [오류] {url[:60]}... : {e}", flush=True)
            time.sleep(3 * (i + 1))
    return None


def collect_articles():
    articles = []
    print(f"[수집] EU-OSHA 목록 수집 시작...", flush=True)

    for page in range(TOTAL_PAGES):
        url = f"{BASE_URL}/en/publications?search_api_language_1%5B0%5D=en&page={page}"
        resp = fetch(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.find_all("a", href=re.compile(r"^/en/publications/[a-z]"))
        seen = set()
        page_found = 0

        for link in links:
            href = link.get("href", "")
            title = link.get_text(strip=True)
            slug = href.replace("/en/publications/", "")

            if not title or title == "See more" or len(title) < 5 or slug in seen:
                continue
            seen.add(slug)

            if not any(a["slug"] == slug for a in articles):
                articles.append({"title": title, "slug": slug})
                page_found += 1

        print(f"  [수집] page={page}: {page_found}건 (누적: {len(articles)}건)", flush=True)
        time.sleep(2)

    print(f"[수집 완료] 총 {len(articles)}건", flush=True)
    return articles


def download_articles(articles, progress):
    total = len(articles)
    downloaded_set = set(progress["downloaded"])
    new_dl = 0
    new_fail = 0

    print(f"\n[다운로드] {total}건 중 {len(downloaded_set)}건 완료됨", flush=True)

    for i, art in enumerate(articles):
        slug = art["slug"]
        if slug in downloaded_set:
            continue

        title = art["title"]

        # 문서 페이지에서 PDF 찾기
        doc_url = f"{BASE_URL}/en/publications/{slug}"
        resp = fetch(doc_url)
        if not resp:
            progress["failed"].append({"key": slug, "error": "page fetch failed"})
            new_fail += 1
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # 날짜 추출
        year = None
        info = soup.find(class_="content-publication-info")
        if info:
            m = re.search(r"(\d{2})/(\d{2})/(\d{4})", info.get_text())
            if m:
                year = int(m.group(3))

        if year and year < MIN_YEAR:
            progress["downloaded"].append(slug)
            downloaded_set.add(slug)
            print(f"  [{i+1}/{total}] 스킵 ({year}년): {title[:50]}", flush=True)
            continue

        # PDF 링크
        pdf_links = soup.find_all("a", href=re.compile(r"/sites/default/files/.*\.pdf", re.I))
        if not pdf_links:
            progress["downloaded"].append(slug)
            downloaded_set.add(slug)
            print(f"  [{i+1}/{total}] PDF 없음: {title[:50]}", flush=True)
            continue

        # 영문 PDF 우선
        pdf_url = None
        for pl in pdf_links:
            h = pl.get("href", "")
            if "_EN" in h.upper() or pl.get_text(strip=True).lower() == "en":
                pdf_url = h
                break
        if not pdf_url:
            pdf_url = pdf_links[0].get("href", "")
        if pdf_url.startswith("/"):
            pdf_url = BASE_URL + pdf_url

        # 다운로드
        try:
            pdf_resp = requests.get(pdf_url, headers=HEADERS, timeout=120, stream=True)
            pdf_resp.raise_for_status()

            year_str = f"[{year}] " if year else ""
            filename = sanitize_filename(f"{year_str}{title}.pdf")
            filepath = os.path.join(SAVE_DIR, filename)

            with open(filepath, "wb") as f:
                for chunk in pdf_resp.iter_content(8192):
                    f.write(chunk)

            size = os.path.getsize(filepath)
            sz = f"{size/1024/1024:.1f}MB" if size > 1024*1024 else f"{size/1024:.0f}KB"

            progress["downloaded"].append(slug)
            downloaded_set.add(slug)
            new_dl += 1
            print(f"  [{i+1}/{total}] 완료 ({sz}): {year_str}{title[:50]}", flush=True)

        except Exception as e:
            progress["failed"].append({"key": slug, "error": str(e)})
            new_fail += 1
            print(f"  [{i+1}/{total}] 실패: {title[:50]} - {e}", flush=True)

        if (new_dl + new_fail) % 20 == 0:
            save_progress(progress)
        time.sleep(2)

    save_progress(progress)
    print(f"\n[다운로드 완료] 성공: {new_dl}건, 실패: {new_fail}건", flush=True)


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    progress = load_progress()

    if progress.get("articles"):
        articles = progress["articles"]
        print(f"[재개] 이전 목록 {len(articles)}건", flush=True)
    else:
        articles = collect_articles()
        progress["articles"] = articles
        save_progress(progress)

    if not articles:
        print("[오류] 수집된 자료 없음", flush=True)
        return

    download_articles(articles, progress)
    print(f"\n[완료] 저장: {SAVE_DIR}", flush=True)


if __name__ == "__main__":
    main()
