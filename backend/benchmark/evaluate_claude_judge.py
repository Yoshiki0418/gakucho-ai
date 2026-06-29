"""
Claude-as-a-Judge 評価スクリプト。
evaluate_main_quality.py と同一の評価基準・プロンプトを使い、
OpenAI ではなく Anthropic Claude を judge として使用する。

Usage:
    python -m benchmark.evaluate_claude_judge \
        --multi  data/benchmark_results/benchmark_20260608_114649.csv \
        --single data/benchmark_results/benchmark_single_agent_complete.csv \
        --model  claude-haiku-4-5
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("pandas がインストールされていません。")
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("anthropic がインストールされていません。")
    sys.exit(1)

# =========================================================
# 評価プロンプト（evaluate_main_quality.py と同一）
# =========================================================
DOMAIN_EXPECTATIONS = {
    "president_qa": (
        "学長の個人的な経験・価値観・研究背景に基づいた一人称の語りスタイル。"
        "単なる事実の羅列ではなく、人柄や哲学が滲み出る温かみのある応答が期待される。"
    ),
    "location_search": (
        "具体的な建物名・方向・所要時間を含む道案内スタイル。「だいたい歩いて〇分くらい」のような自然な表現。"
        "「1号館」を起点とした案内が期待される。抽象的な説明や「お調べください」のような回避は不適切。"
    ),
    "simple_chat": (
        "軽くテンポよい雑談スタイル。短く温かみのある応答。"
        "長い説明・専門的な内容は不要で、会話のキャッチボールができる自然さが期待される。"
    ),
    "complex_consult": (
        "人生相談・キャリア・生活設計に対するカウンセリングスタイル。"
        "「押し付けず選択肢を示す」姿勢で、具体的な一歩を提示しながらも断定を避ける語り口が期待される。"
        "医療・法律・投資の断定は不適切。"
    ),
    "multi_agent_tool": (
        "ツール（天気・時刻・周辺検索・経路案内）の結果を自然な会話に変換するスタイル。"
        "数値や専門用語をそのまま読み上げず「今日はだいぶ寒いみたいですよ」のように人間らしく解釈して伝える。"
        "ツール結果の機械的な列挙は不適切。"
    ),
    "cross_domain_complex": (
        "複数の観点（専門知識と個人見解、または複数ドメインの情報）を自然につなぎ合わせた統合的な応答。"
        "どちらかの観点が欠落していたり、話題間の接続が唐突にならないことが期待される。"
    ),
}

SYSTEM_PROMPT = """あなたはAI対話システムの品質評価を行う専門家です。
与えられたユーザーの発話（Query）、そのクエリが属するドメイン情報（Domain）、
システムが生成した回答（Main Response）を読み、以下の6つの観点から品質をそれぞれ1〜5の5段階で評価してください（5が最高）。

【システムに課されている厳格な制約事項】
1. 箇条書き（- や 1. など）・番号リスト・マークダウン記法を使わず、自然な対話風に回答すること。
2. 場所や経路を案内する際、起点は必ず「1号館」とすること。
3. 音声読み上げシステムのため、記号（% や °Cなど）は使わず、カタカナ（パーセント、度など）を使用すること。
※ URLの出力はシステム側で後処理されるため、評価対象外とすること。

【評価観点】

1. Instruction Following (制約遵守率)
- 上記の【システムに課されている厳格な制約事項】が遵守されているか。
- （5: 全て遵守されている, 3: 一部違反がある, 1: ルール違反が複数ある）
- 特に箇条書きの使用は重い減点対象。URLの有無は評価に含めないこと。

2. Persona Consistency (ペルソナ一貫性)
- このシステムは「金沢工業大学の大澤敏 学長」というペルソナを持っています。（丁寧な敬語、権威がありつつも親身、一人称は「私」）
- 学長としてのトーン＆マナーが保たれているか。機械的・無機質な回答になっていないか。
- （5: ペルソナに完全に一致, 3: ややズレがあるが許容範囲, 1: ペルソナ崩壊・馴れ馴れしい・機械的すぎるなど）

3. Task Success / Helpfulness (回答の正確性と有用性)
- ユーザーの質問に対して、必要な情報を漏らさず的確かつ自然に回答できているか。
- （5: 完璧な回答, 3: 情報は足りているが一部不自然または不足, 1: 質問の意図を外している・情報が全く足りない）

4. Specialization Depth (専門性深度) ※マルチエージェント有用性の評価指標
- 回答がそのドメインの専門家らしい具体性・深みを持っているか。
- 安全で無難な「一般論」に終始せず、ドメイン固有の知識や視点が感じられるか。
- （5: 明らかに専門家レベルの深みがある具体的な回答, 3: 合格点だが一般的すぎる, 1: 専門性が全くなく誰でも言える内容）
- ※形式（箇条書きか否か等）は評価しない。内容の深さのみを評価する。

5. Domain Appropriateness (ドメイン適合性) ※マルチエージェント有用性の評価指標
- 提供されたDomain情報と【期待される応答スタイル】に照らして、回答のトーン・アプローチ・内容の種類がそのドメインに適切か。
- 間違ったドメインのアプローチで回答していないか（例: 学長への質問に事実の羅列で答えるなど）。
- （5: ドメインに完全に適合したスタイル, 3: やや合っているが他ドメインのアプローチが混入, 1: 全くドメインに合っていない）
- ※形式（箇条書きか否か等）は評価しない。スタイルと内容の種類のみを評価する。

6. Response Precision (応答精度) ※マルチエージェント有用性の評価指標
- ユーザーが求めた情報だけに的を絞って回答できているか。求めていない余分な情報を不必要に追加していないか。
- （5: 質問に対してちょうどよい情報量で的確, 3: 求めていない情報が一部あるが許容範囲, 1: 過剰応答・的外れな付加情報が多い）
- ※形式（箇条書きか否か等）は評価しない。情報の的確さのみを評価する。

【出力形式】
必ず以下のJSONフォーマットのみを出力してください。
{
  "instruction_following": {"score": [1から5の整数], "rationale": "評価理由を1文で"},
  "persona_consistency": {"score": [1から5の整数], "rationale": "評価理由を1文で"},
  "task_success": {"score": [1から5の整数], "rationale": "評価理由を1文で"},
  "specialization_depth": {"score": [1から5の整数], "rationale": "評価理由を1文で"},
  "domain_appropriateness": {"score": [1から5の整数], "rationale": "評価理由を1文で"},
  "response_precision": {"score": [1から5の整数], "rationale": "評価理由を1文で"}
}
"""

EXCLUDE_CATEGORIES = {"rag_search", "greeting", "unclear_query", "emotional_query"}
METRICS = [
    "instruction_following",
    "persona_consistency",
    "task_success",
    "specialization_depth",
    "domain_appropriateness",
    "response_precision",
]

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def load_token() -> str:
    cred_path = Path.home() / ".claude" / ".credentials.json"
    if cred_path.exists():
        d = json.loads(cred_path.read_text())
        return d.get("claudeAiOauth", {}).get("accessToken", "")
    return ""


def evaluate_response(client: "anthropic.Anthropic", query: str, response: str,
                       category: str, model: str) -> dict:
    domain_hint = ""
    if category in DOMAIN_EXPECTATIONS:
        domain_hint = (
            f"\n\n【Domain】{category}\n"
            f"【期待される応答スタイル】{DOMAIN_EXPECTATIONS[category]}"
        )
    user_msg = f"【Query】\n{query}\n\n【Main Response】\n{response}{domain_hint}"

    for attempt in range(5):
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = msg.content[0].text
            m = _JSON_RE.search(raw)
            if m:
                return json.loads(m.group(0))
        except anthropic.RateLimitError:
            wait = 10 * (2 ** attempt)
            print(f"\n  [RateLimit] {wait}s 待機...", end="", flush=True)
            time.sleep(wait)
        except Exception as e:
            print(f"\n  [Error] {e}", end="", flush=True)
            if attempt == 4:
                break
            time.sleep(5)

    err = {"score": 0, "rationale": "Error"}
    return {m: err for m in METRICS}


def main():
    parser = argparse.ArgumentParser(description="Claude-as-a-Judge 絶対評価")
    parser.add_argument("--multi", required=True)
    parser.add_argument("--single", required=True)
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--sleep", type=float, default=4.0, help="APIコール間スリープ秒数")
    args = parser.parse_args()

    token = load_token()
    if not token:
        print("認証トークンが見つかりません。")
        sys.exit(1)

    client = anthropic.Anthropic(auth_token=token)

    # --- データ読み込み & フィルタ ---
    df_multi = pd.read_csv(args.multi)
    df_multi["condition"] = df_multi["condition"].replace({"dynamic_filler": "multi_agent"})
    df_multi = df_multi[df_multi["condition"] == "multi_agent"].copy()

    df_single = pd.read_csv(args.single)
    df_single = df_single[df_single["condition"] == "single_agent"].copy()

    combined = pd.concat([df_multi, df_single], ignore_index=True)
    combined = combined[~combined["category"].isin(EXCLUDE_CATEGORIES)].copy()

    # dialogueルートのみ
    combined = combined[combined["route"] == "dialogue"].copy()
    combined = combined[combined["response_text"].notna() & (combined["response_text"] != "")].copy()
    combined = combined.reset_index(drop=True)

    total = len(combined)
    print(f"評価対象: {total}件（dialogue-only, multi+single）")
    print(f"モデル: {args.model}")
    print("-" * 60)

    score_cols = {m: [] for m in METRICS}
    rationale_cols = {m: [] for m in METRICS}

    for i, (_, row) in enumerate(combined.iterrows(), 1):
        print(f"Evaluating {i}/{total} ({row['condition']}, {row['category']})...", end="\r")
        result = evaluate_response(
            client, str(row["query"]), str(row["response_text"]),
            str(row["category"]), args.model
        )
        for m in METRICS:
            score_cols[m].append(result.get(m, {}).get("score", 0))
            rationale_cols[m].append(result.get(m, {}).get("rationale", ""))
        time.sleep(args.sleep)

    print()

    for m in METRICS:
        combined[f"{m}_score"] = score_cols[m]
        combined[f"{m}_rationale"] = rationale_cols[m]

    # --- 結果集計 ---
    try:
        from scipy.stats import mannwhitneyu
        has_scipy = True
    except ImportError:
        has_scipy = False

    print("\n" + "=" * 65)
    print(f"【絶対評価スコア比較 (Claude judge: {args.model}, dialogueルート限定)】")
    print("=" * 65)

    METRIC_LABELS = {
        "instruction_following": "Instruction Following",
        "persona_consistency":   "Persona Consistency",
        "task_success":          "Task Success",
        "specialization_depth":  "Specialization Depth",
        "domain_appropriateness":"Domain Appropriateness",
        "response_precision":    "Response Precision",
    }

    for m, label in METRIC_LABELS.items():
        col = f"{m}_score"
        mdf = combined[combined["condition"] == "multi_agent"]
        sdf = combined[combined["condition"] == "single_agent"]
        mv = mdf[col].dropna(); mv = mv[mv > 0]
        sv = sdf[col].dropna(); sv = sv[sv > 0]

        diff = mv.mean() - sv.mean()
        sig = ""
        if has_scipy and len(mv) > 0 and len(sv) > 0:
            _, p = mannwhitneyu(mv, sv, alternative="greater")
            sig = f"p={p:.4f}  " + ("★★★" if p < 0.001 else "★★" if p < 0.01 else "★" if p < 0.05 else "n.s.")

        print(f"\n{label}")
        print(f"  Multi  (n={len(mv)}): {mv.mean():.2f}")
        print(f"  Single (n={len(sv)}): {sv.mean():.2f}")
        print(f"  差分: {diff:+.2f}  |  {sig}")

    # カテゴリ別 Specialization Depth
    print("\n\n【カテゴリ別 Specialization Depth】")
    for cat in sorted(combined["category"].unique()):
        cat_df = combined[combined["category"] == cat]
        mv = cat_df[cat_df["condition"] == "multi_agent"]["specialization_depth_score"]
        sv = cat_df[cat_df["condition"] == "single_agent"]["specialization_depth_score"]
        mv = mv[mv > 0].mean() if len(mv[mv > 0]) > 0 else float("nan")
        sv = sv[sv > 0].mean() if len(sv[sv > 0]) > 0 else float("nan")
        diff = mv - sv if not (mv != mv or sv != sv) else float("nan")
        print(f"  {cat:<28}: multi={mv:.2f}  single={sv:.2f}  diff={diff:+.2f}")

    # --- CSV保存 ---
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(args.multi).parent / f"claude_judge_{ts}.csv"
    combined.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n結果保存先: {out}")


if __name__ == "__main__":
    main()
