# 開発とIssue・PR運用

## 作業の開始

- 新規タスクは対応するIssueを確認し、なければ作成する。重複を避け、目的・完了条件・依存関係を記載する。
- 追跡ファイルを変更する作業は、最新mainから `prefix/Issue番号/english-kebab-case` の専用ブランチを作る。原則として一実装Issueにつき一ブランチ・一PRとし、大きな作業は子Issueへ分割する。
- mainへ直接コミットせず、マージ済みブランチは再利用しない。並行作業は別worktreeを利用し、既存の未コミット変更を混在させない。
- 実験・調査・承認など、リポジトリ変更がない作業はIssueのみで管理する。空コミットや空PRは作らない。
- ローカル保管を依頼されたブランチは、ユーザーが許可するまでpushしない。PR作成・pushと、本番デプロイは別の操作として扱う。

## タイトル・分類

IssueとPRのタイトルは `prefix: タイトル` とする。接頭辞は `fix`, `hotfix`, `add`, `feat`, `update`, `change`, `clean`, `refactor`, `improve`, `disable`, `remove`, `delete`, `rename`, `move`, `upgrade`, `revert`, `docs`, `style`, `perf`, `test`, `chore` から選ぶ。

新機能は原則 `feat`、不具合は `fix`、文書は `docs`、研究実験・人手承認・既存コマンドによるデータ生成は `chore`。`test`はテストコードの追加・修正に使用する。

- GitHub Issue Type: 機能・テスト・動作設定の追加や改善は **Feature**、不具合修正は **Bug**、運用・文書のみ・親管理は **Task**。
- 種別ラベルは一つ: `type:implementation`（追跡ファイル変更）、`type:operation`（実行・確認）、`type:tracking`（親管理）。文書のみの変更はTaskと`type:implementation`を併用する。
- 優先度は一つ: `priority:P0`（赤・即時）、`priority:P1`（橙・次の重要作業）、`priority:P2`（黄・通常）、`priority:P3`（灰・将来候補）。着手可否とは区別する。
- 未完了Issueの状態は一つ: `status:todo`, `status:in-progress`, `status:blocked`, `status:review`。blockedには原因と解除条件を記載し、完了時は状態ラベルを外す。
- Issue本文・フォームと実際のラベルを一致させる。別リポジトリのIssueを共有方針だけを理由に一括変更しない。

## 検証とPR

- 変更に適したテスト、型チェック、lint等を実行し、結果と検証の限界をPRへ記載する。
- PRレビューとリポジトリの承認・保護ルールを経てmainへマージする。
- マージで完了する実装Issueのみ `Closes #番号` を使用する。運用Issue・親Issueは `Refs #番号` とし、実行結果・件数・保存先・残件を記録して手動closeする。
- 公開Issue・PRには秘密情報、生データ、画像、音声、対話本文、UID一覧を掲載しない。集計結果と管理場所を記録する。
- Issue作成を理由に、ユーザーの許可範囲を超える課金・削除・処理を開始しない。

## 共著の表記

CodexとYoshiki0418が共同で行った作業は、主著者を以下とする。

```text
YAMAMOTO YOSHIKI <145079668+Yoshiki0418@users.noreply.github.com>
```

コミット本文末尾の独立した段落に次を記載し、PR本文にも本人とCodexの共著を明記する。

```text
Co-authored-by: Codex <199175422+chatgpt-codex-connector[bot]@users.noreply.github.com>
```

squashマージ時も最終コミットに同じトレーラーを含め、GitHub上の著者を確認する。
