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

# プロンプトの定義
SYSTEM_PROMPT = """あなたはAI対話システムの品質評価を行う専門家です。
与えられたユーザーの発話（Query）、システムが遅延隠蔽のために発話したフィラー/相槌（Filler）、そしてその後に続くシステムのメイン応答（Main Response）を読み、以下の4つの学術的な観点からフィラーの品質をそれぞれ1〜5の5段階で評価してください（5が最高）。

【評価観点】
1. Naturalness (自然さ)
- フィラーの発話自体が、人間同士の対話のように自然に感じられるか。機械的な不自然さがないか。
- （5: 人間として極めて自然, 3: 普通のシステム音声程度, 1: 非常に機械的で不自然）

2. Appropriateness (文脈的適切さ)
- ユーザーの発話意図（質問、相談など）に対して、選択されたフィラーの語彙（「えっと」「なるほど」「はい」など）が適切に呼応しているか。的はずれな相槌を打っていないか。
- （5: 意図を完璧に汲み取った適切な相槌, 3: 汎用的で無難な相槌, 1: 完全に的はずれな相槌）

3. Smoothness (対話の円滑さ / 接続性)
- フィラーからメインの応答への流れ（トランジション）に矛盾や唐突感がなく、論理的にスムーズに接続されているか。
- （5: 前後が完璧に接続されている, 3: 多少の違和感はあるが許容範囲, 1: フィラーとメイン応答で内容が矛盾・切断されている）

4. Persona Consistency (ペルソナ一貫性)
- このシステムは「大学の学長」というペルソナを持っています。（丁寧な敬語、少し権威がありつつも親身、一人称は「私」）
- このペルソナのトーン＆マナーにフィラーが合致しているか。
- （5: ペルソナに完全に一致, 3: ややズレがあるが許容範囲, 1: ペルソナ崩壊・馴れ馴れしいなど）

【出力形式】
必ず以下のJSONフォーマットのみを出力してください。
{
  "naturalness": {
    "score": [1から5の整数],
    "rationale": "評価の理由を1〜2文で記述"
  },
  "appropriateness": {
    "score": [1から5の整数],
    "rationale": "評価の理由を1〜2文で記述"
  },
  "smoothness": {
    "score": [1から5の整数],
    "rationale": "評価の理由を1〜2文で記述"
  },
  "persona_consistency": {
    "score": [1から5の整数],
    "rationale": "評価の理由を1〜2文で記述"
  }
}
"""

def evaluate_filler(api_key: str, query: str, filler: str, response: str, model: str = "gpt-4o") -> dict:
    """OpenAI API (REST) を呼び出してフィラーを評価する"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    user_message = (
        f"【Query】\n{query}\n\n"
        f"【Filler】\n{filler}\n\n"
        f"【Main Response】\n{response}"
    )
    
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    
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
                return {
                    "naturalness": err_dict,
                    "appropriateness": err_dict,
                    "smoothness": err_dict,
                    "persona_consistency": err_dict
                }
            time.sleep(2) # リトライ待機

def main():
    parser = argparse.ArgumentParser(description="LLM-as-a-Judge: フィラー品質の自動評価")
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
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        sys.exit(1)

    target_mask = (df["filler_fired"].astype(str).str.lower() == "true") & (df["filler_text"].notna()) & (df["filler_text"] != "")
    eval_df = df[target_mask].copy()
    
    total = len(eval_df)
    if total == 0:
        print("評価対象となるフィラー生成データがありません。")
        sys.exit(0)
        
    print(f"入力ファイル: {args.input}")
    print(f"評価対象データ数: {total}件")
    print("-" * 50)

    metrics = ["naturalness", "appropriateness", "smoothness", "persona_consistency"]
    results_dict = {f"{m}_score": [] for m in metrics}
    results_dict.update({f"{m}_rationale": [] for m in metrics})

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
        filler = str(row.get("filler_text", ""))
        response = str(row.get("response_text", ""))
        
        result = evaluate_filler(api_key, query, filler, response, args.model)
        
        for m in metrics:
            results_dict[f"{m}_score"].append(result.get(m, {}).get("score", 0))
            results_dict[f"{m}_rationale"].append(result.get(m, {}).get("rationale", ""))
        
        time.sleep(0.5)

    for key, values in results_dict.items():
        eval_df[key] = values

    result_df = df.copy()
    for key in results_dict.keys():
        result_df[key] = None
    
    result_df.update(eval_df)

    input_path = Path(args.input)
    output_filename = f"{input_path.stem}_evaluated{input_path.suffix}"
    output_path = input_path.parent / output_filename
    
    result_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print("-" * 50)
    print("評価完了！")
    print(f"結果保存先: {output_path}")
    print("\n【サマリ (Mean Scores)】")
    
    for m in metrics:
        valid_scores = eval_df[eval_df[f"{m}_score"] > 0][f"{m}_score"]
        avg = valid_scores.mean() if not valid_scores.empty else 0
        name = m.replace('_', ' ').title()
        print(f"{name:25s}: {avg:.2f} / 5.0")

if __name__ == "__main__":
    main()
