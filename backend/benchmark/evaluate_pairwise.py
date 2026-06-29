"""
Pairwise比較評価スクリプト。
Multi-Agent と Single Agent の回答を同一クエリで直接比較し、
「どちらが専門性・ドメイン適合性で優れているか」をGPT-4oに判定させる。

位置バイアス（A/B の順序効果）対策として、A/B の割り当てをクエリごとにランダム化する。
引き分けを除いた勝率に対して二項検定（片側）で有意性を検証する。

Usage:
    python -m benchmark.evaluate_pairwise \\
        --multi  data/benchmark_results/benchmark_20260608_114649.csv \\
        --single data/benchmark_results/benchmark_20260605_160605_exp2_evaluated.csv
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("エラー: pandas がインストールされていません。")
    sys.exit(1)

# =========================================================
# 評価対象外カテゴリ（evaluate_main_quality.py と同一）
# =========================================================
EXCLUDE_CATEGORIES = {"rag_search", "greeting", "unclear_query", "emotional_query"}

# =========================================================
# GPT-4o ジャッジのシステムプロンプト
# =========================================================
SYSTEM_PROMPT = """あなたはAI対話システムの品質評価を行う専門家です。
以下のシステムの前提を理解した上で評価してください。

【システムの前提】
これは「金沢工業大学の大澤学長」を模した音声対話AIです。
ユーザーとの対話のキャッチボールを重視しており、1ターンで全情報を一方的に提供することより、
ユーザーが本当に求めていることを引き出す応答を理想としています。

【重要：冗長性バイアスへの注意】
「情報量が多い＝専門性が高い」ではありません。
ドメインによって「専門家らしい振る舞い」は異なります。
情報を大量に提供するのは検索エンジンの行動であり、専門家の行動とは別物です。

【ドメイン別「専門性の深さ」の定義】

■ complex_consult（キャリア・人生・生活相談）
  プロのキャリアカウンセラー・コーチが最初にすることは何か？
  → ユーザーの動機・状況・価値観を把握するために「問いかける」こと。
  → 「なぜそれをやりたいのか」「今の状況はどうか」を確認し、個別最適なアドバイスへ繋げる。
  ✅ 動機の深掘り・共感・個別化された問いかけ → 専門性が高い
  ❌ 「まずXXXを学び、次にYYY」という一般的な手順リストの提供 → 専門性が低い（検索エンジンと同じ）

■ cross_domain_complex（複数分野をまたぐ複合質問）
  複数の観点（専門知識と個人見解、または複数ドメインの情報）を自然につなぎ合わせているか。
  ✅ 両方の観点をバランスよく統合している → 専門性が高い
  ❌ 一方の観点だけに偏っている → 専門性が低い

■ research（調査・リサーチ）
  調査結果をそのまま返すのではなく、学長としての示唆・見解・文脈が加わっているか。
  ✅ 事実 ＋ 学長独自の視点・示唆 → 専門性が高い
  ❌ 調査結果の単純な羅列のみ → 専門性が低い

■ location_search（場所・経路案内）
  1号館を起点とした具体的な建物名・距離・目印での案内ができているか。
  ✅ 具体的な目印・方向・距離の感覚 → 専門性が高い
  ❌ 「〜の近くにあります」等の抽象的な案内 → 専門性が低い

■ simple_chat / president_qa（雑談・学長への質問）
  学長としての個性・価値観・経験が応答に滲み出ているか。
  ✅ 個人的な見解・経験談・ユーモア → 専門性が高い
  ❌ 教科書的な一般論 → 専門性が低い

■ multi_agent_tool（ツール利用を伴う質問）
  ツール結果を機械的に読み上げず、学長の言葉で自然に解釈して伝えているか。
  ✅ ツール結果を人間的な言葉に変換 → 専門性が高い

【評価観点】

1. Specialization Depth（専門性深度）
上記【ドメイン別「専門性の深さ」の定義】に照らして、そのドメインで「専門家らしい振る舞い」を
しているのはどちらか？形式（箇条書きか否か）は評価しない。内容の質のみ評価する。

2. Domain Appropriateness（ドメイン適合性）
そのドメインに適したアプローチ・トーン・内容の種類を取っているのはどちらか？
上記の定義に基づいて判断する。形式は評価しない。

【判定基準】
- "A": 回答Aの方が明らかに優れている
- "B": 回答Bの方が明らかに優れている
- "TIE": 実質的に差がなくほぼ同等

【出力形式】
必ず以下のJSONのみを出力してください。
{
  "specialization_depth": {
    "winner": "A" or "B" or "TIE",
    "reason": "判定理由を1文で"
  },
  "domain_appropriateness": {
    "winner": "A" or "B" or "TIE",
    "reason": "判定理由を1文で"
  }
}
"""


def load_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("\"'")
                    break
    return key


def call_judge(api_key: str, query: str, response_a: str, response_b: str,
               category: str = "", model: str = "gpt-4o") -> dict | None:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    user_message = (
        f"【質問】\n{query}\n\n"
        f"【回答A】\n{response_a}\n\n"
        f"【回答B】\n{response_b}"
    )
    if category:
        user_message += f"\n\n【ドメイン】{category}"

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST"
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            if attempt == 2:
                print(f"\nAPI Error: {e}")
                return None
            time.sleep(2)
    return None


def resolve_winner(raw_winner: str, multi_is_a: bool) -> str:
    """A/B表記をmulti/singleに変換する"""
    if raw_winner == "TIE":
        return "TIE"
    if raw_winner == "A":
        return "multi" if multi_is_a else "single"
    if raw_winner == "B":
        return "single" if multi_is_a else "multi"
    return "TIE"


def print_metric_summary(df_results: "pd.DataFrame", metric: str, has_scipy: bool) -> None:
    from scipy.stats import binomtest  # type: ignore

    sub = df_results[df_results["metric"] == metric]
    multi_wins = int((sub["winner"] == "multi").sum())
    single_wins = int((sub["winner"] == "single").sum())
    ties = int((sub["winner"] == "TIE").sum())
    total = len(sub)
    decisive = multi_wins + single_wins

    label = metric.replace("_", " ").title()
    print(f"\n--- {label} ---")
    print(f"  Multi  勝利: {multi_wins:3d} / {total}  ({100*multi_wins/total:5.1f}%)")
    print(f"  Single 勝利: {single_wins:3d} / {total}  ({100*single_wins/total:5.1f}%)")
    print(f"  引き分け:    {ties:3d} / {total}  ({100*ties/total:5.1f}%)")

    if decisive > 0:
        win_rate = multi_wins / decisive
        print(f"  Multi 勝率（引き分け除外）: {win_rate:.3f}  ({multi_wins}/{decisive})")
        if has_scipy:
            result = binomtest(multi_wins, decisive, p=0.5, alternative="greater")
            p = result.pvalue
            sig = "★ p<0.05 有意" if p < 0.05 else ("† p<0.10 傾向" if p < 0.10 else "n.s.")
            print(f"  二項検定 p-value: {p:.4f}  {sig}")

    print(f"  カテゴリ別:")
    for cat in sorted(sub["category"].unique()):
        c = sub[sub["category"] == cat]
        mw = int((c["winner"] == "multi").sum())
        sw = int((c["winner"] == "single").sum())
        tw = int((c["winner"] == "TIE").sum())
        mark = "✅" if mw > sw else ("≈" if mw == sw else "🔴")
        print(f"    {cat:<28}: Multi={mw}  Single={sw}  Tie={tw}  {mark}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pairwise比較評価: Multi-Agent vs Single Agent"
    )
    parser.add_argument("--multi", required=True, help="Multi-Agent のベンチマークCSVパス")
    parser.add_argument("--single", required=True, help="Single Agent のベンチマークCSVパス")
    parser.add_argument("--model", default="gpt-4o", help="評価に使用するOpenAIモデル")
    parser.add_argument("--seed", type=int, default=42, help="A/B割り当てのランダムシード")
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key:
        print("エラー: OPENAI_API_KEY が設定されていません。")
        sys.exit(1)

    random.seed(args.seed)

    # --- データ読み込み ---
    df_multi = pd.read_csv(args.multi)
    df_multi["condition"] = df_multi["condition"].replace({"dynamic_filler": "multi_agent"})
    df_multi = df_multi[df_multi["condition"] == "multi_agent"].copy()

    df_all_single = pd.read_csv(args.single)
    df_single = df_all_single[df_all_single["condition"] == "single_agent"].copy()

    # --- カテゴリフィルタ ---
    df_multi = df_multi[~df_multi["category"].isin(EXCLUDE_CATEGORIES)]
    df_single = df_single[~df_single["category"].isin(EXCLUDE_CATEGORIES)]

    # --- dialogueルートのみに絞る（RAG応答はエージェント比較の対象外）---
    df_multi = df_multi[df_multi["route"] == "dialogue"].copy()
    df_single = df_single[df_single["route"] == "dialogue"].copy()

    # --- 有効な応答のみ ---
    df_multi = df_multi[df_multi["response_text"].notna() & (df_multi["response_text"] != "")]
    df_single = df_single[df_single["response_text"].notna() & (df_single["response_text"] != "")]

    # --- ペアマッチング（query + trial で結合）---
    pairs = []
    for _, m_row in df_multi.iterrows():
        query = m_row["query"]
        trial = int(m_row.get("trial", 1))

        # query + trial で厳密にマッチ
        match = df_single[
            (df_single["query"] == query) & (df_single["trial"] == trial)
        ]
        if len(match) == 0:
            continue

        s_row = match.iloc[0]
        pairs.append({
            "query": query,
            "category": str(m_row.get("category", "")),
            "trial": trial,
            "multi_response": str(m_row["response_text"]),
            "single_response": str(s_row["response_text"]),
        })

    total_pairs = len(pairs)
    print(f"入力 Multi  : {args.multi}")
    print(f"入力 Single : {args.single}")
    print(f"評価対象ペア数: {total_pairs}")
    print("-" * 60)

    if total_pairs == 0:
        print("マッチするペアがありません。queryカラムが一致しているか確認してください。")
        sys.exit(1)

    # --- Pairwise評価ループ ---
    results = []
    for i, pair in enumerate(pairs, 1):
        print(f"Evaluating {i}/{total_pairs} (trial={pair['trial']}, cat={pair['category']})...", end="\r")

        multi_is_a = random.random() < 0.5
        response_a = pair["multi_response"] if multi_is_a else pair["single_response"]
        response_b = pair["single_response"] if multi_is_a else pair["multi_response"]

        judgment = call_judge(api_key, pair["query"], response_a, response_b,
                              pair["category"], args.model)
        if judgment is None:
            continue

        for metric in ["specialization_depth", "domain_appropriateness"]:
            m_data = judgment.get(metric, {})
            raw_winner = m_data.get("winner", "TIE")
            reason = m_data.get("reason", "")
            actual_winner = resolve_winner(raw_winner, multi_is_a)

            results.append({
                "query": pair["query"],
                "category": pair["category"],
                "trial": pair["trial"],
                "metric": metric,
                "winner": actual_winner,
                "raw_winner_ab": raw_winner,
                "multi_is_a": multi_is_a,
                "reason": reason,
            })

        time.sleep(0.5)

    print()

    if not results:
        print("評価結果がありません。")
        sys.exit(1)

    df_results = pd.DataFrame(results)

    try:
        from scipy.stats import binomtest
        has_scipy = True
    except ImportError:
        has_scipy = False
        print("注意: scipy がないため二項検定はスキップされます。")

    # --- 結果表示 ---
    print("\n" + "=" * 60)
    print("【Pairwise比較 評価結果】")
    print("=" * 60)

    for metric in ["specialization_depth", "domain_appropriateness"]:
        print_metric_summary(df_results, metric, has_scipy)

    # --- CSV保存 ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.multi).parent / f"pairwise_{timestamp}.csv"
    df_results.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n結果保存先: {output_path}")


if __name__ == "__main__":
    main()
