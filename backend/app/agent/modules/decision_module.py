import json
import re
from typing import Optional, Sequence

from app.models.llm import OpenAILLM

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
    ) -> None:
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
            あなたは金沢工業大学内AIアシスタントです。
            以下のユーザー発話が「学内情報」に関する質問かどうかを判定してください。

            ### 学内情報の例
            - 授業・講義・教員・学科・研究室・施設（例：図書館、学食、体育館）
            - イベント・スケジュール・履修登録・奨学金・学生支援・アクセス案内
            - 大学名（金沢工業大学、KIT）に関する話題
            - 学内システム（KITナビ、ポータル、Moodleなど）

            ### ルール
            - 上記のような「学内関連情報」を尋ねている場合は "rag"
            - 挨拶、雑談、感想、AIへの意見などは "dialogue"
            - 出力は "rag" または "dialogue" のどちらか一語のみ
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
        ]

        for input_text in test_inputs:
            label = await classifier.classify_complexity(input_text)
            print(f"Input: {input_text}\nClassified as: {label}\n")

    asyncio.run(main())
