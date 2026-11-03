"""지표 목록과 기준값. 기준의 출처를 source로 구분한다: 영상 / 관행 / 설정(직접 정한 값)."""

CASH_TARGET_PCT = 20

RATE_WARN = 4.5      # 영상: 미국 10년물 4.5% 초과 시 위험
OIL_WARN = 100       # 영상: 유가 100달러
OIL_WATCH = 90       # 영상: 90달러대 유지 시 이익 성장률 부담
INFLATION_WARN = 3.0 # 영상: CPI·PCE 3%는 금리 인하를 막는 기준
FX_MOVE_WATCH = 2.0  # 설정: 20거래일 2% 이상 변동
DD_WARN = -10        # 설정: 고점 대비 10% 하락
DD_BEAR = -20        # 영상: 20% 하락은 약세장
OVERSOLD_K, OVERSOLD_WR = 20, -80      # 관행: 영상에 수치 언급 없음
OVERBOUGHT_K, OVERBOUGHT_WR = 80, -20  # 관행: 영상에 수치 언급 없음
STD_LOW_PCTL = 20    # 설정: 3년 중 하위 20%면 표준편차가 낮다고 판단

MARKETS = {
    "us10y": {"ticker": "^TNX", "name": "미국 10년물 금리", "unit": "%", "kind": "rate"},
    "wti": {"ticker": "CL=F", "name": "WTI 유가", "unit": "달러", "kind": "oil"},
    "dxy": {"ticker": "DX-Y.NYB", "name": "달러 인덱스", "unit": "", "kind": "fx"},
    "usdkrw": {"ticker": "KRW=X", "name": "원/달러", "unit": "원", "kind": "fx"},
    "spx": {"ticker": "^GSPC", "name": "S&P 500", "unit": "", "kind": "index"},
    "ixic": {"ticker": "^IXIC", "name": "나스닥 종합", "unit": "", "kind": "index"},
    "kospi": {"ticker": "^KS11", "name": "코스피", "unit": "", "kind": "index"},
}

WEEKLY_TICKERS = {"spx": "S&P 500", "kospi": "코스피"}

# transform: trend=수준의 추세, diffusion=0 기준 지수, inverse=낮을수록 좋음, quarterly=분기 성장률,
# yoy=전년 대비 %, level=수준만 표시
FRED_SERIES = {
    "pmi_proxy": {"id": "GACDFSA066MSFRBPHI", "name": "필라델피아 연은 제조업지수(PMI 대체)", "group": "leading", "transform": "diffusion", "core": True},
    "sentiment": {"id": "UMCSENT", "name": "소비자심리지수(미시간대)", "group": "leading", "transform": "trend", "core": False},
    "curve": {"id": "T10Y2Y", "name": "장단기 금리차(10년-2년)", "group": "leading", "transform": "level", "core": False, "unit": "%p"},
    "indpro": {"id": "INDPRO", "name": "산업 생산", "group": "coincident", "transform": "trend", "core": True},
    "retail": {"id": "RSAFS", "name": "소매 판매", "group": "coincident", "transform": "trend", "core": True},
    "tcu": {"id": "TCU", "name": "설비 가동률", "group": "coincident", "transform": "trend", "core": False},
    "gdp": {"id": "A191RL1Q225SBEA", "name": "실질 GDP 성장률", "group": "lagging", "transform": "quarterly", "core": True, "unit": "%"},
    "unrate": {"id": "UNRATE", "name": "실업률", "group": "lagging", "transform": "inverse", "core": True, "unit": "%"},
    "hours": {"id": "AWHAETP", "name": "주당 노동시간", "group": "lagging", "transform": "trend", "core": False},
    "wages": {"id": "CES0500000003", "name": "시간당 임금(전년 대비)", "group": "lagging", "transform": "yoy", "core": False},
    "cpi": {"id": "CPIAUCSL", "name": "CPI(전년 대비)", "group": "inflation", "transform": "yoy", "core": True},
    "pce": {"id": "PCEPI", "name": "PCE 물가(전년 대비)", "group": "inflation", "transform": "yoy", "core": True},
    "capex": {"id": "NEWORDER", "name": "자본재 주문(항공 제외)", "group": "aux", "transform": "trend", "core": False},
}

GROUP_NAMES = {
    "leading": "선행", "coincident": "동행", "lagging": "후행",
    "inflation": "물가", "aux": "참고",
}

# 아직 자동 수집하지 않는 지표. 값을 지어내지 않고 화면에 미연동으로 표시한다.
NOT_CONNECTED = [
    ("외국인 순매수(10~20일 누적)", "매일", "안정적인 무료 출처 확인 필요"),
    ("ISM 제조업 PMI", "매달", "FRED 미제공. 필라델피아 연은 지수로 대체"),
    ("S&P 500 12개월 선행 PER", "매주", "무료 공식 데이터 없음"),
    ("EPS 추정치 변화", "매주", "유료 데이터 필요"),
    ("투자자 예탁금", "매주", "금융투자협회 출처 연동 필요"),
    ("한국 반도체 수출", "매달", "한국은행 ECOS API 키 필요"),
]

SOURCES = {
    "macro": "경기를 보고 투자하라, 3부작 총정리",
    "loss": "만약 손실이 난다면 근본적인 원인을 분석해야 합니다",
    "chart": "백찬규 센터장의 주식 차트 분석법 합본",
    "h2": "7월 변동성 예견한 백찬규 센터장의 하반기 전략",
    "per": "주식은 시간을 사는 것입니다",
    "roe": "미 증시, 사상 최고치 랠리! 단, 조건을 충족하는 기업만 오릅니다",
    "growth": "실적이 좋아도 주가가 안 오르는 기업의 비밀",
}
