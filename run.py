"""지표를 수집해 판단하고 data/history.json과 site/index.html을 갱신한다."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import analyze as a
import collect
import config as c
from render import render

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "data" / "history.json"
PAGE = ROOT / "site" / "index.html"
KST = timezone(timedelta(hours=9))


def write_atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def main():
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    errors, daily, prices = [], [], {}
    for key, spec in c.MARKETS.items():
        try:
            prices[key] = collect.fetch_price(spec["ticker"])
            daily.append(a.analyze_market(key, spec, prices[key]))
        except Exception as error:  # 한 지표가 실패해도 나머지는 표시한다
            errors.append(f"{spec['name']}: {error}")
    if "spx" not in prices:
        print("S&P 500 수집 실패: 페이지를 갱신하지 않습니다.", *errors, sep="\n", file=sys.stderr)
        return 1

    weekly = []
    for key, name in c.WEEKLY_TICKERS.items():
        if key in prices:
            weekly.append(a.analyze_weekly(name, prices[key]))

    monthly = []
    for key, spec in c.FRED_SERIES.items():
        try:
            monthly.append(a.analyze_fred(key, spec, collect.fetch_fred(spec["id"])))
        except Exception as error:
            errors.append(f"{spec['name']}: {error}")

    phase = a.build_phase(monthly, prices["spx"]["Close"])
    history = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {}
    previous = a.latest_before(history, today)
    snapshot = {
        "date": today, "generated_at": now.strftime("%Y-%m-%d %H:%M KST"), "daily": daily,
        "weekly": weekly, "monthly": monthly, "phase": phase, "errors": errors, "has_previous": previous is not None,
        "stance": a.stance_of(daily, weekly, phase), "advice": a.build_advice(daily, weekly, monthly, phase),
    }
    snapshot["changes"] = a.detect_changes(snapshot, previous)
    history[today] = snapshot
    write_atomic(HISTORY, json.dumps(history, ensure_ascii=False, indent=1))
    write_atomic(PAGE, render(snapshot))

    print(f"완료: {PAGE}")
    print(f"판단: {snapshot['stance']} / 국면: {phase['name']} / 실패 {len(errors)}건")
    for line in errors:
        print("실패:", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
