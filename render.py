"""스냅샷을 외부 의존성이 없는 HTML 한 장으로 만든다."""
from html import escape

import config as c
from analyze import TREND_LABEL

CSS = """
:root{--bg:#f7f7f5;--card:#fff;--text:#1f2328;--muted:#646b73;--line:#e2e4e6;--ok:#16794c;--watch:#a15c00;--warn:#b42318;--okbg:#e7f5ee;--watchbg:#fdf1dc;--warnbg:#fde8e6}
@media (prefers-color-scheme:dark){:root{--bg:#15181c;--card:#1e2227;--text:#e8eaed;--muted:#a0a7b0;--line:#30353b;--ok:#5fd19b;--watch:#f0b45c;--warn:#ff8a7d;--okbg:#17332a;--watchbg:#3a2d16;--warnbg:#3f201d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.6 -apple-system,"Malgun Gothic","Apple SD Gothic Neo",sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 16px 56px}h1{font-size:24px;margin:0}h2{font-size:18px;margin:32px 0 12px}h3{font-size:15px;margin:20px 0 8px;color:var(--muted)}
.sub,.src,.foot{color:var(--muted);font-size:13px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.hero{margin-top:16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.big{font-size:24px;font-weight:700;margin-top:2px}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:700;white-space:nowrap}.ok{background:var(--okbg);color:var(--ok)}.watch{background:var(--watchbg);color:var(--watch)}.warn{background:var(--warnbg);color:var(--warn)}.na{background:var(--line);color:var(--muted)}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}td.wrap{white-space:normal;min-width:190px}tr:last-child td{border-bottom:0}th{font-size:12px;color:var(--muted);font-weight:600}.num{text-align:right;font-variant-numeric:tabular-nums}
.advice{display:grid;gap:10px}.advice .card{border-left:4px solid var(--line)}.advice .ok{background:var(--card);color:inherit;border-left-color:var(--ok)}.advice .watch{background:var(--card);color:inherit;border-left-color:var(--watch)}.advice .warn{background:var(--card);color:inherit;border-left-color:var(--warn)}.advice b{display:block}
ul{margin:0;padding-left:20px}
"""

STATUS = {"ok": "정상", "watch": "주의", "warn": "경고"}
SIGNAL = {"oversold": ("과매도", "warn"), "overbought": ("과매수", "watch"), "neutral": ("중립", "ok")}
TREND_CLASS = {1: "ok", 0: "na", -1: "warn"}


def e(value):
    return escape(str(value))


def badge(text, css):
    return f'<span class="badge {css}">{e(text)}</span>'


def trend_badge(trend):
    if trend is None:
        return badge("표시만", "na")
    return badge(TREND_LABEL[trend], TREND_CLASS[trend])


def daily_table(items):
    rows = "".join(
        f"<tr><td>{e(i['name'])}</td><td class='num'>{i['value']:,}{e(i['unit'])}</td><td class='num'>{i['chg1d']:+.2f}%</td>"
        f"<td class='num'>{i['chg20d']:+.2f}%</td><td>{badge(STATUS[i['status']], i['status'])}</td><td class='wrap'>{e(i['note'])}</td><td class='src'>{e(i['asof'])}</td></tr>"
        for i in items
    )
    return f"<div class='scroll'><table><tr><th>지표</th><th class='num'>현재</th><th class='num'>1일</th><th class='num'>20거래일</th><th>상태</th><th>판단</th><th>기준일</th></tr>{rows}</table></div>"


def weekly_table(items):
    rows = "".join(
        f"<tr><td>{e(w['name'])}</td><td class='num'>{w['slow_k']}</td><td class='num'>{w['slow_d']}</td><td class='num'>{w['williams']}</td>"
        f"<td>{badge(*SIGNAL[w['signal']])}</td><td class='num'>{w['std_pctl']}%</td><td>{badge('낮음', 'watch') if w['std_low'] else badge('보통', 'ok')}</td><td class='src'>{e(w['asof'])}</td></tr>"
        for w in items
    )
    return f"<div class='scroll'><table><tr><th>지수</th><th class='num'>Slow %K</th><th class='num'>Slow %D</th><th class='num'>Williams %R</th><th>신호</th><th class='num'>표준편차 3년 위치</th><th>변동성</th><th>기준일</th></tr>{rows}</table></div>"


def monthly_tables(items, phase):
    html = ""
    for group, title in c.GROUP_NAMES.items():
        rows = ""
        if group == "leading":
            rows += f"<tr><td>S&amp;P 500 주가 <span class='badge ok'>핵심</span></td><td class='num'>-</td><td>{trend_badge(phase['stock_signal'])}</td><td class='wrap'>200일선과 6개월 수익률로 판정</td><td class='src'>매일</td></tr>"
        for i in (x for x in items if x["group"] == group):
            core = " <span class='badge ok'>핵심</span>" if i["core"] else ""
            rows += f"<tr><td>{e(i['name'])}{core}</td><td class='num'>{i['value']:,}{e(i['unit'])}</td><td>{trend_badge(i['trend'])}</td><td class='wrap'>{e(i['note'])}</td><td class='src'>{e(i['asof'])}</td></tr>"
        if rows:
            html += f"<h3>{e(title)}</h3><div class='scroll'><table><tr><th>지표</th><th class='num'>최근값</th><th>방향</th><th>메모</th><th>자료 시점</th></tr>{rows}</table></div>"
    return html


def render(snapshot):
    phase = snapshot["phase"]
    advice = "".join(
        f"<div class='card {e(a['level'])}'><b>{e(a['title'])}</b>{e(a['body'])}<div class='src'>근거: {e(a['source'])}</div></div>"
        for a in snapshot["advice"]
    )
    changes = snapshot["changes"]
    change_html = "<ul>" + "".join(f"<li>{e(x)}</li>" for x in changes) + "</ul>" if changes else "<span class='sub'>직전 기록 대비 눈에 띄는 변화가 없습니다.</span>"
    if not snapshot["has_previous"]:
        change_html = "<span class='sub'>첫 실행이라 비교할 기록이 없습니다. 내일부터 변화를 표시합니다.</span>"
    errors = "".join(f"<li>{e(x)}</li>" for x in snapshot["errors"])
    error_html = f"<h2>수집 실패</h2><div class='card'><ul>{errors}</ul></div>" if errors else ""
    pending = "".join(f"<tr><td>{e(n)}</td><td>{e(p)}</td><td class='wrap'>{e(r)}</td></tr>" for n, p, r in c.NOT_CONNECTED)
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>경제지표 모니터</title><style>{CSS}</style></head><body><main>
<h1>경제지표 모니터</h1><div class="sub">마지막 확인 {e(snapshot['generated_at'])} · 공개 영상의 기준을 개인적으로 정리해 적용한 규칙 기반 판단이며, 영상 출연자나 소속사가 제공하거나 검토한 조언이 아닙니다. 투자 권유가 아닙니다.</div>
<div class="hero"><div class="card"><div class="sub">현재 판단</div><div class="big">{e(snapshot['stance'])}</div></div>
<div class="card"><div class="sub">경기 국면</div><div class="big">{e(phase['name'])}</div><div class="sub">{e(phase['action'])}</div></div>
<div class="card"><div class="sub">선행 · 동행 · 후행</div><div class="big" style="font-size:18px">{trend_badge(phase['leading'])} {trend_badge(phase['coincident'])} {trend_badge(phase['lagging'])}</div><div class="sub">핵심 지표 방향의 합</div></div></div>
<h2>오늘의 변화</h2><div class="card">{change_html}</div>
<h2>조언</h2><div class="advice">{advice}</div>
<h2>매일 볼 지표</h2>{daily_table(snapshot['daily'])}
<h2>매주 볼 지표</h2>{weekly_table(snapshot['weekly'])}
<p class="foot">스토캐스틱 Slow 15·5·5, 윌리엄스 %R 19는 영상의 설정입니다. 과매도·과매수 기준선(20/80, -80/-20)은 영상에 수치가 없어 일반 관행을 적용했습니다. 이번 주 값은 주중에 계속 바뀝니다.</p>
<h2>매달 볼 지표</h2>{monthly_tables(snapshot['monthly'], phase)}
{error_html}
<h2>아직 연결되지 않은 지표</h2><div class="scroll"><table><tr><th>지표</th><th>주기</th><th>사유</th></tr>{pending}</table></div>
<p class="foot">출처: Yahoo Finance, FRED. 시세는 지연될 수 있습니다. 조언은 정해진 규칙으로 생성되며 수익을 보장하지 않습니다. 추세 판정 방식과 일부 기준은 영상 내용을 코드로 옮기며 직접 정한 값입니다(config.py).</p>
</main></body></html>"""
