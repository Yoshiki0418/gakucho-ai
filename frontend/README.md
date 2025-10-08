## 🚀 プロジェクト概要

このリポジトリは、[`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app) で構築された **Next.js + TypeScript** プロジェクトです。
`app/layout.tsx` と `app/page.tsx` を中心とした **App Router構成** を採用し、スタイリングには **Tailwind CSS** を使用しています。

## 🧩 ディレクトリ構成
```
frontend/
├── app/                # ページ構成 (App Router)
├── components/         # 再利用可能なUIコンポーネント
├── features/           # 機能単位のモジュール（例: chat, audio）
├── lib/                # 共通ロジックや設定
├── styles/             # グローバルスタイル（Tailwind）
├── public/             # 静的ファイル（画像・音声など）
├── types/              # 型定義
├── package.json
├── tsconfig.json
├── next.config.js
└── README.md
```

## ⚙️ 環境構築手順

`.gitignore` により依存関係（`node_modules` や `.next`）はコミットされません。
そのため、各メンバーはローカル環境で依存関係をインストールする必要があります。

① 依存関係のインストール
```
npm install
```

② 開発サーバーの起動
```
npm run dev
```

ブラウザで http://localhost:3000
 を開くと、トップページが表示されます。

## 💡 開発メモ

* 環境変数：

`.env` ファイルはGit管理外です。
必要に応じて配布しますので、連絡してください。

* コード整形 / Lint：

`eslint.config.mjs` により、ESLintとPrettierが設定済みです。

* ビルド成果物：

`.next/` 以下に生成され、Gitでは無視されます。

他メンバーの更新を取得したとき：

```
npm install
```

を実行して依存関係を同期してください。

## 📚 参考資料

- [Next.js 公式ドキュメント](https://nextjs.org/docs)  
- [Tailwind CSS 公式ドキュメント](https://tailwindcss.com/docs)  
- [TypeScript ドキュメント](https://www.typescriptlang.org/docs/)  