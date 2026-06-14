import requests
import json
from concurrent.futures import ThreadPoolExecutor
import os

TIMEOUT = 5
RETRY_COUNT = 3


# -----------------------------
# 获取接口数据
# -----------------------------
def fetch_api(url):
    try:
        r = requests.get(url, timeout=TIMEOUT)

        if r.status_code != 200:
            return None

        text = r.text.strip()

        if not text:
            return None

        # JSON接口
        if text.startswith("{") or text.startswith("["):
            return r.json()

        return None

    except:
        return None


# -----------------------------
# 提取播放地址（兼容TVBox常见结构）
# -----------------------------
def extract_urls(data):
    urls = []

    try:
        if isinstance(data, dict):

            # 常见：list / data / vod
            for key in ["list", "data", "vod"]:
                if key in data and isinstance(data[key], list):
                    for item in data[key]:
                        url = item.get("vod_play_url") or item.get("url")
                        if url:
                            urls.append(url)

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    url = item.get("vod_play_url") or item.get("url")
                    if url:
                        urls.append(url)

    except:
        pass

    return urls


# -----------------------------
# 播放地址真实检测
# -----------------------------
def check_play_url(url):
    try:
        r = requests.get(url, timeout=TIMEOUT, stream=True)

        if r.status_code != 200:
            return False

        # 有些源返回空或html
        if not r.content:
            return False

        return True

    except:
        return False


# -----------------------------
# 单次完整检测
# -----------------------------
def single_check(url):
    data = fetch_api(url)

    if not data:
        return False

    play_urls = extract_urls(data)

    if not play_urls:
        return False

    # 只抽样检测前2个播放地址
    test_urls = play_urls[:2]

    success = 0

    for u in test_urls:
        if check_play_url(u):
            success += 1

    return success > 0


# -----------------------------
# 多次检测（核心规则）
# ≥2次成功才算可用
# -----------------------------
def multi_check(url):
    success = 0

    for _ in range(RETRY_COUNT):
        if single_check(url):
            success += 1

    return url, success


# -----------------------------
# 读取源
# -----------------------------
def load_sources():
    with open("sources.txt", "r", encoding="utf-8") as f:
        return [i.strip() for i in f if i.strip()]


# -----------------------------
# 保存结果
# -----------------------------
def save_group(name, data):
    os.makedirs("output", exist_ok=True)

    with open(f"output/{name}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(data))

    with open(f"output/{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -----------------------------
# 主程序
# -----------------------------
def main():
    urls = list(set(load_sources()))
    print(f"检测源数量: {len(urls)}")

    stable = []
    normal = []
    dead = []

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
