import os
import sys

# 【デッドロック回避の設定】モデルの並行処理によるフリーズを防ぐ
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# backend ディレクトリにパスを通す
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

from dotenv import load_dotenv
import torch
# PyTorchのスレッド制限
torch.set_num_threads(1)

from app.rag.store import RAGStore

def main():
    # backend/.env から環境変数を読み込む（DB_URL等）
    load_dotenv()
    
    # プロジェクト直下の data/rag_documents.csv を絶対パスで指定
    project_root = os.path.dirname(backend_dir)
    csv_path = os.path.join(project_root, "data", "rag_documents.csv")
    
    if not os.path.exists(csv_path):
        print(f"❌ エラー: 指定されたCSVファイルが見つかりません: {csv_path}")
        sys.exit(1)
        
    db_url = os.environ.get("DB_URL")
    if not db_url:
        print("❌ エラー: .env ファイルに DB_URL の設定がありません。")
        sys.exit(1)
        
    print(f"🔌 PostgreSQL データベースに接続しています...")
    # RAGStoreの初期化
    store = RAGStore(db_url)
    
    try:
        print(f"📦 '{csv_path}' の読み込みとベクトル化(Embedding)を開始します。")
        print("※データ件数によってはGPU/CPUで数分〜十几分かかる場合があります...")
        
        # 実際にDBにインサートする処理（store.pyのinsert_from_csvを利用）
        result = store.insert_from_csv(csv_path)
        
        print("\n✨ === データの登録が完了しました！ === ✨")
        print(f"📥 新規追加: {result.get('inserted', 0)} 件")
        print(f"🔄 更新: {result.get('updated', 0)} 件")
        print(f"⏭️ スキップ: {result.get('skipped', 0)} 件 / サイズ超過: {result.get('skipped_index_limit', 0)} 件")
        
    except Exception as e:
        print(f"\n📛 エラーで中断しました: {e}")
    finally:
        store.close()
        print("🔒 データベース接続を閉じました。")

if __name__ == "__main__":
    main()
