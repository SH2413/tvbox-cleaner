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
# 获取原始内容
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
# JSON解析
# =========================
def try_parse_json(raw):
    try:
        if raw and (raw.strip().startswith("{") or raw.strip().startswith("[")):
            return json.loads(raw)
    except:
        pass
    return None


# =========================
# 多仓展开（不扣分）
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
# 播放检测（只判断成功/失败）
# =========================
def check_play_url(url):
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True
        )

        if r.status_code < 400 and r.content:
            return 1

        return 0

    except:
        return 0


# =========================
# 播放评分（0~60 → 改为10个抽样）
# =========================
def play_score(urls):
    if not urls:
        return 0

    sample = random.sample(urls, min(10, len(urls)))  # ✔ 改这里：10个

    success = sum([check_play_url(u) for u in sample])

    return int((success / len(sample)) * 60)


# =========================
# 稳定性评分（0~40）
# =========================
def stability_score(urls):
    if not urls:
        return 0

    total = 0

    for _ in range(RETRY_COUNT):
        sample = random.sample(urls, min(3, len(urls)))
        success = sum([check_play_url(u) for u in sample])

        total += int((success / len(sample)) * 40)

    return int(total / RETRY_COUNT)


# =========================
# 单源评分
# =========================
def single_score(api_url):
    score = 0

    raw = fetch_raw(api_url)
    data = try_parse_json(raw)

    if raw:
        score += 30

    if data:
        score += 20

    urls = extract_sources(data) if data else []
    urls = [u for u in urls if u.startswith("http")]

    if urls:
        score += 10
        score += play_score(urls)
        score += stability_score(urls)

    return min(score, 100)


# =========================
# 多次评分
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
# 保存
# =========================
def save_group(name, data):
    os.makedirs("output", exist_ok=True)

    with open(f"output/{name}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join([d[0] for d in data]))

    with open(f"output/{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# 主流程（按新分级）
# =========================
def main():
    urls = list(set(load_sources()))
    print(f"检测源数量: {len(urls)}")

    stable = []
    normal = []
    weak = []

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = pool.map(multi_score, urls)

        for url, score in results:

            # ✔ 按你新规则
            if score >= 61:
                stable.append((url, score))

            elif score >= 31:
                normal.append((url, score))

            else:
                weak.append((url, score))

    print(f"稳定源: {len(stable)}")
    print(f"可用源: {len(normal)}")
    print(f"弱源: {len(weak)}")

    save_group("stable", stable)
    save_group("normal", normal)
    save_group("weak", weak)


if __name__ == "__main__":
    main()
