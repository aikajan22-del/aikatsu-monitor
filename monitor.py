import json
import os
import re
import sys
from pathlib import Path

import requests

URL = "https://dcd.aikatsu.com/encore/shoplist/list.php"
PARAMS = {"free": "港南台", "p": 1}
STORE = "モーリーファンタジー港南台店"
STATE = Path("state.json")


def fetch():
    """{'1': 'オンライン' or 'オフライン', '2': ...} を返す
    オフラインの台は「オフライン」と表示され、稼働中の台は
    「排出されるカード」などが表示される（オンラインという文字は出ない）。
    """
    r = requests.get(
        URL, params=PARAMS, headers={"User-Agent": "Mozilla/5.0"}, timeout=30
    )
    r.raise_for_status()
    text = re.sub(r"<[^>]+>", " ", r.text)
    text = re.sub(r"\s+", "", text)
    blocks = re.findall(r"(\d+)台目(.*?)(?=\d+台目|・|$)", text)
    result = {}
    for num, body in blocks:
        if not body:
            continue
        result[num] = "オフライン" if "オフライン" in body else "オンライン"
    if not result:
        i = text.find("台目")
        print("台目の周辺:", text[i - 20 : i + 120] if i >= 0 else "（見つからない）")
    return result


def notify(msg):
    url = os.environ["DISCORD_WEBHOOK_URL"]
    requests.post(url, json={"content": msg}, timeout=30).raise_for_status()


def main():
    current = fetch()
    if not current:
        print("オンライン/オフラインの表示が見つかりません（ページ構造が変わった？）")
        sys.exit(1)

    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    changed = False

    for num, status in current.items():
        old = state.get(num)
        if not isinstance(old, str):
            # 初回（または旧形式の記録）は基準を記録するだけ
            state[num] = status
            changed = True
            continue
        if old != status:
            mark = "🟢" if status == "オンライン" else "🔴"
            notify(
                f"{mark} {STORE} {num}台目が{old}から{status}になりました\n"
                f"{URL}?free=港南台&p=1"
            )
            state[num] = status
            changed = True

    if changed:
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
