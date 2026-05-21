import os
import sys

# 【デッドロック回避の設定】モデルの並行処理によるフリーズを防ぐ
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# backend ディレクトリにパスを通す
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

import torch
from dotenv import load_dotenv

# PyTorchのスレッド制限
torch.set_num_threads(1)

from app.rag.store import RAGStore


def main():
    # backend/.env から環境変数を読み込む（DB_URL等）
    load_dotenv()

    # プロジェクト直下の data/ にある対象CSVを絶対パスで指定
    project_root = os.path.dirname(backend_dir)
    data_dir = os.path.join(project_root, "data")
    csv_files = [
        "rag_documents.csv",
        "kit_main_rag_data.csv",
        "toranomon_rag_data.csv",
    ]
    csv_paths = [os.path.join(data_dir, name) for name in csv_files]

    missing = [p for p in csv_paths if not os.path.exists(p)]
    if missing:
        print("❌ エラー: 以下のCSVファイルが見つかりません:")
        for p in missing:
            print(f"  - {p}")
        sys.exit(1)

    db_url = os.environ.get("DB_URL")
    if not db_url:
        print("❌ エラー: .env ファイルに DB_URL の設定がありません。")
        sys.exit(1)

    print(f"🔌 PostgreSQL データベースに接続しています...")
    # RAGStoreの初期化
    store = RAGStore(db_url)

    totals = {"inserted": 0, "updated": 0, "skipped": 0, "skipped_index_limit": 0}

    try:
        for idx, csv_path in enumerate(csv_paths, start=1):
            print(f"\n=========================================")
            print(f"[{idx}/{len(csv_paths)}] 📦 '{csv_path}' の読み込みとベクトル化(Embedding)を開始します。")
            print("※データ件数によってはGPU/CPUで数分〜十数分かかる場合があります...")

            result = store.insert_from_csv(csv_path)

            for k in totals:
                totals[k] += result.get(k, 0)

            print(f"  📥 新規追加: {result.get('inserted', 0)} 件")
            print(f"  🔄 更新: {result.get('updated', 0)} 件")
            print(
                f"  ⏭️ スキップ: {result.get('skipped', 0)} 件 / サイズ超過: {result.get('skipped_index_limit', 0)} 件"
            )

        print("\n✨ === 全CSVの登録が完了しました！ === ✨")
        print(f"📥 新規追加 合計: {totals['inserted']} 件")
        print(f"🔄 更新 合計: {totals['updated']} 件")
        print(
            f"⏭️ スキップ 合計: {totals['skipped']} 件 / サイズ超過: {totals['skipped_index_limit']} 件"
        )

    except Exception as e:
        print(f"\n📛 エラーで中断しました: {e}")
    finally:
        store.close()
        print("🔒 データベース接続を閉じました。")


if __name__ == "__main__":
    main()
