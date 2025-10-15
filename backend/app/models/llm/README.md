## 🧠 独自 LLM クラスの実装方法
`BaseLLM` は、すべての LLM モジュールの抽象基底クラスです。
新しい LLM モジュールを追加する場合は、このクラスを継承して以下のメソッドを実装してください。

#### 最低限実装が必要なメソッド
| メソッド名             | 概要                                 |
| ----------------- | ---------------------------------- |
| `build_context`   | ユーザー発話と履歴、システムコンテキストからプロンプトコンテキストを構築          |
| `_generate_impl`  | 実際にモデルを呼び出して応答テキストを生成              |
| `stream_generate` | ストリーミングでトークンや文チャンクを逐次返す（不要なら例外でOK） |

#### 📄 サンプル実装
以下は、ダミー応答を返す最小構成の例です👇

```
from typing import AsyncIterator, Dict, List, Optional
from .base_llm import BaseLLM

class DummyLLM(BaseLLM):
    def __init__(self):
        self._model_name = "dummy-llm"

    def build_context(self, message: str, system_prompt: str, history: List[Dict[str, str]], tool_calls=None):
        # シンプルにシステムプロンプトと履歴、現在のメッセージを連結
        context = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
        return context

    async def _generate_impl(self, message: str, history: List[Dict[str, str]], tool_calls=None) -> str:
        # 本来はモデル呼び出しを行うが、ここでは固定応答を返す
        return f"『{message}』に対するダミー応答です。"

    async def stream_generate(
        self,
        message: str,
        history: List[Dict[str, str]],
        tool_calls=None,
    ) -> AsyncIterator[str]:
        # 実際はモデルからのストリーミングを処理する
        for chunk in ["ダ", "ミ", "ー"]:
            yield chunk
```

#### 🧪 実装後はテストの追加を推奨
新しい LLM モジュールを実装したら、`tests/llm/` 以下に対応するテストファイルを作成することを推奨します。
テストを書くことで、モデルの入れ替えや API の変更があっても、安全に機能を拡張できます。

## 🚀 OpenAILLM の使い方

まず、環境変数 `OPENAI_API_KEY` を `backend/app/.env` ファイルに設定してください：

```.env
OPENAI_API_KEY=YOUR_API_KEY
```

> 📌 .env ファイルは .gitignore に設定しているので、各自でファイルを用意してください。

次に、以下の簡単なスクリプトで動作確認ができます👇

```
import asyncio
from app.models.llm.openai_llm import OpenAILLM

async def main():
    llm = OpenAILLM(model_name="gpt-4o")

    history = [
        {"role": "assistant", "content": "こんにちは、何かお困りですか？"},
        {"role": "user", "content": "学長先生、AI教育についてどう思いますか？"},
    ]

    response = await llm.generate(
        message="学生の創造力を育てるには何が大切ですか？",
        history=history,
        token_count=True,
    )
    print(response.content)
    print(f"(プロンプトトークン数: {response.prompt_tokens}, 完了トークン数: {response.completion_tokens})")

    # ストリーミングで受け取りたい場合
    # async for chunk in llm.stream_generate(message="...", history=history):
    #     print(chunk, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
```
