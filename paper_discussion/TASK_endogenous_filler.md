# 実装指示書：親エージェントによる「自己判断フィラー（endogenous filler）」条件の追加

対象リポジトリ: `/gpu-server/yamamoto/gakucho-ai`（論文用の実験フィールド）
作成者: Claude（gakucho-ai-motion 側で先行実装した担当）
想定読者: gakucho-ai 側で作業する Claude（このリポジトリの事情は知らない前提で書いています）

---

## 0. このタスクの一言要約

これまでフィラー（つなぎ言葉）は**外部の専用LLMを並列に走らせて挿入**していた（外因的 / exogenous）。
本タスクでは、**親エージェント自身がツール実行・handoff の前に、文脈に応じて自分でつなぎ言葉を発話する**方式（内因的 / endogenous）を、**新しい実験条件として追加**する。

⚠️ 重要：これは**論文のための比較実験フィールド**です。既存のフィラー方式を消したり決め打ちで無効化したりせず、**条件として切り替え可能**にすること。最終的に最低でも次の条件を A/B 比較できる状態にするのがゴール：

- `none` … フィラーなし
- `external` … 既存の外部動的フィラー（並列LLM・タイムアウト方式）
- `static` … 既存の静的フィラー（`_start_static_filler_producer`）
- `endogenous` … ★今回追加★ 親エージェント自身が判断して出すフィラー

---

## 1. 背景と狙い（なぜこれをやるか）

- 現状の外部フィラーは「本応答の最初のトークンが `filler_timeout` 内に来なければフィラーを流す」というタイムアウト・ヒューリスティックで、別LLMが生成する。タイミングが外因的で、内容も会話文脈を渡し直すため汎用的になりがち。
- 一方、OpenAI Agents SDK では **handoff も検索/天気などのツールも「ツール呼び出し」**であり、モデルは**ツール呼び出しの前にテキストを出力できる**。
- そこで親エージェントに「ツール/handoff の直前に、まず短いつなぎ言葉を1文だけ喋ってから実行せよ」と指示すると、その文字列が `response.output_text.delta` として流れ、**モデル自身が必要なタイミングと内容を判断したフィラー**になる。
- 研究上の主眼は「**内因的フィラー vs 外因的フィラー**」の比較（自然さ・タイミング整合・遅延体感）。だから両方を残して切り替えられることが必須。

---

## 2. 先行（参照）実装：これを手本にする

同じ構造の姉妹リポジトリ `/gpu-server/yamamoto/gakucho-ai-motion` に、**動作確認済みの自己判断フィラー実装**がある。まず差分を読んで手本にすること（ただし motion 側は「決め打ちでオフ」にしている点だけは真似しない）。

参照ファイル（motion 側）:
1. `backend/app/agent/general_conversation/agent.py`
   - `general_agent` の instructions 末尾に `# [L] フィラー（つなぎ言葉）— 自己判断で出す` セクションを追加
   - `ceremony_agent` にも短いフィラー節を追加
2. `backend/app/agent/response_orchestrator.py`
   - `__init__` に `use_external_filler: bool` を追加し、`stream_response` の `enable_filler` 計算に組み込んで外部フィラーを止められるようにした
3. `backend/app/agent/agent_factory.py`
   - `ResponseOrchestrator(..., use_external_filler=False)` を渡している

確認コマンド例:
```bash
diff /gpu-server/yamamoto/gakucho-ai-motion/backend/app/agent/general_conversation/agent.py \
     /gpu-server/yamamoto/gakucho-ai/backend/app/agent/general_conversation/agent.py
```
※ 2リポジトリはもともと内容が異なる（motion はモーション生成 `generate_motion` ツールを持つが、gakucho-ai は持たない等）。**コピーではなく「同じ趣旨の編集を gakucho-ai の実コードに合わせて当てる」**こと。

---

## 3. gakucho-ai 側の現状（作業前に必ず自分で読むこと）

- 親エージェント: `backend/app/agent/general_conversation/agent.py`
  - `GeneralConversationAgent`（`general_agent` と `ceremony_agent` の2つ）。`model="gpt-5.2"`。
  - tools は `get_current_time, get_weather`（motion と違い `generate_motion` は無い）。`handoffs=[...]` で専門エージェントへ委譲。
- オーケストレータ: `backend/app/agent/response_orchestrator.py`
  - 外部動的フィラー（`_generate_filler` / `_start_filler_producer`）と**静的フィラー**（`_start_static_filler_producer`）の両方を既に持つ。
  - 公開入口は `stream_response(...)`。分類器（rag vs dialogue）・フィラー・本応答を並列起動してレースする構造。
- 生成器: `agent_factory.py: build_conversation_orchestrator()` が全部を組み立てて `ResponseOrchestrator(...)` を返す。
- 比較用: `backend/app/agent/baseline_agent.py`、`paper_discussion/` あり。

作業前チェックリスト:
- [ ] `agent.py` 全体を読む（instructions の節構成・tools・handoffs）
- [ ] `response_orchestrator.py` 全体を読む（特に `stream_response` の分岐、`enable_filler` の決め方、static/external フィラーの呼ばれ方）
- [ ] `agent_factory.py` を読む（何が orchestrator に渡されているか）
- [ ] 既に「フィラー方式を選ぶ仕組み（mode/flag/env）」が無いか grep で確認（`filler_mode` `MODE` `condition` 等）

---

## 4. 実装タスク

### 4-1. フィラー方式を「条件」として選べるようにする（最重要）

`FILLER_MODE` という設定値（`none` / `external` / `static` / `endogenous`）で挙動を切り替えられるようにする。実験で**コードを書き換えずに条件を変えられる**よう、環境変数で読むのを推奨：

```python
# agent_factory.py（例）
import os
FILLER_MODE = os.getenv("FILLER_MODE", "external")  # 既定は現行挙動（external）を維持
```

- 既定値は**現行の挙動を壊さない値**にすること（おそらく `external`）。
- `ResponseOrchestrator` にこのモードを渡す（例：`filler_mode: str = "external"`）。
- `stream_response` 内で、外部/静的フィラーのプロデューサ起動を `filler_mode` で分岐：
  - `external` → 既存の外部動的フィラーを使う
  - `static` → 既存の静的フィラーを使う
  - `none` / `endogenous` → **外部・静的フィラーは一切起動しない**（`enable_filler = False` 相当）。`endogenous` の場合はフィラーを親エージェント側に任せる。
- 分類器→RAG ルーティングなど、フィラー以外のロジックは**全モードで温存**すること。

実装ヒント：motion 側の `use_external_filler` を一般化した形。bool ではなく文字列 mode にして 4 値に対応させる。

### 4-2. 親エージェントに自己判断フィラーの指示を「条件付きで」入れる

`GeneralConversationAgent.__init__` に `endogenous_filler: bool = False` 引数を追加し、**True のときだけ** instructions にフィラー節を追記する（baseline/他条件の prompt を汚さないため）。

```python
class GeneralConversationAgent:
    def __init__(self, research_agent, life_planning_agent, location_agent,
                 endogenous_filler: bool = False):
        ...
        filler_block = ENDOGENOUS_FILLER_INSTRUCTION if endogenous_filler else ""
        self.general_agent = Agent(
            ...
            instructions=f"""...既存の instructions...
            {filler_block}
            """,
            ...
        )
```

`ENDOGENOUS_FILLER_INSTRUCTION`（gakucho-ai 用。`generate_motion` は無いのでツール列から外してある）:

```
# =========================================================
# [X] フィラー（つなぎ言葉）— 自己判断で出す ★実験条件: endogenous★
# =========================================================
ツール (get_weather / get_current_time) の実行や、専門エージェントへの handoff には
待ち時間が発生します。その「間（ま）」を埋めるため、以下を厳守してください。

【最重要の動作順序】
- 検索・天気・時刻などのツールを呼ぶ前、または handoff する前に、
  まず声に出すつなぎの一言を1文だけ出力してから、ツール/handoff を実行する。
  （テキストを出力 → そのあと同じターンでツール呼び出し/handoff、の順）

【つなぎの一言のルール】
- ユーザーの発話内容に軽く触れた、自然な口語の1文にする。
  例：
    - 天気ツール前 → 「天気ですね、ちょっと確認しますね。」
    - 調査/検索前 → 「なるほど、その点は少し調べてみますね。」
    - 学長本人の話へ handoff 前 → 「それはぜひお話ししたいですね、——」
- 結論・事実・数値・固有情報はこの一言に含めない（「受け止め」と「予告」のみ）。
- 「少々お待ちください」のような機械的な定型文は禁止。毎回表現を変える。
- ツールも handoff も使わず即答できる短い雑談・挨拶では、フィラーは不要。

【handoff 時の注意】
- handoff 前のつなぎは「橋渡し」の一言にとどめ、本題や結論には踏み込まない
  （続きは専門エージェントに委ねる）。
```

`ceremony_agent` にも、ツール待ち用の短い版を同様に条件付きで入れる。

### 4-3. 配線

`agent_factory.build_conversation_orchestrator()` で：
- `FILLER_MODE` を読む
- `GeneralConversationAgent(..., endogenous_filler=(FILLER_MODE == "endogenous"))` を渡す
- `ResponseOrchestrator(..., filler_mode=FILLER_MODE)` を渡す

### 4-4. 評価用ログ（論文のために重要）

最低限、各ターンについて構造化ログ（print でも logging でも可、後で集計できる形）を残す：
- `filler_mode`（その時の条件）
- 本応答の **time-to-first-token（TTFT/TTFB, ms）**
- フィラーとして出力された文字列（endogenous の場合は「最初のツール/handoff より前に出たテキスト」を切り出す。external/static は既存のフィラー文字列）
- そのターンで **ツール呼び出し / handoff が実際に発生したか**（endogenous フィラーが"空振り"していないかの指標）

※ endogenous で「ツール/handoff 前のテキスト」を切り出すには、`stream_generate`（`response_orchestrator` ではなく `general_conversation/agent.py` 側）で SDK のストリームイベントを見て、最初のツール呼び出しイベントの前に来た `output_text.delta` をフィラーとみなすのが素直。可能なら `agent.py` の `stream_generate` でツール呼び出し系イベント（handoff含む）も検知してログ用フックを足すとよい。難しければ最低限 TTFT とテキスト全文だけでも残す。

---

## 5. 検証手順（prod を再ビルドする前に devcontainer で確認）

このリポジトリは **devcontainer がソースを live mount している**ので、prod を焼き直さなくても dev 環境で確認できる：
- `gakucho-ai_devcontainer-backend-1` が `/gpu-server/yamamoto/gakucho-ai -> /workspace` をマウント済み。
- 一方 **prod（`gakucho-ai-backend-1`, project=`gakucho-ai`）はソース焼き込み**なので、本番反映には再ビルドが必要。

手順:
1. **構文チェック**（import 不要）:
   ```bash
   cd /gpu-server/yamamoto/gakucho-ai/backend
   python3 -m py_compile app/agent/general_conversation/agent.py \
     app/agent/response_orchestrator.py app/agent/agent_factory.py
   ```
2. **条件ごとに起動して挙動確認**：`FILLER_MODE` を変えて（`none`/`external`/`static`/`endogenous`）対話し、
   - `endogenous`：天気・検索・学長個人質問（handoff 誘発）を投げ、**ツール/handoff の直前に短いつなぎ言葉が先に出る**か。
   - `external`/`static`/`none`：従来通り動くか（デグレしていないか）。
3. **観察ポイント**（論文の論点になる）:
   - 第一声の速さ：`gpt-5.2` は推論モデルなので、フィラーも thinking 後にしか出ない。endogenous は「最初の音までの時間」を必ずしも縮めない可能性 → TTFT ログで確認。
   - フィラーの省略率（endogenous がフィラーを出さない割合）。
   - handoff 後の二重挨拶（親のフィラー＋専門エージェントの挨拶が重複していないか）。
4. **prod 反映が必要な場合のみ**、ユーザー承認を取ってから：
   ```bash
   docker compose --project-directory /gpu-server/yamamoto/gakucho-ai \
     -f /gpu-server/yamamoto/gakucho-ai/docker-compose.prod.yml build backend
   docker compose --project-directory /gpu-server/yamamoto/gakucho-ai \
     -f /gpu-server/yamamoto/gakucho-ai/docker-compose.prod.yml up -d backend
   ```
   ⚠️ prod の再ビルドは稼働中サービスを停止する。**勝手にやらず必ずユーザーに確認**すること。

---

## 6. やってはいけないこと / 落とし穴

- ❌ 既存の external / static フィラー経路を削除・破壊する（比較条件として必要）。
- ❌ `endogenous` を既定値にする（既定は現行挙動を維持）。
- ❌ baseline や他条件の prompt に endogenous フィラー指示を混ぜる（条件純度が崩れる。必ずフラグで分岐）。
- ❌ `gakucho-ai-motion`（"motion" 付き）のファイルを編集する。**今回の対象は `gakucho-ai`（"motion" なし）**。両者は別物なので混同しないこと。
- ❌ ユーザー承認なしの prod 再ビルド。
- ⚠️ 2リポジトリは内容が異なるので、motion のコードを丸コピペしない（特に `generate_motion` ツールは gakucho-ai には無い）。

---

## 7. 完了条件（Acceptance Criteria）

- [ ] `FILLER_MODE` で `none` / `external` / `static` / `endogenous` を切り替えられる（環境変数、既定は現行挙動）。
- [ ] `endogenous` で、親エージェントがツール/handoff の前に文脈依存のつなぎ言葉を1文出してから実行する。
- [ ] それ以外の条件は従来通り動作（デグレなし）。
- [ ] 各ターンの `filler_mode` / TTFT / フィラー文字列 / ツール・handoff 有無がログに残る。
- [ ] `py_compile` が通り、devcontainer で各条件の手動対話確認済み。
- [ ] 変更点と確認結果を簡潔に報告（prod 反映が要るかはユーザー判断に委ねる）。

---

## 補足：研究フレーミング（実装の意図理解のため）

主張は「LLMにフィラーを言わせたら自然」ではなく、
**「ツール拡張型マルチエージェントLLM対話において、フィラーの挿入タイミングと内容を**
**エージェントの行動方策(tool-use/handoff policy)の一部として内因的に決定する手法を、**
**外因的（タイムアウト）方式・静的方式・無フィラーと比較評価する」**。
このため「同一コードベースで条件だけを切り替えられる」ことが評価の前提になる。実装はその土台。
