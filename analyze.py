"""지표 판정, 경기 국면 판단, 변화 감지, 조언 생성. 네트워크를 쓰지 않는 순수 함수만 둔다."""
import pandas as pd

import config as c

UP, FLAT, DOWN = 1, 0, -1
TREND_LABEL = {UP: "상승", FLAT: "횡보", DOWN: "하락"}


def pct(new, old):
    return (new / old - 1) * 100


def analyze_market(key, spec, prices):
    close = prices["Close"]
    item = {
        "id": key, "name": spec["name"], "unit": spec["unit"], "kind": spec["kind"],
        "value": round(float(close.iloc[-1]), 2), "asof": close.index[-1].strftime("%Y-%m-%d"),
        "chg1d": round(pct(close.iloc[-1], close.iloc[-2]), 2),
        "chg20d": round(pct(close.iloc[-1], close.iloc[-21]), 2),
        "status": "ok", "note": "",
    }
    if spec["kind"] == "rate":
        if item["value"] > c.RATE_WARN:
            item.update(status="warn", note=f"경고선 {c.RATE_WARN}% 초과")
        else:
            item["note"] = f"경고선 {c.RATE_WARN}% 이하"
    elif spec["kind"] == "oil":
        if item["value"] >= c.OIL_WARN:
            item.update(status="warn", note=f"경고선 {c.OIL_WARN}달러 이상")
        elif item["value"] >= c.OIL_WATCH:
            item.update(status="watch", note="90달러대: 지속되면 기업 마진 부담")
        else:
            item["note"] = "90달러 미만"
    elif spec["kind"] == "fx":
        if abs(item["chg20d"]) >= c.FX_MOVE_WATCH:
            direction = "강세" if item["chg20d"] > 0 else "약세"
            subject = "달러" if key == "dxy" else "달러 대비 원화 " + ("약세" if item["chg20d"] > 0 else "강세")
            item.update(status="watch", note=f"20거래일 {item['chg20d']:+.1f}%: " + (f"{subject} {direction}" if key == "dxy" else subject))
        else:
            item["note"] = "20거래일 변동 작음"
    elif spec["kind"] == "index":
        ma200 = close.rolling(200).mean().iloc[-1]
        drawdown = pct(close.iloc[-1], close.iloc[-252:].max())
        item.update(above_ma200=bool(close.iloc[-1] >= ma200), drawdown=round(float(drawdown), 2))
        position = "200일선 위" if item["above_ma200"] else "200일선 아래"
        item["note"] = f"{position}, 고점 대비 {drawdown:.1f}%"
        if drawdown <= c.DD_WARN:
            item["status"] = "warn"
        elif not item["above_ma200"]:
            item["status"] = "watch"
    return item


def analyze_weekly(name, prices):
    weekly = prices.resample("W-FRI").agg({"High": "max", "Low": "min", "Close": "last"}).dropna()
    low15, high15 = weekly["Low"].rolling(15).min(), weekly["High"].rolling(15).max()
    fast_k = 100 * (weekly["Close"] - low15) / (high15 - low15)
    slow_k = fast_k.rolling(5).mean()
    slow_d = slow_k.rolling(5).mean()
    low19, high19 = weekly["Low"].rolling(19).min(), weekly["High"].rolling(19).max()
    williams = -100 * (high19 - weekly["Close"]) / (high19 - low19)
    stdev = weekly["Close"].rolling(20).std().dropna()
    recent = stdev.iloc[-156:]
    std_pctl = float((recent <= recent.iloc[-1]).mean() * 100)
    k, wr = float(slow_k.iloc[-1]), float(williams.iloc[-1])
    if k <= c.OVERSOLD_K and wr <= c.OVERSOLD_WR:
        signal = "oversold"
    elif k >= c.OVERBOUGHT_K and wr >= c.OVERBOUGHT_WR:
        signal = "overbought"
    else:
        signal = "neutral"
    return {
        "name": name, "asof": prices.index[-1].strftime("%Y-%m-%d"), "slow_k": round(k, 1),
        "slow_d": round(float(slow_d.iloc[-1]), 1), "williams": round(wr, 1), "signal": signal,
        "std_pctl": round(std_pctl), "std_low": std_pctl <= c.STD_LOW_PCTL,
    }


def trend_of(series, band_pct=0.1):
    """3개월 평균과 12개월 평균을 비교해 방향을 낸다."""
    short, long_ = series.iloc[-3:].mean(), series.iloc[-12:].mean()
    gap = pct(short, long_)
    return UP if gap > band_pct else DOWN if gap < -band_pct else FLAT


def analyze_fred(key, spec, series):
    transform = spec["transform"]
    item = {
        "id": key, "name": spec["name"], "group": spec["group"], "core": spec["core"],
        "asof": series.index[-1].strftime("%Y-%m"), "unit": spec.get("unit", ""),
        "value": round(float(series.iloc[-1]), 2), "trend": None, "status": "ok", "note": "",
    }
    if transform == "trend":
        item["trend"] = trend_of(series)
    elif transform == "inverse":
        gap = series.iloc[-3:].mean() - series.iloc[-12:].mean()
        item["trend"] = DOWN if gap > 0.05 else UP if gap < -0.05 else FLAT
        item["note"] = "낮아질수록 긍정으로 판정"
    elif transform == "diffusion":
        average = series.iloc[-3:].mean()
        item["trend"] = UP if average > 0 and series.iloc[-1] >= series.iloc[-6:].mean() else DOWN if average < 0 else FLAT
        item["note"] = "0보다 크면 확장"
    elif transform == "quarterly":
        item["trend"] = UP if series.iloc[-1] >= series.iloc[-3:-1].mean() else DOWN
    elif transform == "yoy":
        yoy = (series / series.shift(12) - 1).dropna() * 100
        item.update(value=round(float(yoy.iloc[-1]), 2), unit="%", prior=round(float(yoy.iloc[-4]), 2))
        item["trend"] = UP if yoy.iloc[-1] > yoy.iloc[-4] + 0.1 else DOWN if yoy.iloc[-1] < yoy.iloc[-4] - 0.1 else FLAT
        if spec["group"] == "inflation" and yoy.iloc[-1] >= c.INFLATION_WARN:
            item.update(status="warn", note=f"{c.INFLATION_WARN}% 이상: 금리 부담")
    return item


def stock_signal(close):
    """선행 지표로서의 주가: 200일선 위이고 6개월 수익률이 플러스인지 본다."""
    above = close.iloc[-1] >= close.rolling(200).mean().iloc[-1]
    rising = close.iloc[-1] >= close.iloc[-126]
    return UP if above and rising else DOWN if not above and not rising else FLAT


def group_trend(values):
    known = [v for v in values if v is not None]
    if not known:
        return None
    total = sum(known)
    return UP if total > 0 else DOWN if total < 0 else FLAT


PHASES = {
    "recovery": ("회복", "적극적으로 담을 구간", "뉴스는 나빠도 주가와 선행 지표가 먼저 돌아서는 구간이다. 미국 대형 성장주를 우선한다."),
    "late_recovery": ("회복 후반", "보유하며 계속 모을 구간", "동행 지표까지 살아나고 후행 지표만 남은 구간이다. 신규 자금을 정해진 일정대로 넣는다."),
    "expansion": ("성장", "보유하며 일부 차익 실현", "모든 지표가 좋은 구간이다. 신흥국과 시클리컬이 유리하지만 끝으로 갈수록 과열을 조심한다."),
    "slowdown": ("둔화 진입", "신규 자금을 방어주로", "선행 지표가 꺾였는데 후행 지표가 좋아 뉴스는 긍정적인 가장 위험한 구간이다. 배당과 필수소비재 비중을 늘린다."),
    "deep_slowdown": ("둔화 심화", "방어 유지, 현금 확보", "선행과 동행이 함께 꺾인 구간이다. 통신, 제약, 유틸리티 등 방어 업종과 현금을 우선한다."),
    "recession": ("침체", "끝날 때쯤 분할 매수", "모든 지표가 내려가는 구간이다. 공포가 극에 달할 때 위험자산을 나눠 담는다."),
    "mixed": ("혼조", "기존 계획 유지", "지표 방향이 엇갈려 국면을 단정하기 어렵다. 다음 달 지표까지 확인한다."),
}


def classify_phase(leading, coincident, lagging):
    if None in (leading, coincident, lagging):
        return "mixed"
    if leading == UP:
        if coincident == UP:
            return "expansion" if lagging == UP else "late_recovery"
        return "recovery" if coincident == DOWN or lagging != UP else "mixed"
    if leading == DOWN:
        if coincident == DOWN:
            return "recession" if lagging == DOWN else "deep_slowdown"
        return "slowdown"
    return "mixed"


def build_phase(fred_items, spx_close):
    groups = {"leading": [stock_signal(spx_close)], "coincident": [], "lagging": []}
    for item in fred_items:
        if item["core"] and item["group"] in groups:
            groups[item["group"]].append(item["trend"])
    trends = {name: group_trend(values) for name, values in groups.items()}
    key = classify_phase(trends["leading"], trends["coincident"], trends["lagging"])
    name, action, detail = PHASES[key]
    return {
        "key": key, "name": name, "action": action, "detail": detail,
        "leading": trends["leading"], "coincident": trends["coincident"], "lagging": trends["lagging"],
        "stock_signal": groups["leading"][0],
    }


def build_advice(daily, weekly, fred_items, phase):
    by_id = {item["id"]: item for item in daily}
    advice = [{
        "title": f"경기 국면: {phase['name']}",
        "body": f"{phase['action']}. {phase['detail']}",
        "source": c.SOURCES["macro"], "level": "warn" if phase["key"] in ("slowdown", "deep_slowdown", "recession") else "ok",
    }]
    rate, oil = by_id.get("us10y"), by_id.get("wti")
    rate_warn = bool(rate and rate["status"] == "warn")
    oil_warn = bool(oil and oil["status"] == "warn")
    if rate_warn and oil_warn:
        advice.append({
            "title": "금리와 유가가 함께 경고선 위",
            "body": "시장이 흔들리기 쉬운 조합이다. 정해진 분할 매수 일정만 지키고 추가 매수는 미룬다.",
            "source": c.SOURCES["growth"], "level": "warn",
        })
    elif rate_warn:
        advice.append({
            "title": f"금리 부담 지속({rate['value']}%)",
            "body": "유가는 경고선 아래지만 금리가 높아 주가 상단이 눌리기 쉽다. 빚이 많은 기업보다 현금을 잘 버는 대형주와 매출 증가율이 좋은 기업을 우선한다.",
            "source": c.SOURCES["roe"], "level": "watch",
        })
    elif oil_warn:
        advice.append({
            "title": f"유가 부담({oil['value']}달러)",
            "body": "유가 상승은 물가와 금리로 이어진다. 금리 움직임을 함께 확인한다.",
            "source": c.SOURCES["per"], "level": "watch",
        })
    if oil and oil["status"] == "watch":
        advice.append({
            "title": "유가 90달러대",
            "body": "이 수준이 이어지면 5~6개월 뒤 기업 마진과 이익 성장률에 부담이 될 수 있다.",
            "source": c.SOURCES["per"], "level": "watch",
        })
    oversold = [w["name"] for w in weekly if w["signal"] == "oversold"]
    if oversold:
        advice.append({
            "title": f"과매도 신호: {', '.join(oversold)}",
            "body": f"스토캐스틱과 윌리엄스 %R이 함께 과매도다. 현금 {c.CASH_TARGET_PCT}% 중 절반까지 지수 ETF 분할 매수를 검토하고, 반등하면 현금 비중을 복원한다.",
            "source": c.SOURCES["chart"], "level": "ok",
        })
    overbought = [w["name"] for w in weekly if w["signal"] == "overbought"]
    if overbought:
        advice.append({
            "title": f"과매수 신호: {', '.join(overbought)}",
            "body": "단기 과열 구간이다. 추격 매수보다 계획된 비중을 유지하고 모멘텀 포지션은 일부 차익 실현을 검토한다.",
            "source": c.SOURCES["chart"], "level": "watch",
        })
    low_std = [w["name"] for w in weekly if w["std_low"]]
    if low_std:
        advice.append({
            "title": f"변동성 축소: {', '.join(low_std)}",
            "body": "표준편차가 낮다. 곧 위아래 어느 쪽으로든 크게 움직일 수 있다는 뜻이며 방향을 알려주지는 않는다.",
            "source": c.SOURCES["chart"], "level": "watch",
        })
    weak = [i["name"] for i in daily if i["kind"] == "index" and not i.get("above_ma200", True)]
    if weak:
        advice.append({
            "title": f"200일선 아래: {', '.join(weak)}",
            "body": "하락 추세에서는 싸 보여도 비싸게 팔 기회가 적다. 가격만 보고 물타기하지 말고 지수 중심으로 나눠 산다.",
            "source": c.SOURCES["chart"], "level": "watch",
        })
    hot = [i["name"] for i in fred_items if i["group"] == "inflation" and i["status"] == "warn"]
    if hot:
        advice.append({
            "title": f"물가 3% 이상: {', '.join(hot)}",
            "body": "금리 인하 기대가 약해지는 수준이다. 비용 상승을 견디는 고마진 기업과 매출 증가율을 먼저 본다.",
            "source": c.SOURCES["roe"], "level": "watch",
        })
    advice.append({
        "title": f"현금 {c.CASH_TARGET_PCT}% 원칙",
        "body": "과매도 신호가 없으면 현금 비중을 유지하고, 컨빅션 종목은 주가 하락만으로 팔지 않는다.",
        "source": "사용자 설정", "level": "ok",
    })
    return advice


def stance_of(daily, weekly, phase):
    by_id = {item["id"]: item for item in daily}
    if phase["key"] in ("slowdown", "deep_slowdown", "recession"):
        return "신중"
    if by_id.get("us10y", {}).get("status") == "warn" and by_id.get("wti", {}).get("status") == "warn":
        return "신중"
    if any(w["signal"] == "oversold" for w in weekly):
        return "분할 매수 기회"
    warnings = sum(1 for item in daily if item["status"] == "warn")
    return "경계 속 계획 유지" if warnings else "계획대로 매수"


def detect_changes(current, previous):
    """이전 스냅샷과 비교해 사람이 볼 변화만 고른다. 이전 값이 없으면 빈 목록을 돌려준다."""
    if not previous:
        return []
    changes = []
    old_daily = {i["id"]: i for i in previous.get("daily", [])}
    labels = {"ok": "정상", "watch": "주의", "warn": "경고"}
    for item in current["daily"]:
        old = old_daily.get(item["id"])
        if old and old["status"] != item["status"]:
            changes.append(f"{item['name']}: {labels[old['status']]} → {labels[item['status']]} ({item['value']}{item['unit']})")
        if old and item["kind"] == "index" and old.get("above_ma200") != item.get("above_ma200"):
            changes.append(f"{item['name']}: 200일선 {'회복' if item.get('above_ma200') else '이탈'}")
    old_weekly = {w["name"]: w for w in previous.get("weekly", [])}
    signal_labels = {"oversold": "과매도", "overbought": "과매수", "neutral": "중립"}
    for week in current["weekly"]:
        old = old_weekly.get(week["name"])
        if old and old["signal"] != week["signal"]:
            changes.append(f"{week['name']} 주봉: {signal_labels[old['signal']]} → {signal_labels[week['signal']]}")
    old_monthly = {i["id"]: i for i in previous.get("monthly", [])}
    for item in current["monthly"]:
        old = old_monthly.get(item["id"])
        if not old or old["asof"] == item["asof"]:
            continue
        message = f"{item['name']} 새 자료({item['asof']}): {old['value']} → {item['value']}{item['unit']}"
        if old["trend"] != item["trend"] and item["trend"] is not None and old["trend"] is not None:
            message += f", 방향 {TREND_LABEL[old['trend']]} → {TREND_LABEL[item['trend']]}"
        changes.append(message)
    if previous.get("phase", {}).get("key") != current["phase"]["key"]:
        changes.insert(0, f"경기 국면 변경: {previous['phase']['name']} → {current['phase']['name']}")
    return changes


def latest_before(history, today):
    dates = sorted(date for date in history if date < today)
    return history[dates[-1]] if dates else None


def as_series(values, start="2020-01-01", freq="MS"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq=freq), dtype=float)
