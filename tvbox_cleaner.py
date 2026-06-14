import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor
import os

TIMEOUT = 5
RETRY_COUNT = 3
INTERVAL = 60


def single_check(url):
    try:
        r = requests.get(url, timeout=TIMEOUT)

        if r.status_code != 200:
            return False

        text = r.text.strip()

        if not text:
            return False

        if text.startswith("{") or text.startswith("["):
            return True

        if "http" in text or "#EXTM3U" in text:
            return True

        return False

    except:
        return False


def multi_check(url):
    success = 0

    for i in range(RETRY_COUNT):
        if single_check(url):
            success += 1

        if i < RETRY_COUNT - 1:
            time.sleep(INTERVAL)

    return url, success


def load_sources():
    with open("sources.txt", "r", encoding="utf-8") as f:
        return [i.strip() for i in f if i.strip()]


def save_group(name, data):
    os.makedirs("output", exist_ok=True)

    with open(f"output/{name}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(data))

    with open(f"output/{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
