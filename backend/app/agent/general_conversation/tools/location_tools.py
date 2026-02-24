"""
地理情報ツール — 周辺施設検索 & 移動時間
すべて無料API（APIキー不要）を使用。
- Overpass API (OpenStreetMap): 周辺施設検索
- Nominatim (OpenStreetMap): ジオコーディング
- OSRM: ルート検索・移動時間
"""

import json
import urllib.parse
import urllib.request

from agents import function_tool

# =========================================================
# 定数
# =========================================================
# 金沢工業大学 扇が丘キャンパス
KIT_LAT = 36.5326
KIT_LON = 136.6271
KIT_NAME = "金沢工業大学"

_HEADERS = {"User-Agent": "GakuchoAI/1.0"}

# ユーザー入力 → OSM タグのマッピング
_CATEGORY_MAP: dict[str, list[dict[str, str]]] = {
    "飲食店": [{"amenity": "restaurant"}, {"amenity": "fast_food"}],
    "レストラン": [{"amenity": "restaurant"}],
    "ラーメン": [{"amenity": "restaurant", "cuisine": "ramen"}],
    "カフェ": [{"amenity": "cafe"}],
    "喫茶店": [{"amenity": "cafe"}],
    "居酒屋": [{"amenity": "bar"}, {"amenity": "pub"}],
    "コンビニ": [{"shop": "convenience"}],
    "スーパー": [{"shop": "supermarket"}],
    "薬局": [{"amenity": "pharmacy"}, {"shop": "chemist"}],
    "ドラッグストア": [{"amenity": "pharmacy"}, {"shop": "chemist"}],
    "病院": [{"amenity": "hospital"}, {"amenity": "clinic"}],
    "本屋": [{"shop": "books"}],
    "銀行": [{"amenity": "bank"}],
    "ATM": [{"amenity": "atm"}],
    "駐車場": [{"amenity": "parking"}],
    "ガソリンスタンド": [{"amenity": "fuel"}],
}

# 「大学」等を金沢工業大学として解決するキーワード
_KIT_KEYWORDS = {"大学", "学校", "キャンパス", "うち", "ここ", "金沢工業大学", "KIT"}

# 移動モード → OSRM profile
_MODE_MAP: dict[str, str] = {
    "車": "car",
    "car": "car",
    "driving": "car",
    "徒歩": "foot",
    "歩き": "foot",
    "foot": "foot",
    "walking": "foot",
    "自転車": "bike",
    "bike": "bike",
    "cycling": "bike",
}

_MODE_LABELS: dict[str, str] = {
    "car": "車",
    "foot": "徒歩",
    "bike": "自転車",
}


# =========================================================
# 内部ヘルパー
# =========================================================
def _is_kit_reference(place: str) -> bool:
    """placeが金沢工業大学を指しているか"""
    return any(kw in place for kw in _KIT_KEYWORDS)


def _nominatim_geocode(place: str) -> tuple[float, float, str] | None:
    """Nominatim で場所名 → 緯度経度"""
    params = urllib.parse.urlencode(
        {
            "q": place,
            "format": "json",
            "limit": 1,
            "countrycodes": "jp",
            "accept-language": "ja",
        }
    )
    url = f"https://nominatim.openstreetmap.org/search?{params}"

    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    if not data:
        return None

    r = data[0]
    name = r.get("display_name", place).split(",")[0]
    return (float(r["lat"]), float(r["lon"]), name)


def _resolve_place(place: str) -> tuple[float, float, str]:
    """プレイス名を座標に解決。大学系キーワードはKIT固定"""
    if _is_kit_reference(place):
        return (KIT_LAT, KIT_LON, KIT_NAME)

    result = _nominatim_geocode(place)
    if result:
        return result

    # フォールバック: 金沢工業大学
    return (KIT_LAT, KIT_LON, KIT_NAME)


def _resolve_category(category: str) -> list[dict[str, str]]:
    """カテゴリ文字列 → OSM タグリスト"""
    # 完全一致
    if category in _CATEGORY_MAP:
        return _CATEGORY_MAP[category]

    # 部分一致
    for key, tags in _CATEGORY_MAP.items():
        if key in category or category in key:
            return tags

    # デフォルト: 飲食店
    return _CATEGORY_MAP["飲食店"]


def _build_overpass_query(
    lat: float, lon: float, radius: int, tags_list: list[dict[str, str]]
) -> str:
    """Overpass QL クエリを構築"""
    queries = []
    for tags in tags_list:
        tag_filters = "".join(f'["{k}"="{v}"]' for k, v in tags.items())
        queries.append(f"  node{tag_filters}(around:{radius},{lat},{lon});")
        queries.append(f"  way{tag_filters}(around:{radius},{lat},{lon});")

    query_body = "\n".join(queries)
    return f"[out:json][timeout:10];\n(\n{query_body}\n);\nout center body qt 10;"


def _overpass_search(query: str) -> list[dict]:
    """Overpass API を実行して結果を返す"""
    url = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []

    return result.get("elements", [])


def _format_place_name(element: dict) -> str | None:
    """OSM要素から場所名を取得"""
    tags = element.get("tags", {})
    return tags.get("name") or tags.get("name:ja")


def _osrm_route(
    origin_lon: float,
    origin_lat: float,
    dest_lon: float,
    dest_lat: float,
    profile: str = "car",
) -> dict | None:
    """OSRM で2点間のルート情報を取得"""
    base = "https://router.project-osrm.org"
    coords = f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
    url = f"{base}/route/v1/{profile}/{coords}?overview=false"

    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    if data.get("code") != "Ok" or not data.get("routes"):
        return None

    route = data["routes"][0]
    return {
        "duration_sec": route["duration"],
        "distance_m": route["distance"],
    }


def _format_duration(seconds: float) -> str:
    """秒数を自然な日本語に変換"""
    minutes = round(seconds / 60)
    if minutes < 1:
        return "1分未満"
    if minutes < 60:
        return f"約{minutes}分"
    hours = minutes // 60
    remaining = minutes % 60
    if remaining == 0:
        return f"約{hours}時間"
    return f"約{hours}時間{remaining}分"


def _format_distance(meters: float) -> str:
    """メートルを自然な日本語に変換"""
    if meters < 1000:
        return f"約{round(meters)}メートル"
    km = meters / 1000
    return f"約{km:.1f}キロ"


# =========================================================
# 公開ツール
# =========================================================
@function_tool
def search_nearby_places(
    place: str = "大学",
    category: str = "飲食店",
    radius: int = 800,
) -> str:
    """
    指定した場所の周辺にある施設を検索します。
    「大学」「学校」「キャンパス」と言った場合は金沢工業大学を指します。

    Args:
        place: 検索の中心となる場所（例: 大学、金沢駅、香林坊）デフォルトは金沢工業大学
        category: 検索カテゴリ（例: 飲食店、カフェ、コンビニ、ラーメン、居酒屋、スーパー、薬局）
        radius: 検索半径（メートル）。デフォルト800m。最大2000m
    """
    # 半径を制限
    radius = min(max(radius, 100), 2000)

    # 場所を解決
    lat, lon, resolved_name = _resolve_place(place)

    # カテゴリを解決
    tags_list = _resolve_category(category)

    # Overpass クエリ実行
    query = _build_overpass_query(lat, lon, radius, tags_list)
    elements = _overpass_search(query)

    # 名前のあるスポットだけ抽出
    places = []
    for el in elements:
        name = _format_place_name(el)
        if name:
            places.append(name)

    # 重複除去（順序保持）
    seen = set()
    unique_places = []
    for p in places:
        if p not in seen:
            seen.add(p)
            unique_places.append(p)

    if not unique_places:
        return (
            f"{resolved_name}の周辺{radius}メートル以内に"
            f"「{category}」は見つかりませんでした。"
            f"範囲を広げるか、別のカテゴリで探してみてください。"
        )

    # 最大8件まで
    display = unique_places[:8]
    names_str = "、".join(display)
    total = len(unique_places)

    result = (
        f"{resolved_name}の周辺{radius}メートル以内に"
        f"「{category}」が{total}件見つかりました。"
        f"例えば、{names_str}などがあります。"
    )

    if total > 8:
        result += f"（他にも{total - 8}件あります）"

    return result


@function_tool
def get_travel_info(
    origin: str = "大学",
    destination: str = "金沢駅",
    mode: str = "車",
) -> str:
    """
    2地点間の移動時間と距離を調べます。
    「大学」「学校」と言った場合は金沢工業大学を指します。

    Args:
        origin: 出発地（例: 大学、金沢駅、香林坊）
        destination: 目的地（例: 金沢駅、兼六園、小松空港）
        mode: 移動手段（車、徒歩、自転車）。デフォルトは車
    """
    # 場所を解決
    o_lat, o_lon, o_name = _resolve_place(origin)
    d_lat, d_lon, d_name = _resolve_place(destination)

    # モードを解決
    profile = _MODE_MAP.get(mode, "car")
    mode_label = _MODE_LABELS.get(profile, "車")

    # ルート検索
    route = _osrm_route(o_lon, o_lat, d_lon, d_lat, profile)

    if route is None:
        return (
            f"{o_name}から{d_name}までの{mode_label}でのルートを"
            f"取得できませんでした。"
        )

    duration = _format_duration(route["duration_sec"])
    distance = _format_distance(route["distance_m"])

    return (
        f"{o_name}から{d_name}までは{mode_label}で{duration}、"
        f"距離は{distance}くらいです。"
    )
