import asyncio
import time
from typing import AsyncIterator, Optional

from app.agent.general_conversation.agent import GeneralConversationAgent
from app.agent.modules.decision_module import LLMDecisionClassifier
from app.agent.modules.rag_module import RAGModule
from app.models.llm import BaseLLM


class ResponseOrchestrator:
    def __init__(
        self,
        rag_engine: RAGModule,  # RAG パイプライン
        daily_agent: GeneralConversationAgent,  # OpenAI Agent SDK の GeneralConversationAgent
        filler_llm: BaseLLM,  # フィラー用 LLM クライアント
        classifier_llm: LLMDecisionClassifier,  # 2値分類用 LLM
        filler_timeout: float = 1.0,  # 本応答の「最初のトークン待ち時間」
    ) -> None:
        self.rag_engine = rag_engine
        self.daily_agent = daily_agent
        self.filler_llm = filler_llm
        self.classifier_llm = classifier_llm
        self.filler_timeout = filler_timeout

    # --- RAG ルート処理 ---
    async def handle_rag(
        self, user_id: str, text: str, history: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """
        RAG はフィラーなし
        """
        async for chunk in self.rag_engine.run_stream(query=text):
            yield chunk

    # --- 日常対話 + フィラー ---
    async def handle_daily_with_filler(
        self, user_id: str, text: str, history: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """
        - 本応答(OpenAI Agent SDK)をストリーミング
        - self.filler_timeout 秒以内に main の最初のトークンが来なければ
        フィラーを「1回だけ・ストリーミングで」送る
        - フィラーが複数文ある場合は、1文目の句読点を返したタイミングで
        main の 1 トークン目が出ているか再チェックし、あればフィラーを打ち切る
        - その後は main を最後までそのまま流す
        """

        # --- メイン応答のストリーム ---
        main_iter = self.daily_agent.stream_generate(
            user_id=user_id,
            message=text,
            history=history,
        ).__aiter__()

        # --- 挨拶だけならフィラー不要 ---
        enable_filler = not self._is_pure_greeting(text)

        # フィラー用のキュー & プロデューサタスク
        filler_queue: Optional[asyncio.Queue[Optional[str]]] = None
        filler_producer_task: Optional[asyncio.Task] = None

        if enable_filler:
            filler_queue = asyncio.Queue()

            async def filler_producer() -> None:
                """
                _generate_filler が返す AsyncIterator[str] から
                チャンクを先読みしてキューに溜めておくタスク。
                """
                try:
                    filler_stream = await self._generate_filler(text)
                    async for chunk in filler_stream:
                        await filler_queue.put(chunk)
                finally:
                    # 終了を知らせる sentinel
                    await filler_queue.put(None)

            # フィラー生成をバックグラウンドで開始
            filler_producer_task = asyncio.create_task(filler_producer())

        # --- main の最初のトークンを取得するタスク ---
        main_first_task = asyncio.create_task(main_iter.__anext__())

        # 「文の終わり」とみなす句読点
        sentence_end_chars = "。.!?！？"

        try:
            # =============================
            # ① main の最初のトークンを timeout 付きで待つ
            # =============================
            done, _ = await asyncio.wait(
                {main_first_task},
                timeout=self.filler_timeout,
            )

            if main_first_task in done:
                # ---- 時間内に main の最初のトークンが来たケース ----
                try:
                    first_chunk = main_first_task.result()
                except StopAsyncIteration:
                    # main が 1 トークンも出さずに終わった
                    # → フィラーがあれば 1 回だけ流して終了
                    if enable_filler and filler_queue is not None:
                        while True:
                            chunk = await filler_queue.get()
                            if chunk is None:
                                break
                            if chunk:
                                yield chunk
                    return

                if first_chunk:
                    yield first_chunk

                # フィラーは不要になったのでキャンセル
                if filler_producer_task is not None and not filler_producer_task.done():
                    filler_producer_task.cancel()

                # main の残りをすべてストリーミング
                async for chunk in main_iter:
                    if chunk:
                        yield chunk
                return

            # =============================
            # ② timeout → フィラーを使うパス
            # =============================
            if not enable_filler or filler_queue is None:
                try:
                    first_chunk = await main_first_task
                except StopAsyncIteration:
                    return

                if first_chunk:
                    yield first_chunk

                async for chunk in main_iter:
                    if chunk:
                        yield chunk
                return

            # --- ここからフィラーを「1回だけ」ストリーミング ---
            saw_sentence_end = False

            while True:
                # 先読み済みフィラーの 1 チャンクを取得
                chunk = await filler_queue.get()
                if chunk is None:
                    # フィラー終了
                    break

                if chunk:
                    # フィラーをユーザーに返す
                    yield chunk

                    # まだ 1文目の区切りに到達しておらず、
                    # 今のチャンクに句読点が含まれていれば区切りとみなす
                    if not saw_sentence_end and any(
                        c in chunk for c in sentence_end_chars
                    ):
                        saw_sentence_end = True

                        # このタイミングで main の 1 トークン目が
                        # すでに用意できていれば、ここでフィラーを打ち切る
                        if main_first_task.done():
                            break

            # ここまでで「フィラーを一度だけ」流し終えた

            # =============================
            # ③ main の最初のトークンを取得して流す
            # =============================
            try:
                first_chunk = await main_first_task
            except StopAsyncIteration:
                # main が結局何も返さなかった場合は、フィラーだけで終了
                return

            if first_chunk:
                yield first_chunk

            # フィラーはここから先不要なのでキャンセル
            if filler_producer_task is not None and not filler_producer_task.done():
                filler_producer_task.cancel()

            # main の残りをすべてストリーミング
            async for chunk in main_iter:
                if chunk:
                    yield chunk

        finally:
            # --- cleanup ---
            if filler_producer_task is not None and not filler_producer_task.done():
                filler_producer_task.cancel()

    async def _run_producer(self, generator: AsyncIterator[str], queue: asyncio.Queue):
        """ジェネレータから読み出してキューに詰めるバックグラウンド処理"""
        try:
            async for item in generator:
                await queue.put(item)
            await queue.put(None)  # 終了を示す番兵
        except Exception:
            await queue.put(None)  # エラー時も終了させる

    def _is_punctuation(self, text: str) -> bool:
        """句読点が含まれているか判定"""
        return any(p in text for p in ["、", "。", "！", "？", "\n"])

    async def _generate_filler(self, text: str) -> AsyncIterator[str]:
        """
        フィラーをストリーミングで返すジェネレータ。
        """

        # 挨拶ならフィラーなし → 空のジェネレータ
        if self._is_pure_greeting(text):

            async def empty_stream():
                if False:
                    yield ""

            return empty_stream()

        # フィラー生成
        async def filler_stream():
            try:
                async for piece in self.filler_llm.stream_generate(
                    message=text,
                    history=None,
                    tool_calls=None,
                    max_tokens=80,
                    temperature=0.3,
                ):
                    if piece:
                        yield piece
            except Exception:
                # エラー時は空ストリーム
                return

        return filler_stream()

    def _is_pure_greeting(self, text: str) -> bool:
        # 「おはよう」「こんにちは」「こんばんは」、とかを検出する簡単なルール
        t = text.strip()
        greetings = [
            "おはよう",
            "おはようございます",
            "こんにちは",
            "こんばんは",
            "やあ",
        ]
        return any(t == g for g in greetings)

    # --- 外部から呼ぶメイン入口 ---
    async def stream_response(
        self, user_id: str, text: str, history: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """
        FastAPI / SSE / WebSocket からはこのメソッドだけ利用
        """
        start = time.perf_counter()
        route = await self.classifier_llm.classify_rag_vs_dialogue(text)
        elapsed = (time.perf_counter() - start) * 1000
        print(
            f"[ResponseOrchestrator] route classified as '{route}' in {elapsed:.2f} ms"
        )

        if route == "rag":
            async for chunk in self.handle_rag(user_id, text, history=history):
                yield chunk
        else:
            # async for chunk in self.handle_daily_with_filler(user_id, text, history=history):
            #     yield chunk
            async for chunk in self.daily_agent.stream_generate(
                user_id=user_id,
                message=text,
                history=history,
            ):
                yield chunk
