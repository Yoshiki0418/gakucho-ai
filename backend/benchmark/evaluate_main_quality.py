import argparse
import csv
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("エラー: pandas がインストールされていません。'pip install pandas' を実行してください。")
    sys.exit(1)

# カテゴリ別に期待される応答スタイルの定義（domain_appropriatenessの評価基準）
DOMAIN_EXPECTATIONS = {
    "president_qa": (
        "学長個人の経験・価値観・思いを語る内省的・対話的なスタイル。"
        "「私は〜と感じています」のような一人称の語り口で、事実の羅列ではなく個人的な見解が滲み出る内容。"
        "ウェブ検索結果をそのまま読み上げる事実説明スタイルは不適切。"
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
  "instruction_following": {
    "score": [1から5の整数],
    "rationale": "評価の理由を1〜2文で記述"
  },
  "persona_consistency": {
    "score": [1から5の整数],
    "rationale": "評価の理由を1〜2文で記述"
  },
  "task_success": {
    "score": [1から5の整数],
    "rationale": "評価の理由を1〜2文で記述"
  },
  "specialization_depth": {
    "score": [1から5の整数],
    "rationale": "評価の理由を1〜2文で記述"
  },
  "domain_appropriateness": {
    "score": [1から5の整数],
    "rationale": "評価の理由を1〜2文で記述"
  },
  "response_precision": {
    "score": [1から5の整数],
    "rationale": "評価の理由を1〜2文で記述"
  }
}
"""


def evaluate_main_response(
    api_key: str,
    query: str,
    response: str,
    category: str = "",
    model: str = "gpt-4o",
) -> dict:
    """OpenAI API (REST) を呼び出してメイン応答を評価する"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    domain_hint = ""
    if category and category in DOMAIN_EXPECTATIONS:
        domain_hint = (
            f"\n\n【Domain】{category}\n"
            f"【期待される応答スタイル】{DOMAIN_EXPECTATIONS[category]}"
        )

    user_message = (
        f"【Query】\n{query}\n\n"
        f"【Main Response】\n{response}"
        + domain_hint
    )

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }

    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST"
    )

    ALL_METRICS = [
        "instruction_following",
        "persona_consistency",
        "task_success",
        "specialization_depth",
        "domain_appropriateness",
        "response_precision",
    ]

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"\nAPI Error: {e}")
                err_dict = {"score": 0, "rationale": f"Error: {e}"}
                return {m: err_dict for m in ALL_METRICS}
            time.sleep(2)


def compute_consistency(eval_df: "pd.DataFrame", score_col: str) -> "pd.DataFrame":
    """
    同一クエリ・同一条件の複数trial間でのスコア標準偏差を計算する。
    標準偏差が小さい = 一貫性が高い。
    """
    consistency = (
        eval_df.groupby(["condition", "query"])[score_col]
        .std(ddof=0)
        .reset_index()
        .rename(columns={score_col: "std"})
    )
    return consistency


def main():
    parser = argparse.ArgumentParser(
        description="LLM-as-a-Judge: 実験2 メイン応答品質の自動評価（6指標版）"
    )
    parser.add_argument("--input", required=True, help="評価対象のベンチマークCSVファイルのパス")
    parser.add_argument("--model", default="gpt-4o", help="評価に使用するOpenAIモデル")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("OPENAI_API_KEY="):
                        api_key = line.strip().split("=", 1)[1].strip('"\'')
                        break

    if not api_key:
        print("エラー: OPENAI_API_KEY が設定されていません。")
        sys.exit(1)

    try:
        df = pd.read_csv(args.input)
        # 過去のCSVデータ（dynamic_fillerラベル）との互換性のため置換
        df["condition"] = df["condition"].replace({"dynamic_filler": "multi_agent"})
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        sys.exit(1)

    # 1. 不要カテゴリの除外
    exclude_categories = ["rag_search", "greeting", "unclear_query", "emotional_query"]
    df_filtered = df[~df["category"].isin(exclude_categories)].copy()

    # 2. 対象条件の抽出
    target_conditions = ["multi_agent", "single_agent"]
    df_filtered = df_filtered[df_filtered["condition"].isin(target_conditions)].copy()

    # 3. RAGルートのペア除外
    df_filtered["pair_id"] = df_filtered["query"] + "_" + df_filtered["trial"].astype(str)
    rag_pair_ids = df_filtered[df_filtered["route"] == "rag"]["pair_id"].unique()
    eval_df = df_filtered[~df_filtered["pair_id"].isin(rag_pair_ids)].copy()

    # 4. 有効な回答があるもののみ
    eval_df = eval_df[eval_df["response_text"].notna() & (eval_df["response_text"] != "")].copy()

    total = len(eval_df)
    if total == 0:
        print("評価対象となるデータがありません。")
        sys.exit(0)

    print(f"入力ファイル: {args.input}")
    print(f"前処理前の総データ数: {len(df)}件")
    print(f"RAGペア除外等によるフィルタ後の評価対象データ数: {total}件")
    print("-" * 60)

    # LLMジャッジで評価する6指標
    llm_metrics = [
        "instruction_following",
        "persona_consistency",
        "task_success",
        "specialization_depth",
        "domain_appropriateness",
        "response_precision",
    ]
    results_dict = {f"{m}_score": [] for m in llm_metrics}
    results_dict.update({f"{m}_rationale": [] for m in llm_metrics})

    try:
        from tqdm import tqdm
        iterator = tqdm(eval_df.iterrows(), total=total, desc="Evaluating")
    except ImportError:
        def simple_iterator(df):
            for i, (idx, row) in enumerate(df.iterrows(), 1):
                print(f"Evaluating {i}/{total} ...", end="\r")
                yield idx, row
            print()
        iterator = simple_iterator(eval_df)

    for idx, row in iterator:
        query = str(row.get("query", ""))
        response = str(row.get("response_text", ""))
        category = str(row.get("category", ""))

        result = evaluate_main_response(api_key, query, response, category, args.model)

        for m in llm_metrics:
            results_dict[f"{m}_score"].append(result.get(m, {}).get("score", 0))
            results_dict[f"{m}_rationale"].append(result.get(m, {}).get("rationale", ""))

        time.sleep(3.0)

    for key, values in results_dict.items():
        eval_df[key] = values

    # =============================================
    # 一貫性スコア（Response Consistency）の計算
    # trial間のtask_successスコアの標準偏差。小さいほど一貫性が高い。
    # =============================================
    consistency_df = compute_consistency(eval_df, "task_success_score")
    consistency_by_condition = (
        consistency_df.groupby("condition")["std"].mean().rename("consistency_std_mean")
    )

    # 元のDFにマージして保存
    result_df = df.copy()
    for key in results_dict.keys():
        result_df[key] = None
    result_df.update(eval_df)

    input_path = Path(args.input)
    output_filename = f"{input_path.stem}_exp2_evaluated{input_path.suffix}"
    output_path = input_path.parent / output_filename
    result_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    # =============================================
    # サマリ出力
    # =============================================
    print("-" * 60)
    print("評価完了！")
    print(f"結果保存先: {output_path}")

    try:
        from scipy.stats import mannwhitneyu
        has_scipy = True
    except ImportError:
        has_scipy = False

    print("\n" + "=" * 60)
    print("【既存指標】")
    print("=" * 60)
    _print_metrics(eval_df, ["instruction_following", "persona_consistency", "task_success"], has_scipy)

    print("\n" + "=" * 60)
    print("【新規指標：マルチエージェント有用性】")
    print("=" * 60)
    _print_metrics(eval_df, ["specialization_depth", "domain_appropriateness", "response_precision"], has_scipy)

    print("\n" + "=" * 60)
    print("【一貫性スコア (Response Consistency)】")
    print("  ※ task_success の trial間標準偏差。小さいほど安定した回答")
    print("=" * 60)
    for cond in ["multi_agent", "single_agent"]:
        label = "Multi-Agent              " if cond == "multi_agent" else "Single Agent             "
        std_mean = consistency_by_condition.get(cond, float("nan"))
        print(f"  {label}: σ = {std_mean:.3f}")

    print("\n【カテゴリ別 Specialization Depth】")
    _print_by_category(eval_df, "specialization_depth_score")

    print("\n【カテゴリ別 Domain Appropriateness】")
    _print_by_category(eval_df, "domain_appropriateness_score")


def _print_metrics(eval_df: "pd.DataFrame", metrics: list, has_scipy: bool) -> None:
    try:
        from scipy.stats import mannwhitneyu
    except ImportError:
        has_scipy = False

    for m in metrics:
        col = f"{m}_score"
        name = m.replace("_", " ").title()
        print(f"\n--- {name} ---")

        dyn = eval_df[eval_df["condition"] == "multi_agent"][col].dropna()
        sta = eval_df[eval_df["condition"] == "single_agent"][col].dropna()
        dyn = dyn[dyn > 0]
        sta = sta[sta > 0]

        dyn_mean = dyn.mean() if not dyn.empty else 0
        sta_mean = sta.mean() if not sta.empty else 0

        print(f"  Multi-Agent                  (n={len(dyn)}): {dyn_mean:.2f} / 5.0")
        print(f"  Single Agent                 (n={len(sta)}): {sta_mean:.2f} / 5.0")

        if has_scipy and len(dyn) > 0 and len(sta) > 0:
            stat, p = mannwhitneyu(dyn, sta, alternative="greater")
            print(f"  U-test p-value (Multi > Single): {p:.3e} {'★ Significant!' if p < 0.05 else ''}")


def _print_by_category(eval_df: "pd.DataFrame", score_col: str) -> None:
    cats = sorted(eval_df["category"].dropna().unique())
    for cat in cats:
        sub = eval_df[eval_df["category"] == cat]
        dyn = sub[sub["condition"] == "multi_agent"][score_col].dropna()
        sta = sub[sub["condition"] == "single_agent"][score_col].dropna()
        dyn = dyn[dyn > 0]
        sta = sta[sta > 0]
        dm = dyn.mean() if not dyn.empty else 0
        sm = sta.mean() if not sta.empty else 0
        diff = dm - sm
        print(f"  {cat:<28} multi={dm:.2f}  single={sm:.2f}  diff={diff:+.2f}")


if __name__ == "__main__":
    main()
