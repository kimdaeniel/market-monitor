"""Yahoo Finance와 FRED에서 원자료를 가져온다."""
import io
import subprocess
import time

import pandas as pd
import requests
import yfinance as yf

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"


def fetch_price(ticker, period="5y"):
    frame = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if frame.empty:
        raise ValueError(f"{ticker}: 데이터 없음")
    frame.index = frame.index.tz_localize(None).normalize()
    return frame[["High", "Low", "Close"]].dropna()


def download_text(url):
    """이 PC에서는 FRED 요청이 requests로 멈추고 curl로는 바로 끝나 curl을 먼저 쓴다."""
    try:
        result = subprocess.run(
            ["curl", "-sSf", "-m", "20", url], capture_output=True, text=True, encoding="utf-8", check=True
        )
        return result.stdout
    except (subprocess.SubprocessError, OSError):
        response = requests.get(url, timeout=(5, 15), headers={"User-Agent": "market-monitor/1.0"})
        response.raise_for_status()
        return response.text


def fetch_fred(series_id, retries=2):
    last_error = None
    for attempt in range(retries):
        try:
            frame = pd.read_csv(io.StringIO(download_text(FRED_URL.format(series_id))))
            frame.columns = ["date", "value"]
            frame["date"] = pd.to_datetime(frame["date"])
            frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
            return frame.dropna().set_index("date")["value"]
        except (requests.RequestException, ValueError) as error:
            last_error = error
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{series_id}: {last_error}")
