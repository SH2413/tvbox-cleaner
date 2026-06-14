import requests
import json
import random
from concurrent.futures import ThreadPoolExecutor
import os

TIMEOUT = 6
RETRY_COUNT = 3
MAX_DEPTH = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.google.com/"
}

# =========================
# 请求原始内容（关键修复点）
# =========================
def fetch_raw(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        return r.text
    except:
        return None


# =========================
# 入口识别（解决误杀核心）
# =========================
def is_entry_source(text):
    if not text:
        return False

    keywords = ["sites", "list", "vod", "class", "api", "tv", "json", "http"]

    if text.strip().startswith("{") or text.strip().startswith("["):
        return True

    text_lower = text.lower()

    for k in keywords:
        if k in text_lower:
            return True

    return False


# =========================
# JSON解析（失败不判死）
# =========================
def try_parse_json(raw):
    try:
        if raw and (raw.strip().startswith("{") or raw.strip().startswith("[")):
            return json.loads(raw)
    except:
        pass
    return None


# =========================
# 多仓递归解析（最多3层）
# =========================
def extract_sources(obj, depth=0):
    urls = []

    if depth >= MAX_DEPTH:
        return urls

    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and v.startswith("http"):
                urls.append(v)
            urls += extract_sources(v, depth + 1)

    elif isinstance(obj, list):
        for i in obj:
            urls += extract_sources(i, depth)

    elif isinstance(obj, str):
        if obj.startswith("http"):
            urls.append(obj)

    return urls


# =========================
# 播放检测（只加分，不判死）
# =========================
def check_play_url(url):
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True
        )

        if r.status_code >= 400:
            return 0

        if not r.content:
            return 0

        return 1

    except:
        return 0


# =========================
# 核心评分逻辑（修复版）
# =========================
def single_score(api_url):
    score = 0

    raw = fetch_raw(api_url)

    # 🟢 入口源：重点修复误杀饭太硬
    if is_entry_source(raw):
        score += 50

    data = try_parse_json(raw)

    # 🟡 能解析JSON
    if data:
        score += 20

        urls = extract_sources(data)

        if urls:
            score += 10

            urls = [u for u in urls if u.startswith("http")]

            if urls:
                sample = random.sample(urls, min(5, len(urls)))

                success = sum([check_play_url(u) for u in sample])

                # 播放能力加分（不决定生死）
                score += success * 5

                if success >= 2:
                    score += 10

    return min(score, 100)


# =========================
# 多次评分（稳定性）
# =========================
def multi_score(url):
    scores = []

    for _ in range(RETRY_COUNT):
        scores.append(single_score(url))

    return url, sum(scores) / len(scores)


# =========================
# 读取源
# =========================
def load_sources():
    with open("sources.txt", "r", encoding="utf-8") as f:
        return [i.strip() for i in f if i.strip()]


# =========================
# 保存结果
# =========================
def save_group(name, data):
    os.makedirs("output", exist_ok=True)

    with open(f"output/{name}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join([d[0] for d in data]))

    with open(f"output/{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# 主程序
# =========================
def main():
    urls = list(set(load_sources()))
    print(f"检测源数量: {len(urls)}")

    stable = []
    normal = []
    weak = []
    poor = []

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = pool.map(multi_score, urls)

        for url, score in results:

            if score >= 80:
                stable.append((url, score))

            elif score >= 50:
                normal.append((url, score))

            elif score >= 20:
                weak.append((url, score))

            else:
                poor.append((url, score))

    print(f"稳定源: {len(stable)}")
    print(f"一般源: {len(normal)}")
    print(f"弱源: {len(weak)}")
    print(f"废弃源: {len(poor)}")

    save_group("stable", stable)
    save_group("normal", normal)
    save_group("weak", weak)
    save_group("poor", poor)


if __name__ == "__main__":
    main()
