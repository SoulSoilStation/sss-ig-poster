#!/usr/bin/env python3
"""
SoulSoilStation ブログ → Instagram 自動投稿スクリプト
1日1回 GitHub Actions から呼び出して使用する

流れ:
  1. ブログから未投稿記事をランダムに1件選ぶ
  2. OGP画像をダウンロードしてJPEGに変換、リポジトリにコミット&プッシュ
     （Instagram Graph APIは画像をURL経由でのみ受け取れるため、
      raw.githubusercontent.com の公開URLを画像ホスティングとして利用する）
  3. Instagram Graph API でメディアコンテナ作成 → 公開
  4. 投稿ログを更新してコミット&プッシュ
"""

import io
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

BLOG_BASE = "https://soulsoilstation.co.jp/blog/"
REPO_ROOT = Path(__file__).parent
LOG_FILE = REPO_ROOT / "posted_log.json"
IMAGES_DIR = REPO_ROOT / "images"
GRAPH_API_VERSION = "v23.0"
# Instagram API with Instagram Login (2024年以降の新方式) は graph.instagram.com を使う。
# 旧方式の graph.facebook.com とは別物なので混在させない。
GRAPH_API_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"

# Instagram API 認証情報 (.env / GitHub Secrets から読み込み)
# アプリのダッシュボード「Instagram」→「APIセットアップ（Instagramログイン）」で
# 発行される長期アクセストークンとユーザーIDを使う（App ID/App Secretは不要）
IG_ACCESS_TOKEN = os.environ["IG_ACCESS_TOKEN"]
IG_USER_ID = os.environ["IG_USER_ID"]

# 画像を公開URLとして参照するためのGitHubリポジトリ情報
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")  # 例: SoulSoilStation/sss-ig-poster

# トークン自動延長をリポジトリSecretsへ書き戻すための任意設定
GH_PAT = os.environ.get("GH_PAT", "")


def load_log() -> dict:
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return {"posted": [], "history": []}


def save_log(log: dict):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def fetch_all_articles() -> list[dict]:
    """全ページから記事一覧を取得する"""
    articles = []
    page = 1
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (compatible; SoulSoilBot/1.0)"

    while True:
        url = BLOG_BASE if page == 1 else f"{BLOG_BASE}page/{page}/"
        resp = session.get(url, timeout=15)
        if resp.status_code == 404:
            break
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".p-postList__item")
        if not cards:
            break

        found = 0
        for card in cards:
            a_tag = card.select_one("a[href]")
            img_tag = card.select_one("img")
            if not a_tag:
                continue
            title_el = card.select_one(".p-postList__title, h2, h3")
            title = title_el.get_text(strip=True) if title_el else a_tag.get_text(strip=True)[:60]
            link = a_tag.get("href", "")
            img_src = img_tag.get("src", "") if img_tag else ""
            img_src = img_tag.get("data-src", img_src) if img_tag else img_src
            if link and title:
                articles.append({"title": title, "url": link, "img": img_src})
                found += 1

        if found == 0:
            break

        next_link = soup.select_one("a.next, .nav-next a, a[rel='next']")
        if not next_link:
            break
        page += 1

    return articles


def fetch_article_detail(url: str) -> dict:
    """記事ページからOGP画像・サマリーを取得する"""
    resp = requests.get(url, timeout=15,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; SoulSoilBot/1.0)"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    og_img = ""
    og_tag = soup.select_one('meta[property="og:image"]')
    if og_tag:
        og_img = og_tag.get("content", "")

    summary = ""
    og_desc = soup.select_one('meta[property="og:description"]')
    if og_desc:
        summary = og_desc.get("content", "").strip()
    if not summary:
        meta_desc = soup.select_one('meta[name="description"]')
        if meta_desc:
            summary = meta_desc.get("content", "").strip()
    if not summary:
        content = soup.select_one(".entry-content, .post-content, article")
        if content:
            for p in content.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 30:
                    summary = text[:120] + "…"
                    break

    return {"img_url": og_img, "summary": summary}


def slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1] or "post"


def prepare_instagram_image(img_url: str, slug: str) -> Optional[Path]:
    """
    OGP画像をダウンロードし、Instagram向けにJPEG変換・アスペクト比調整して
    images/ ディレクトリに保存する。Instagram Content Publishing APIは
    JPEG画像のみ・アスペクト比 4:5〜1.91:1 を要求するため。
    """
    if not img_url:
        return None
    try:
        resp = requests.get(img_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        im = Image.open(io.BytesIO(resp.content)).convert("RGB")

        w, h = im.size
        ratio = w / h
        if ratio > 1.91:  # 横長すぎる場合は左右をトリミング
            new_w = int(h * 1.91)
            offset = (w - new_w) // 2
            im = im.crop((offset, 0, offset + new_w, h))
        elif ratio < 0.8:  # 縦長すぎる場合は上下をトリミング
            new_h = int(w / 0.8)
            offset = (h - new_h) // 2
            im = im.crop((0, offset, w, offset + new_h))

        if im.width > 1440:  # 推奨最大幅にリサイズ
            new_height = int(im.height * (1440 / im.width))
            im = im.resize((1440, new_height), Image.LANCZOS)

        IMAGES_DIR.mkdir(exist_ok=True)
        out_path = IMAGES_DIR / f"{slug}.jpg"
        im.save(out_path, "JPEG", quality=88)
        return out_path
    except Exception as e:
        print(f"[WARN] 画像準備失敗: {e}")
        return None


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def commit_and_push(paths: list[str], message: str) -> Optional[str]:
    """指定ファイルをコミット&プッシュし、そのコミットSHAを返す（変更が無ければNone）"""
    git("add", *paths)
    staged = git("diff", "--cached", "--name-only")
    if not staged:
        return None
    git("-c", "user.name=soulsoil-bot", "-c", "user.email=soulsoil-bot@users.noreply.github.com",
        "commit", "-m", message)
    git("push")
    return git("rev-parse", "HEAD")


def raw_url_for(sha: str, relative_path: str) -> str:
    return f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/{sha}/{relative_path}"


def refresh_access_token() -> str:
    """
    長期アクセストークンの有効期限を60日に延長する。
    Instagram API with Instagram Login の ig_refresh_token は、
    発行/前回延長から24時間以上経過したトークンでないと延長できない
    （その場合は例外を投げるので、呼び出し側で現行トークンにフォールバックする）
    """
    resp = requests.get("https://graph.instagram.com/refresh_access_token", params={
        "grant_type": "ig_refresh_token",
        "access_token": IG_ACCESS_TOKEN,
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def persist_refreshed_token(new_token: str):
    """延長後トークンをGitHub Secretsに書き戻す（GH_PAT設定時のみ）"""
    if not GH_PAT or not GITHUB_REPOSITORY:
        print("[INFO] GH_PAT未設定のため、延長トークンの自動書き戻しはスキップします")
        return
    env = {**os.environ, "GH_TOKEN": GH_PAT}
    result = subprocess.run(
        ["gh", "secret", "set", "IG_ACCESS_TOKEN", "--repo", GITHUB_REPOSITORY, "--body", new_token],
        env=env, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"[WARN] トークンのSecrets書き戻し失敗: {result.stderr}")
    else:
        print("[OK] 延長済みアクセストークンをGitHub Secretsに書き戻しました")


def build_caption(title: str, summary: str, url: str) -> str:
    lines = [f"📝 {title}", ""]
    if summary:
        lines.append(summary)
        lines.append("")
    lines.append("▶️ 本編はプロフィールのリンクからもご覧いただけます")
    lines.append(f"🔗 {url}")
    return "\n".join(lines)


def wait_until_container_ready(container_id: str, token: str, timeout_sec: int = 60):
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resp = requests.get(f"{GRAPH_API_BASE}/{container_id}", params={
            "fields": "status_code",
            "access_token": token,
        }, timeout=15)
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError("メディアコンテナの処理でエラーが発生しました")
        time.sleep(3)
    raise RuntimeError("メディアコンテナの処理がタイムアウトしました")


def post_to_instagram(image_url: str, caption: str, token: str) -> str:
    create_resp = requests.post(f"{GRAPH_API_BASE}/{IG_USER_ID}/media", data={
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    }, timeout=30)
    if not create_resp.ok:
        print(f"[ERROR] メディアコンテナ作成に失敗: {create_resp.status_code} {create_resp.text}")
    create_resp.raise_for_status()
    container_id = create_resp.json()["id"]

    wait_until_container_ready(container_id, token)

    publish_resp = requests.post(f"{GRAPH_API_BASE}/{IG_USER_ID}/media_publish", data={
        "creation_id": container_id,
        "access_token": token,
    }, timeout=30)
    if not publish_resp.ok:
        print(f"[ERROR] メディア公開に失敗: {publish_resp.status_code} {publish_resp.text}")
    publish_resp.raise_for_status()
    return publish_resp.json()["id"]


def main():
    print(f"[{datetime.now().isoformat()}] 投稿処理開始")

    print("記事一覧を取得中...")
    articles = fetch_all_articles()
    if not articles:
        print("[ERROR] 記事が取得できませんでした")
        sys.exit(1)
    print(f"合計 {len(articles)} 記事を取得")

    log = load_log()
    posted_urls = set(log["posted"])

    unposted = [a for a in articles if a["url"] not in posted_urls]
    if not unposted:
        print("[INFO] 全記事投稿済み。ログをリセットして再開します。")
        log["posted"] = []
        posted_urls = set()
        unposted = articles

    article = random.choice(unposted)
    print(f"選択記事: {article['title']}")

    detail = fetch_article_detail(article["url"])
    img_url = detail["img_url"] or article["img"]
    summary = detail["summary"]

    slug = slug_from_url(article["url"])
    img_path = prepare_instagram_image(img_url, slug)
    if not img_path:
        print("[ERROR] 画像の準備に失敗したため投稿を中止します")
        sys.exit(1)

    image_sha = commit_and_push(
        [str(img_path.relative_to(REPO_ROOT))],
        f"chore: add IG image for {slug}",
    )
    if not image_sha:
        # 同名画像が既にリポジトリにある場合はHEADのSHAを使う
        image_sha = git("rev-parse", "HEAD")

    image_public_url = raw_url_for(image_sha, str(img_path.relative_to(REPO_ROOT)))
    print(f"画像公開URL: {image_public_url}")

    token = IG_ACCESS_TOKEN
    try:
        token = refresh_access_token()
        if token != IG_ACCESS_TOKEN:
            persist_refreshed_token(token)
    except Exception as e:
        print(f"[WARN] トークン延長に失敗、既存トークンで続行します: {e}")

    caption = build_caption(article["title"], summary, article["url"])

    media_id = post_to_instagram(image_public_url, caption, token)
    print(f"[OK] 投稿完了: media_id={media_id}")

    log["posted"].append(article["url"])
    log.setdefault("history", []).append({
        "timestamp": datetime.now().isoformat(),
        "media_id": str(media_id),
        "url": article["url"],
        "title": article["title"],
        "image_url": image_public_url,
    })
    save_log(log)
    commit_and_push(["posted_log.json"], f"chore: log IG post for {slug}")


if __name__ == "__main__":
    main()
