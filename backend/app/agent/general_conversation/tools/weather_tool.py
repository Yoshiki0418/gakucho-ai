"""
天気ツール - Open-Meteo API（無料・APIキー不要）
日本各地を含む世界中の天気情報を取得します。
「今日」「明日」「明後日」の天気予報にも対応。
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

from agents import function_tool

# WMO Weather Code → 日本語天気表現
_WMO_DESCRIPTIONS: dict[int, str] = {
    0: "快晴",
    1: "おおむね晴れ",
    2: "一部曇り",
    3: "曇り",
    45: "霧",
    48: "着氷性の霧",
    51: "弱い霧雨",
    53: "霧雨",
    55: "強い霧雨",
    56: "弱い着氷性の霧雨",
    57: "強い着氷性の霧雨",
    61: "弱い雨",
    63: "雨",
    65: "強い雨",
    66: "弱い着氷性の雨",
    67: "強い着氷性の雨",
    71: "弱い雪",
    73: "雪",
    75: "強い雪",
    77: "霧雪",
    80: "弱いにわか雨",
    81: "にわか雨",
    82: "激しいにわか雨",
    85: "弱いにわか雪",
    86: "激しいにわか雪",
    95: "雷雨",
    96: "雹を伴う雷雨",
    99: "激しい雹を伴う雷雨",
}

# when パラメータ → 日数オフセット
_WHEN_OFFSETS: dict[str, int] = {
    "今日": 0,
    "今": 0,
    "現在": 0,
    "明日": 1,
    "あした": 1,
    "明後日": 2,
    "あさって": 2,
    "明々後日": 3,
    "しあさって": 3,
}


def _geocode(city: str) -> tuple[float, float, str] | None:
    """都市名から緯度・経度を取得する（Open-Meteo Geocoding API）"""
    params = urllib.parse.urlencode({
        "name": city,
        "count": 1,
        "language": "ja",
        "format": "json",
    })
    url = f"https://geocoding-api.open-meteo.com/v1/search?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GakuchoAI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    results = data.get("results")
    if not results:
        return None

    r = results[0]
    name = r.get("name", city)
    return (r["latitude"], r["longitude"], name)


def _fetch_current(lat: float, lon: float) -> dict | None:
    """現在の天気を取得する"""
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": "Asia/Tokyo",
        "forecast_days": 1,
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GakuchoAI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    return data.get("current")


def _fetch_daily(lat: float, lon: float, target_date: str) -> dict | None:
    """指定日の天気予報を取得する（target_date: YYYY-MM-DD）"""
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
        "timezone": "Asia/Tokyo",
        "start_date": target_date,
        "end_date": target_date,
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GakuchoAI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    daily = data.get("daily")
    if not daily:
        return None

    # daily の各フィールドはリスト形式、1日分なのでインデックス0
    return {
        "weather_code": daily["weather_code"][0],
        "temp_max": daily["temperature_2m_max"][0],
        "temp_min": daily["temperature_2m_min"][0],
        "precip_prob": daily["precipitation_probability_max"][0],
        "wind_max": daily["wind_speed_10m_max"][0],
    }


def _resolve_offset(when: str) -> int:
    """when 文字列から日数オフセットを返す（デフォルト0=今日）"""
    when_normalized = when.strip()
    return _WHEN_OFFSETS.get(when_normalized, 0)


@function_tool
def get_weather(city: str, when: str = "今") -> str:
    """
    指定した都市の天気情報を取得します。
    日本各地（東京、大阪、札幌、金沢、那覇など）をはじめ、
    世界中の都市に対応しています。

    Args:
        city: 都市名（例: 東京、大阪、金沢、石川）
        when: いつの天気か（例: 今、今日、明日、明後日）。デフォルトは「今」
    """
    # 1. ジオコーディング
    geo = _geocode(city)
    if geo is None:
        return f"「{city}」の位置情報を取得できませんでした。正しい都市名を指定してください。"

    lat, lon, resolved_name = geo
    offset = _resolve_offset(when)

    # 2. 今日・現在の場合は現在の天気を返す
    if offset == 0:
        current = _fetch_current(lat, lon)
        if current is None:
            return f"「{resolved_name}」の天気情報を取得できませんでした。"

        temp = current.get("temperature_2m", "不明")
        humidity = current.get("relative_humidity_2m", "不明")
        wind = current.get("wind_speed_10m", "不明")
        weather_code = current.get("weather_code", -1)
        description = _WMO_DESCRIPTIONS.get(weather_code, "不明")

        return (
            f"{resolved_name}は今{description}で、"
            f"気温は{temp}度、湿度{humidity}パーセント、"
            f"風は{wind}キロくらいです。"
        )

    # 3. 明日以降は日別予報を返す
    target = datetime.now() + timedelta(days=offset)
    target_str = target.strftime("%Y-%m-%d")
    daily = _fetch_daily(lat, lon, target_str)

    if daily is None:
        return f"「{resolved_name}」の{when}の天気予報を取得できませんでした。"

    description = _WMO_DESCRIPTIONS.get(daily["weather_code"], "不明")
    temp_max = daily["temp_max"]
    temp_min = daily["temp_min"]
    precip = daily["precip_prob"]
    wind_max = daily["wind_max"]

    when_label = when if when in ("明日", "明後日", "明々後日") else f"{target.month}月{target.day}日"

    return (
        f"{resolved_name}の{when_label}の天気は{description}の予報で、"
        f"最高気温{temp_max}度、最低気温{temp_min}度、"
        f"降水確率は{precip}パーセント、"
        f"風は最大{wind_max}キロくらいの見込みです。"
    )
