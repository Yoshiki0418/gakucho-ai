"""
キャンパスナビゲーションツール — キャンパス内の建物間の経路案内
グラフ（ネットワーク）構造とダイクストラ法を用いて最適な道順を計算します。
"""

import heapq
from agents import function_tool

# ノード（建物や交差点）の定義
BUILDINGS = [
    "1号館", "2号館", "3号館", "5号館", "6号館", "7号館", "8号館", "9号館",
    "10号館", "11号館", "12号館", "13号館", "15号館", "17号館", "20号館",
    "21号館", "23号館", "24号館", "26号館", "27号館", "28号館", "29号館",
    "31号館", "32号館", "36号館", "39号館", "40号館", "41号館", "43号館",
    "47号館"
]

# エッジ（接続関係）: (ノードA, ノードB, 距離(m), 方向)
# マップ画像に基づいて大まかな距離と方角を定義
EDGES = [
    # 1号館周辺 (北西/正門エリア)
    ("1号館", "3号館", 30, "東"),
    ("1号館", "2号館", 20, "西"),
    ("1号館", "11号館", 60, "南"),
    ("3号館", "6号館", 50, "東"),
    
    # 南西エリア (11, 15, 12, 13, 20号館など)
    ("11号館", "17号館", 30, "西"),
    ("11号館", "15号館", 40, "東"),
    ("15号館", "32号館", 50, "西"),
    ("15号館", "12号館", 60, "南"),
    ("12号館", "20号館", 60, "西"),
    ("12号館", "13号館", 30, "東"),
    ("13号館", "10号館", 50, "東"),
    
    # 中央南エリア (10, 39, 9, 29, 21号館)
    ("10号館", "39号館", 20, "南"),
    ("10号館", "9号館", 30, "東"),
    ("9号館", "29号館", 20, "北"),
    ("9号館", "21号館", 80, "東"),
    
    # 中央エリア (6, 47, 40, 7, 5, 8号館)
    ("6号館", "47号館", 30, "北"),
    ("6号館", "40号館", 30, "北東"),
    ("6号館", "7号館", 50, "東"),  # 7号館 = ライブラリーセンター
    ("7号館", "5号館", 30, "東"),
    ("7号館", "8号館", 50, "南"),
    ("8号館", "21号館", 30, "南"),
    
    # 東エリア (24, 26, 23, 27, 31, 36, 41, 43号館)
    ("7号館", "24号館", 60, "東"),
    ("8号館", "26号館", 40, "東"),
    ("21号館", "26号館", 50, "北東"),
    ("21号館", "28号館", 60, "南"),
    ("24号館", "23号館", 60, "北"),
    ("23号館", "27号館", 20, "西"),
    ("24号館", "31号館", 50, "東"),
    ("31号館", "36号館", 40, "南東"),
    ("31号館", "41号館", 60, "東"), # 41号館 = 夢考房
    ("41号館", "43号館", 20, "南"),
    ("26号館", "41号館", 80, "東"),
]

# 双方向グラフ辞書の構築
_GRAPH = {}
for u, v, dist, direction in EDGES:
    if u not in _GRAPH: _GRAPH[u] = []
    if v not in _GRAPH: _GRAPH[v] = []
    _GRAPH[u].append((v, dist, direction))
    
    # 逆方向の計算
    opposite = {
        "北": "南", "南": "北", 
        "東": "西", "西": "東", 
        "北東": "南西", "南西": "北東", 
        "北西": "南東", "南東": "北西"
    }.get(direction, "")
    _GRAPH[v].append((u, dist, opposite))


def _dijkstra(start: str, end: str):
    """ダイクストラ法で最短経路を探索"""
    if start not in _GRAPH or end not in _GRAPH:
        return None
    
    # queue: (cost, current_node, path)
    queue = [(0, start, [])]
    visited = set()
    
    while queue:
        cost, current, path = heapq.heappop(queue)
        
        if current in visited:
            continue
        visited.add(current)
        
        if current == end:
            return path + [(current, 0, "")]
            
        for neighbor, dist, direction in _GRAPH[current]:
            if neighbor not in visited:
                heapq.heappush(queue, (cost + dist, neighbor, path + [(current, dist, direction)]))
                
    return None


def _generate_directions_text(path) -> str:
    """経路データから自然言語の道順を生成"""
    if not path or len(path) == 1:
        return "すでに目的地に到着しています。"
    
    total_dist = 0
    instructions = []
    
    for i in range(len(path) - 1):
        current, dist, direction = path[i]
        next_node = path[i+1][0]
        total_dist += dist
        instructions.append(f"{current}から{direction}へ進んで{next_node}へ向かいます。")
        
    minutes = max(1, total_dist // 80) # 徒歩80m/分として計算
    
    text = f"総距離は約{total_dist}m、徒歩で約{minutes}分です。\n"
    for i, step in enumerate(instructions):
        text += f" {i+1}. {step}\n"
    
    return text


@function_tool
def get_campus_route(start: str, end: str) -> str:
    """
    金沢工業大学キャンパス内の2つの建物間の道順を案内します。
    「1号館から41号館への行き方」のように、キャンパス内の建物のナビゲーションに使用してください。
    
    Args:
        start: 出発地の建物名（例: "1号館", "ライブラリーセンター"）
        end: 目的地の建物名（例: "41号館", "夢考房"）
    """
    # エイリアスの解決
    aliases = {
        "ライブラリーセンター": "7号館",
        "ライブラリセンター": "7号館",
        "夢考房": "41号館",
        "食堂": "21号館",
        "カフェテリア": "21号館",
        "学生課": "1号館",
        "教務課": "1号館",
        "正門": "1号館",
        "進路開発センター": "10号館",
        "法人本部": "29号館",
        "保健室": "11号館",
        "扇が丘診療所": "11号館",
        "体育館": "13号館",
        "第1体育館": "13号館",
        "第2体育館": "20号館",
    }
    
    real_start = aliases.get(start, start)
    real_end = aliases.get(end, end)
    
    # "号館" が抜けている場合の補完 (例: "1" -> "1号館")
    if real_start.isdigit(): 
        real_start += "号館"
    if real_end.isdigit(): 
        real_end += "号館"
    
    path = _dijkstra(real_start, real_end)
    if not path:
        return f"「{start}」から「{end}」へのルートが見つかりませんでした。建物名が正しいか確認してください。"
        
    route_text = _generate_directions_text(path)
    return f"【{real_start}から{real_end}への道順】\n{route_text}"
