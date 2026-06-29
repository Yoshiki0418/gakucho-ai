"""
ベンチマーク自動実行スクリプト。

定義済みクエリセットを各条件（filler_on / filler_off）× 複数回反復で
APIに送信し、タイミングデータを CSV に保存する。

Usage:
    python -m benchmark.benchmark_runner --api-url http://localhost:8076 --trials 5
    python -m benchmark.benchmark_runner --api-url http://localhost:8076 --trials 3 --conditions filler_on
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

from benchmark.benchmark_queries import BENCHMARK_QUERIES

# --- デフォルト設定 ---
DEFAULT_API_URL = "http://localhost:8077"
DEFAULT_TRIALS = 5
DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "data", "benchmark_results",
)

# --- 条件定義 ---
CONDITIONS = {
    "dynamic_filler": {"filler_mode": "dynamic", "mode": "general"},  # 提案手法 (実験1互換用)
    "static_filler": {"filler_mode": "static", "mode": "general"},    # 比較手法1（定型フィラー）
    "filler_off": {"filler_mode": "off", "mode": "general"},          # 比較手法2（フィラーなし）
    "multi_agent": {"filler_mode": "off", "mode": "general"},     # 実験2用（提案手法・Multi-Agent・フィラー無効）
    "single_agent": {"filler_mode": "off", "mode": "baseline"},   # 実験2用（比較手法・Single Agent・フィラー無効）
}

# CSV カラム定義
CSV_COLUMNS = [
    "condition",
    "category",
    "query",
    "trial",
    "ttft_ms",
    "ttfa_ms",
    "ttmr_ms",
    "total_ms",
    "filler_fired",
    "filler_text",
    "filler_ttfb_ms",
    "first_sentence_ms",
    "tts_duration_ms",
    "filler_duration_ms",
    "classifier_ms",
    "route",
    "main_responded_in_time",
    "response_text",
    "timestamp",
]


def run_single_query(
    api_url: str,
    query: str,
    filler_mode: str = "dynamic",
    mode: str = "general",
) -> dict:
    """
    1つのクエリをAPIに送信し、SSEストリームからタイミングデータを取得する。
    """
    params = {
        "text": query,
        "user_id": "benchmark",
        "session_id": f"bench_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "mode": mode,
        "filler_mode": filler_mode,
        "benchmark_mode": "true",
    }
    url = f"{api_url}/api/text-chat/char-stream-orchestrator?{urllib.parse.urlencode(params)}"

    timing = {}
    response_text = ""

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=60) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                event_type = data.get("type", "")

                if event_type == "text_chunk":
                    response_text += data.get("content", "")
                elif event_type == "timing":
                    timing = data
                elif event_type == "done":
                    break
    except Exception as e:
        print(f"  [ERROR] {e}")
        timing = {"error": str(e)}

    timing["response_text"] = response_text.strip()
    return timing


def run_benchmark(
    api_url: str,
    trials: int,
    conditions: list[str],
    output_dir: str,
    categories: list[str] | None = None,
) -> str:
    """
    全条件・全クエリ・全試行のベンチマークを実行し、結果をCSVに保存する。

    Returns:
        出力CSVファイルのパス
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"benchmark_{timestamp}.csv")

    # 使用するカテゴリをフィルタ
    query_categories = categories or list(BENCHMARK_QUERIES.keys())

    total_runs = 0
    for condition in conditions:
        for category in query_categories:
            if category not in BENCHMARK_QUERIES:
                continue
            if condition in ["multi_agent", "single_agent"] and category in ["rag_search", "greeting", "unclear_query", "emotional_query"]:
                continue
            total_runs += len(BENCHMARK_QUERIES[category]["queries"]) * trials

    print(f"=== ベンチマーク開始 ===")
    print(f"  API: {api_url}")
    print(f"  条件: {conditions}")
    print(f"  カテゴリ: {query_categories}")
    print(f"  試行回数: {trials}")
    print(f"  合計実行数: {total_runs}")
    print(f"  出力先: {output_path}")
    print()

    # CSV ファイルを初期化してヘッダーを書き込む
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()

    results = []
    run_count = 0

    for condition in conditions:
        cond_params = CONDITIONS[condition]
        print(f"--- 条件: {condition} ---")

        for category in query_categories:
            if category not in BENCHMARK_QUERIES:
                print(f"  [SKIP] 不明なカテゴリ: {category}")
                continue

            if condition in ["multi_agent", "single_agent"] and category in ["rag_search", "greeting", "unclear_query", "emotional_query"]:
                print(f"  [SKIP] 実験2評価対象外カテゴリ: {category}")
                continue

            cat_info = BENCHMARK_QUERIES[category]
            print(f"  カテゴリ: {category} ({cat_info['description']})")

            for query in cat_info["queries"]:
                for trial in range(1, trials + 1):
                    run_count += 1
                    print(
                        f"    [{run_count}/{total_runs}] "
                        f"trial={trial} query=\"{query[:25]}...\""
                        if len(query) > 25
                        else f"    [{run_count}/{total_runs}] "
                        f"trial={trial} query=\"{query}\"",
                        end="",
                        flush=True,
                    )

                    timing = run_single_query(
                        api_url=api_url,
                        query=query,
                        filler_mode=cond_params["filler_mode"],
                        mode=cond_params.get("mode", "general"),
                    )

                    row = {
                        "condition": condition,
                        "category": category,
                        "query": query,
                        "trial": trial,
                        "ttft_ms": timing.get("ttft_ms"),
                        "ttfa_ms": timing.get("ttfa_ms"),
                        "ttmr_ms": timing.get("ttmr_ms"),
                        "total_ms": timing.get("total_ms"),
                        "filler_fired": timing.get("filler_fired"),
                        "filler_text": timing.get("filler_text", ""),
                        "filler_ttfb_ms": timing.get("filler_ttfb_ms"),
                        "first_sentence_ms": timing.get("first_sentence_ms"),
                        "tts_duration_ms": timing.get("tts_duration_ms"),
                        "filler_duration_ms": timing.get("filler_duration_ms"),
                        "classifier_ms": timing.get("classifier_ms"),
                        "route": timing.get("route"),
                        "main_responded_in_time": timing.get("main_responded_in_time"),
                        "response_text": timing.get("response_text", ""),
                        "timestamp": datetime.now().isoformat(),
                    }
                    results.append(row)

                    # 1行ごとにCSVに追記する（途中で強制終了しても保存されるようにする）
                    with open(output_path, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                        writer.writerow(row)

                    ttft = timing.get("ttft_ms", "?")
                    ttfa = timing.get("ttfa_ms", "?")
                    total = timing.get("total_ms", "?")
                    filler = "Yes" if timing.get("filler_fired") else "No"
                    print(f"  → TTFT={ttft}ms, TTFA={ttfa}ms, Total={total}ms, Filler={filler}")

                    # APIに負荷をかけすぎないよう少し待つ
                    time.sleep(1.0)

    print()
    print(f"=== ベンチマーク完了 ===")
    print(f"  結果: {len(results)} 件")
    print(f"  保存先: {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Gakucho-AI レイテンシベンチマーク実行ツール"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"バックエンドAPIのURL（デフォルト: {DEFAULT_API_URL}）",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=DEFAULT_TRIALS,
        help=f"各クエリの反復回数（デフォルト: {DEFAULT_TRIALS}）",
    )
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=list(CONDITIONS.keys()),
        choices=list(CONDITIONS.keys()),
        help="実行する条件（デフォルト: 全条件）",
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        default=None,
        choices=list(BENCHMARK_QUERIES.keys()),
        help="実行するカテゴリ（デフォルト: 全カテゴリ）",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"結果の出力先ディレクトリ",
    )
    args = parser.parse_args()

    output_path = run_benchmark(
        api_url=args.api_url,
        trials=args.trials,
        conditions=args.conditions,
        output_dir=args.output_dir,
        categories=args.categories,
    )

    # 分析スクリプトの案内
    print()
    print("分析を実行するには:")
    print(f"  python -m benchmark.analyze_benchmark --input \"{output_path}\"")


if __name__ == "__main__":
    main()
