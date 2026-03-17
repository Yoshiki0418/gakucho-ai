import json
import re
from typing import Optional, Sequence

from app.models.llm import OpenAILLM
from app.models.llm.base_llm import BaseLLM

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMDecisionClassifier:
    """
    最小構成の汎用LLM分類器。
    - 任意ラベル(2クラス以上OK)
    - プロンプトをインスタンス時/呼び出し時に差し替え可
    - 出力は {"label": "..."} のみを想定
    - Python側の戻り値は str (選択ラベル)
    """

    DEFAULT_SYSTEM_PROMPT = (
        "あなたはユーザー発話を与えられた候補ラベルの中から厳密に1つを選ぶ分類器です。"
        "出力はJSONのみで、追加テキストは返さないでください。"
    )

    DEFAULT_INSTRUCTION = (
        "以下の入力について、与えられたラベル集合から最も適切な1つだけを選びます。\n"
        "- 出力は **必ず** 次のJSON形式のみで返してください（説明文は不要）。\n"
        '  {"label": "<候補ラベルのいずれか>"}\n'
        "- label は候補に含まれる **ちょうど一つ** を厳密に返すこと。"
    )

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None,
        base_instruction: Optional[str] = None,
        temperature: float = 0.0,
        llm: Optional[BaseLLM] = None,
    ) -> None:
        if llm is not None:
            self.llm = llm
        else:
            self.llm = OpenAILLM(
                model_name=model_name,
                system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
            )
        self.base_instruction = base_instruction or self.DEFAULT_INSTRUCTION
        self.temperature = temperature

    async def classify(
        self,
        user_input: str,
        *,
        labels: Sequence[str],
        context_rules: Optional[str] = None,
        extra_guidance: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        任意のラベル集合で分類を実行し、選択ラベル(str)のみを返す。
        """
        prompt = self._build_prompt(
            user_input=user_input,
            labels=labels,
            context_rules=context_rules,
            extra_guidance=extra_guidance,
        )
        raw = await self.llm.generate(
            prompt,
            temperature=(self.temperature if temperature is None else temperature),
        )
        return self._parse_label(raw, labels)

    # 利便メソッド：RAG/Dialogue
    async def classify_rag_vs_dialogue(self, user_input: str) -> str:
        labels = ["rag", "dialogue"]
        rules = """
            あなたは金沢工業大学（KIT）内AIアシスタントです。
            ユーザーの質問に答えるために「KIT固有のデータベース（学内情報）」が必要かどうかを判断してください。

            ## 判断の最重要基準
            「この質問の答えは、KITの学内データベースを検索しなければ得られないか？」
            → YES → "rag"
            → NO（一般知識・LLM・Webで答えられる） → "dialogue"

            ## "rag" にすべき例（KIT固有データが必要）
            - 特定の教員・研究室・授業・学科・施設の情報（例：〇〇先生の研究室は？、食堂の営業時間は？）
            - 履修登録・奨学金・学内イベントなどのKIT独自のスケジュール・手続き
            - 研究テーマや就職先についてKITの学科・研究室と紐づけて相談したい場合
            - KITへのアクセス方法、学内システム（KITナビ、Moodle等）の使い方

            ## "dialogue" にすべき例（一般知識で答えられる）
            - 挨拶・雑談・感情的な会話（「こんにちは」「疲れた」「ありがとう」など）
            - 一般的なAI・技術・科学・社会のトレンドや知識（例：最近のAIのトレンドを教えて）
            - 数学・英語・プログラミングの一般的な質問（KIT固有でない）
            - KITとは無関係の天気・時事・娯楽・料理・スポーツなどの話題

            ## 判断に迷う場合のルール
            - このアシスタントはKITの学内専用です。ユーザーが「大学」「学校」「うちの大学」など特定の大学名を明示しない場合も、KITのことを指していると判断し "rag" とすること。
              （例：「大学にキャンパスはいくつある？」「学食はどこにある？」→ KITについての質問として "rag"）
            - 「KITの〇〇を教えて」のようにKITが明示されていれば当然 "rag"
            - KITや大学と全く無関係で、一般知識で十分に答えられる内容のみ "dialogue"
            - 「研究について相談したい」のように学業・学科がらみで文脈が不明瞭な場合は "rag"（学内相談として扱う）
            """
        return await self.classify(user_input, labels=labels, context_rules=rules)

    # 利便メソッド：簡単/複雑
    async def classify_complexity(self, user_input: str) -> str:
        labels = ["simple", "complex"]
        rules = (
            "### 判定方針\n"
            "次の観点で判断してください：\n"
            "1. **simple（単純）** に分類するのは次のような場合です。\n"
            "   - 一般知識・定義・概念説明・雑談・感想などで、外部情報を参照しなくても答えられる。\n"
            "   - モデル内部の常識的知識のみで1ターンで応答できる。\n"
            "   - 計算・天気・時間・要約・翻訳・検索・スケジュール・メール作成などの明確なツール呼び出しが不要。\n\n"
            "2. **complex（複雑）** に分類するのは次のような場合です。\n"
            "   - 現在のローカルLLM単体では対応できず、外部の知識・API・ツールを呼び出す必要がある。\n"
            "   - 天気、時間、検索、学内情報、スケジュール、要約、翻訳、データ計算、メール生成などを含む。\n"
            "   - 2段階以上の思考・条件分岐・依存関係（例：「〜なら〜して」や「まず〜して次に〜する」）がある。\n"
            "   - 複数の指示が含まれる（例：「要約して翻訳して」「調べて整理して説明して」など）。\n"
            "   - 外部ファイル・RAG・関数呼び出し・プラグイン実行が必要な処理を含む。\n\n"
            "### 注意事項\n"
            "- ローカルLLMが即時に答えられない情報（天気・時間・検索・要約・翻訳・計算など）が含まれていれば、必ず 'complex' とする。\n"
            "- 分類は必ず 'simple' または 'complex' のいずれか1語のみを出力すること。\n"
            "- 迷った場合は安全側（complex）に分類してください。\n\n"
        )
        return await self.classify(user_input, labels=labels, context_rules=rules)

    # ---------------- internal ----------------
    def _build_prompt(
        self,
        *,
        user_input: str,
        labels: Sequence[str],
        context_rules: Optional[str],
        extra_guidance: Optional[str],
    ) -> str:
        label_list = ", ".join(f'"{label}"' for label in labels)
        rules_block = f"\n### ルール/文脈\n{context_rules}\n" if context_rules else ""
        guidance_block = f"\n### 追加方針\n{extra_guidance}\n" if extra_guidance else ""
        return (
            f"{self.base_instruction}\n"
            f"### 候補ラベル\n[{label_list}]\n"
            f"{rules_block}"
            f"{guidance_block}"
            f"### 入力文\n{user_input}\n"
            f"### 出力形式\n"  # 確認用の雛形を末尾に置くと堅牢
            '{"label": "..."}'
        )

    def _parse_label(self, raw: str, labels: Sequence[str]) -> str:
        # JSONブロックを抽出して "label" を取得。失敗時はフォールバック。
        match = _JSON_BLOCK_RE.search(raw)
        if match:
            try:
                obj = json.loads(match.group(0))
                label = str(obj.get("label", "")).strip()
                if self._is_in_candidates(label, labels):
                    return self._normalize(label, labels)
            except Exception:
                pass
        # 非JSON応答だった場合のフォールバック（大文字小文字無視）
        lowered = raw.lower()
        for label in labels:
            if label.lower() in lowered:
                return label
        return labels[0] if labels else ""

    @staticmethod
    def _is_in_candidates(label: str, labels: Sequence[str]) -> bool:
        return label in labels or label.lower() in {
            label_candidate.lower() for label_candidate in labels
        }

    @staticmethod
    def _normalize(label: str, labels: Sequence[str]) -> str:
        for label_candidate in labels:
            if label.lower() == label_candidate.lower():
                return label_candidate
        return label


# テストコード
if __name__ == "__main__":
    import asyncio

    async def main():
        classifier = LLMDecisionClassifier()

        test_inputs = [
            "AIとは何ですか？",
            "PythonとJavaの違いを教えてください。",
            "今日の金沢の天気を教えてください。",
            "今何時ですか？",
            "金沢駅からKITまでの行き方を教えてください。",
            "研究テーマについて相談したいです。",
            "情報工学科でおすすめの研究室はありますか？",
            "こんにちは、今日はいい天気ですね。",
        ]

        print("=== Complexity Test ===")
        for input_text in test_inputs:
            label = await classifier.classify_complexity(input_text)
            print(f"[{label}] {input_text}")

        print("\n=== RAG vs Dialogue Test ===")
        for input_text in test_inputs:
            label = await classifier.classify_rag_vs_dialogue(input_text)
            print(f"[{label}] {input_text}")

    asyncio.run(main())
