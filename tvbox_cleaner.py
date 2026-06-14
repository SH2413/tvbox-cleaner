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
# 获取JSON
# =========================
def fetch_json(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

        if r.status_code != 200:
            return None

        text = r.text.strip()

        if text.startswith("{") or text.startswith("["):
            return r.json()

        return None

    except:
        return None


# =========================
# 多仓递归解析
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
# 播放检测（轻量）
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

        # m3u8 / ts / mp4加分
        if "m3u8" in url or "ts" in url or "mp4" in url:
            return 1

        return 1

    except:
        return 0


# =========================
# 单次评分（核心）
# =========================
def single_score(api_url):
    score = 0

    data = fetch_json(api_url)
    if not data:
        return 0

    score += 20  # 接口可访问

    urls = extract_sources(data)
    if not urls:
        return score

    score += 20  # 能解析播放结构

    urls = [u for u in urls if u.startswith("http")]

    if not urls:
        return score

    # 随机抽样（避免误杀）
    sample = random.sample(urls, min(5, len(urls)))

    success = 0

    for u in sample:
        success += check_play_url(u)

    # 播放成功加分
    score += success * 15  # 最多30分

    # 稳定性加分（轻量模拟）
    if success >= 2:
        score += 30
    elif success == 1:
        score += 15

    return min(score, 100)


# =========================
# 多次评分（稳定性）
# =========================
def multi_score(url):
    scores = []

    for _ in range(RETRY_COUNT):
        scores.append(single_score(url))

    final_score = sum(scores) / len(scores)

    return url, final_score


# =========================
# 读取源
# =========================
def load_sources():
    with open("sources.txt", "r", encoding="utf-8") as f:
        return [i.strip() for i in f if i.strip()]


# =========================
# 保存分类
# =========================
def save_group(name, data):
    os.makedirs("output", exist_ok=True)

    with open(f"output/{name}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join([d[0] for d in data]))

    with open(f"output/{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# 主程序（评分分级）
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
