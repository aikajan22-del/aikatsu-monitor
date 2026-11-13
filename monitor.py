import json
import os
import re
import sys
import time
from pathlib import Path

import requests

URL = "https://dcd.aikatsu.com/encore/shoplist/list.php"
PARAMS = {"free": "港南台", "p": 1}
STORE = "モーリーファンタジー港南台店"
STATE = Path("state.json")
SEC = {"秒": 1, "分": 60, "時間": 3600, "日": 86400}


def parse_age(s):
    """'3時間前' -> (経過秒, 表示の粗さ秒)。読めなければ None"""
    m = re.fullmatch(r"(\d+)(秒|分|時間|日)前", s)
    if m:
        unit = SEC[m.group(2)]
        return int(m.group(1)) * unit, max(unit, 60)
    if "今" in s or "未満" in s:
        return 0, 60
    return None


def fetch():
    r = requests.get(
        URL, params=PARAMS, headers={"User-Agent": "Mozilla/5.0"}, timeout=30
    )
    r.raise_for_status()
    text = re.sub(r"<[^>]+>", " ", r.text)
    text = re.sub(r"\s+", "", text)
    found = re.findall(
        r"最終更新[：:](\d+(?:秒|分|時間|日)前|たった今|今|1分未満)", text
    )
    if not found:
        i = text.find("最終更新")
        print("最終更新の周辺:", text[i : i + 80] if i >= 0 else "（見つからない）")
    return found


def notify(msg):
    url = os.environ["DISCORD_WEBHOOK_URL"]
    requests.post(url, json={"content": msg}, timeout=30).raise_for_status()


def main():
    raws = fetch()
    if not raws:
        print("最終更新の表示が見つかりません（ページ構造が変わった？）")
        sys.exit(1)

    now = time.time()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    changed = False

    for i, raw in enumerate(raws, 1):
        parsed = parse_age(raw)
        if parsed is None:
            print(f"{i}台目: 読み取れない表示 {raw!r}")
            continue
        age, gran = parsed
        est = now - age  # 推定の最終更新時刻
        key = str(i)
        old = state.get(key)
        if old is None:
            # 初回は基準を記録するだけ（通知なし）
            state[key] = {"est": est, "gran": gran}
            changed = True
            continue
        tol = max(old["gran"], gran) + 120
        if est - old["est"] > tol:
            notify(
                f"🎴 {STORE} {i}台目が更新されました（最終更新：{raw}）\n"
                f"{URL}?free=港南台&p=1"
            )
            state[key] = {"est": est, "gran": gran}
            changed = True

    if changed:
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
