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
        self, user_id: str, text: str, history: list[dict] | None = None, mode: str = "general"
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
            mode=mode,
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
                    filler_stream = await self._generate_filler(text, history=history)
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

    async def _generate_filler(
        self, text: str, history: list[dict] | None = None
    ) -> AsyncIterator[str]:
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
                    history=history,
                    tool_calls=None,
                    temperature=0.3,
                ):
                    if piece:
                        yield piece
            except Exception as e:
                print(f"[ResponseOrchestrator] _generate_filler error: {e}")
                return

        return filler_stream()

    def _is_pure_greeting(self, text: str) -> bool:
        """挨拶だけの発話を検出（部分一致で判定）"""
        t = text.strip().rstrip("！!〜~。.、")
        greetings = [
            "おはよう",
            "おはようございます",
            "こんにちは",
            "こんばんは",
            "やあ",
            "はじめまして",
            "よろしくお願いします",
        ]
        return any(
            t == g or t.startswith(g) and len(t) <= len(g) + 3 for g in greetings
        )

    async def _start_filler_producer(
        self, text: str, history: list[dict] | None = None
    ) -> asyncio.Queue:
        """フィラー LLM のストリームをキューに流すプロデューサを起動"""
        queue: asyncio.Queue = asyncio.Queue()

        async def producer():
            try:
                if self._is_pure_greeting(text):
                    return
                async for piece in self.filler_llm.stream_generate(
                    message=text,
                    history=history,
                    tool_calls=None,
                    temperature=0.3,
                ):
                    if piece:
                        await queue.put(piece)
            except Exception as e:
                print(f"[ResponseOrchestrator] _start_filler_producer error: {e}")
                pass
            finally:
                await queue.put(None)  # 終了マーカー

        asyncio.create_task(producer())
        return queue

    async def _start_static_filler_producer(self, text: str) -> asyncio.Queue:
        """固定フィラー（ベースライン比較用）をキューに流すプロデューサを起動"""
        import random
        queue: asyncio.Queue = asyncio.Queue()

        async def producer():
            try:
                if self._is_pure_greeting(text):
                    return
                # 固定フィラーの候補
                static_fillers = [
                    "少々お待ちください。",
                    "確認いたしますね。",
                    "えーと、そうですね…",
                    "お調べしますので、少しお待ちください。"
                ]
                chosen = random.choice(static_fillers)
                
                # ストリーミングを模倣するために数文字ずつ出力
                chunk_size = 2
                for i in range(0, len(chosen), chunk_size):
                    await queue.put(chosen[i:i+chunk_size])
                    await asyncio.sleep(0.05) # 少しだけディレイを入れて自然に
            except Exception as e:
                print(f"[ResponseOrchestrator] _start_static_filler_producer error: {e}")
                pass
            finally:
                await queue.put(None)  # 終了マーカー

        asyncio.create_task(producer())
        return queue

    # --- 外部から呼ぶメイン入口 ---
    async def stream_response(
        self,
        user_id: str,
        text: str,
        history: list[dict] | None = None,
        mode: str = "general",
        filler_mode: str = "dynamic",
        timing_data: dict | None = None,
    ) -> AsyncIterator[str]:
        """
        FastAPI / SSE / WebSocket からはこのメソッドだけ利用。

        最適化パイプライン:
        - Classifier / Filler / Main を並列起動
        - Main の TTFB が timeout 以内なら → フィラーなしで Main を流す
        - Main が遅ければ → フィラーをストリーミングで即座に出力
        - フィラー出力後に Classifier 結果をチェックし RAG/dialogue を判定

        Args:
            filler_mode: "dynamic" (提案手法), "static" (固定音声比較用), "off" (フィラー無効化)
            timing_data: 計測結果を格納する辞書。呼び出し側が空の dict を渡すと
                         各種タイミング情報が書き込まれる。
        """
        start = time.perf_counter()
        sentence_end_chars = "。.!?！？"

        # --- タイミング計測の初期化 ---
        _td = timing_data if timing_data is not None else {}
        _td.update({
            "filler_mode": filler_mode,
            "filler_fired": False,
            "filler_text": "",
            "filler_ttfb_ms": None,
            "filler_duration_ms": None,
            "ttmr_ms": None,
            "classifier_ms": None,
            "route": None,
            "main_responded_in_time": None,
        })

        # =============================
        # 3つ同時起動
        # =============================
        classifier_task = asyncio.create_task(
            self.classifier_llm.classify_rag_vs_dialogue(text)
        )

        # フィラーをキュー経由でストリーミング（バックグラウンド開始）
        enable_filler = (filler_mode != "off") and (mode != "ceremony") and not self._is_pure_greeting(text)
        filler_queue = None
        if enable_filler:
            if filler_mode == "static":
                filler_queue = await self._start_static_filler_producer(text)
            else:
                filler_queue = await self._start_filler_producer(text, history=history)

        # Main を dialogue 前提で先行起動
        main_iter = self.daily_agent.stream_generate(
            user_id=user_id,
            message=text,
            history=history,
            mode=mode,
        ).__aiter__()
        main_first_task = asyncio.create_task(main_iter.__anext__())

        try:
            # =============================
            # ① Main の TTFB を timeout 付きで待つ
            # =============================
            done, _ = await asyncio.wait(
                {main_first_task},
                timeout=self.filler_timeout,
            )

            if main_first_task in done:
                # --- Main が時間内に応答 → フィラー不要 ---
                elapsed = (time.perf_counter() - start) * 1000
                _td["main_responded_in_time"] = True
                _td["ttmr_ms"] = elapsed
                print(
                    f"[ResponseOrchestrator] Main responded in {elapsed:.0f}ms, no filler needed"
                )

                # Classifier 結果を確認
                route = await classifier_task
                _td["classifier_ms"] = (time.perf_counter() - start) * 1000
                _td["route"] = route
                print(
                    f"[ResponseOrchestrator] route='{route}' in {(time.perf_counter() - start) * 1000:.0f}ms"
                )

                if route == "rag":
                    main_first_task.cancel()

                    # RAG処理は時間がかかるため、フィラーが使用可能なら出力する
                    if enable_filler and filler_queue is not None:
                        filler_text = ""
                        t_filler_start = time.perf_counter()
                        while True:
                            chunk = await filler_queue.get()
                            if chunk is None:
                                break
                            if not filler_text and chunk:
                                _td["filler_ttfb_ms"] = (time.perf_counter() - start) * 1000
                            yield chunk
                            filler_text += chunk
                            if any(c in chunk for c in sentence_end_chars):
                                break
                        if filler_text.strip():
                            _td["filler_fired"] = True
                            _td["filler_text"] = filler_text.strip()
                            _td["filler_duration_ms"] = (time.perf_counter() - t_filler_start) * 1000
                            elapsed = (time.perf_counter() - start) * 1000
                            print(
                                f"[ResponseOrchestrator] filler sent for RAG in {elapsed:.0f}ms: '{filler_text.strip()}'"
                            )

                    async for chunk in self.handle_rag(user_id, text, history=history):
                        yield chunk
                    return

                # dialogue → Main の応答を流す
                try:
                    first_chunk = main_first_task.result()
                except StopAsyncIteration:
                    return
                if first_chunk:
                    yield first_chunk
                async for chunk in main_iter:
                    if chunk:
                        yield chunk
                return

            # =============================
            # ② Main が遅い → フィラーをストリーミング出力
            #    ★ Classifier を待たない ★
            #    ★ 全文収集せず、チャンク単位で即 yield ★
            # =============================
            _td["main_responded_in_time"] = False
            filler_text = ""
            if enable_filler and filler_queue is not None:
                t_filler_start = time.perf_counter()
                while True:
                    chunk = await filler_queue.get()
                    if chunk is None:
                        break
                    if not filler_text and chunk:
                        _td["filler_ttfb_ms"] = (time.perf_counter() - start) * 1000
                    yield chunk
                    filler_text += chunk

                    # 1文完了したら打ち切り
                    if any(c in chunk for c in sentence_end_chars):
                        break

                if filler_text.strip():
                    _td["filler_fired"] = True
                    _td["filler_text"] = filler_text.strip()
                    _td["filler_duration_ms"] = (time.perf_counter() - t_filler_start) * 1000
                    elapsed = (time.perf_counter() - start) * 1000
                    print(
                        f"[ResponseOrchestrator] filler sent in {elapsed:.0f}ms: '{filler_text.strip()}'"
                    )

            # =============================
            # ③ フィラー出力後に Classifier を確認
            # =============================
            route = await classifier_task
            _td["classifier_ms"] = (time.perf_counter() - start) * 1000
            _td["route"] = route
            elapsed = (time.perf_counter() - start) * 1000
            print(f"[ResponseOrchestrator] route='{route}' in {elapsed:.0f}ms")

            if route == "rag":
                main_first_task.cancel()
                async for chunk in self.handle_rag(user_id, text, history=history):
                    yield chunk
                return

            # =============================
            # ④ dialogue → Main の応答を流す
            # =============================
            try:
                first_chunk = await main_first_task
            except StopAsyncIteration:
                return
            _td["ttmr_ms"] = (time.perf_counter() - start) * 1000
            if first_chunk:
                yield first_chunk
            async for chunk in main_iter:
                if chunk:
                    yield chunk

        finally:
            # --- cleanup ---
            if not classifier_task.done():
                classifier_task.cancel()
            if not main_first_task.done():
                main_first_task.cancel()
