#!/usr/bin/env python3
"""Heritage Books の商品価格を取得し、しきい値を下回ったら通知フラグを立てる。

- 価格は Shopify の /products/<handle>.js エンドポイントから取得する（HTML を
  スクレイピングするよりテーマ変更に強い）。
- 同じ価格で毎日メールが飛ばないよう、通知済み価格を data/state.json に記録する。
- 実行ごとに data/price-log.csv へ1行追記する。これは値動きの記録を兼ねつつ、
  リポジトリに commit を発生させて schedule ワークフローの自動無効化
  （公開リポジトリは60日間 活動がないと停止）を防ぐ役割も持つ。
"""

import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PRODUCT_URL = os.environ.get(
    "PRODUCT_URL",
    "https://heritagebooks.org/products/theoretical-practical-theology-volume-5",
)
THRESHOLD_CENTS = int(os.environ.get("THRESHOLD_CENTS", "2800"))

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "data" / "state.json"
LOG_PATH = ROOT / "data" / "price-log.csv"

USER_AGENT = "Mozilla/5.0 (compatible; price-watch/1.0; +https://github.com/cannedcountry-star/theoretical-practical)"


def fetch_product(url):
    req = urllib.request.Request(url.rstrip("/") + ".js", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8"))


def money(cents):
    return "${:,.2f}".format(cents / 100)


def load_state():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def append_log(now, price_cents, available):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["checked_at_utc", "price_usd", "available"])
        w.writerow([now.strftime("%Y-%m-%dT%H:%M:%SZ"), "{:.2f}".format(price_cents / 100), available])


def emit(**outputs):
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        for k, v in outputs.items():
            print("{}={}".format(k, v))
        return
    with open(path, "a", encoding="utf-8") as f:
        for k, v in outputs.items():
            f.write("{}={}\n".format(k, v))


def main():
    try:
        product = fetch_product(PRODUCT_URL)
    except (urllib.error.URLError, ValueError, TimeoutError) as e:
        # 取得失敗はジョブを失敗させる。GitHub から失敗通知メールが届くので、
        # 「壊れたまま静かに監視が止まる」状態を避けられる。
        print("ERROR: 価格の取得に失敗しました: {}".format(e), file=sys.stderr)
        return 1

    price_cents = product["price"]
    available = bool(product.get("available"))
    now = datetime.now(timezone.utc)

    print("title     : {}".format(product.get("title")))
    print("price     : {} ({} cents)".format(money(price_cents), price_cents))
    print("threshold : {}".format(money(THRESHOLD_CENTS)))
    print("available : {}".format(available))

    append_log(now, price_cents, available)

    state = load_state()
    last_notified = state.get("last_notified_cents")

    below = price_cents < THRESHOLD_CENTS
    # 同じ価格を通知済みなら再通知しない。さらに下がった場合は改めて通知する。
    should_notify = below and last_notified != price_cents

    if should_notify:
        print("=> しきい値を下回りました。通知します。")
        state["last_notified_cents"] = price_cents
        state["last_notified_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif not below and last_notified is not None:
        # 値段が戻ったら通知済みフラグを解除し、次に下がったとき再び通知できるようにする。
        print("=> しきい値以上に戻りました。通知済みフラグを解除します。")
        state.pop("last_notified_cents", None)
        state.pop("last_notified_at", None)
    else:
        print("=> 通知なし。")

    state["last_checked_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    state["last_price_cents"] = price_cents
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    emit(
        dropped=str(should_notify).lower(),
        price=money(price_cents),
        threshold=money(THRESHOLD_CENTS),
        title=product.get("title", ""),
        url=PRODUCT_URL,
        available=str(available).lower(),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
