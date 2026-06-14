import requests
import json
import random
from concurrent.futures import ThreadPoolExecutor
import os

TIMEOUT = 6
RETRY_COUNT = 3
MAX_DEPTH = 3  # 🔥最多递归3层


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
# 🔥 多仓递归解析（核心）
# =========================
def extract_sources(obj, depth=0):
    urls = []

    if depth >= MAX_DEPTH:
        return urls

    if isinstance(obj, dict):

        for k, v in obj.items():

            # 发现URL
            if isinstance(v, str) and v.startswith("http"):
                urls.append(v)

            # 继续递归
            urls += extract_sources(v, depth + 1)

    elif isinstance(obj, list):

        for i in obj:
            urls += extract_sources(i, depth)

    elif isinstance(obj, str):

        if obj.startswith("http"):
            urls.append(obj)

    return urls


# =========================
# 检测播放源
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
            return False

        if not r.content:
            return False

        return True

    except:
        return False


# =========================
# 单次检测
# =========================
def single_check(api_url):
    data = fetch_json(api_url)

    if not data:
        return False

    urls = extract_sources(data)

    if not urls:
        return False

    urls = [u for u in urls if u.startswith("http")]

    if not urls:
        return False

    # 随机抽样（避免误杀）
    sample = random.sample(urls, min(5, len(urls)))

    success = 0

    for u in sample:
        if check_play_url(u):
            success += 1

    return success >= 1


# =========================
# 多次检测
# =========================
def multi_check(url):
    success = 0

    for _ in range(RETRY_COUNT):
        if single_check(url):
            success += 1

    return url, success


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
        f.write("\n".join(data))

    with open(f"output/{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# 主程序
# =========================
def main():
    urls = list(set(load_sources()))
    print(f"检测源数量: {len(urls)}")

    stable, normal, dead = [], [], []

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = pool.map(multi_check, urls)

        for url, success in results:

            if success >= 2:
                stable.append(url)

            elif success == 1:
                normal.append(url)

            else:
                dead.append(url)

    print(f"稳定源: {len(stable)}")
    print(f"一般源: {len(normal)}")
    print(f"废弃源: {len(dead)}")

    save_group("stable", stable)
    save_group("normal", normal)
    save_group("dead", dead)


if __name__ == "__main__":
    main()
