import os
import sys
from pathlib import Path

# backend ディレクトリへのパスを追加して app モジュールをインポートできるようにする
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from app.models.model_registry import create_tts

def main():
    # =====================================================================
    # 📝 入力テキストの設定 (ここで合成したいテキストを指定してください)
    # =====================================================================
    text = "こんにちは。"
    # =====================================================================

    # モデルディレクトリの解決
    project_root = backend_dir
    default_tts_dir = project_root / "app" / "weights" / "tts" / "gakucho_ai_v2"
    
    # 環境変数 TTS_MODEL_DIR があればそれを使い、なければデフォルトのパスを使用
    tts_model_dir_str = os.getenv("TTS_MODEL_DIR", str(default_tts_dir))
    tts_model_dir = Path(tts_model_dir_str)

    if not tts_model_dir.exists():
        print(f"[エラー] TTSモデルディレクトリが見つかりません: {tts_model_dir}")
        print("正しいパスが設定されているか、またはモデルファイルが配置されているか確認してください。")
        return

    print(f"[INFO] モデル読み込み中: {tts_model_dir}")
    
    # 音声合成モデルの初期化
    try:
        tts = create_tts("style-bert-vits2", str(tts_model_dir))
    except Exception as e:
        print(f"[エラー] TTSモデルの読み込みに失敗しました: {e}")
        return

    # 出力パスの設定 (このスクリプトと同じディレクトリの output.wav)
    output_filename = "output.wav"
    output_path = Path(__file__).parent / output_filename

    print(f"\n[INFO] 音声を生成します...")
    print(f"テキスト: {text}")

    # 音声生成処理
    try:
        # StyleBertVITS2_TTS.generate() は同期的に呼び出され、ファイルに結果を書き出す
        saved_path = tts.generate(text, str(output_path))
        print(f"\n[成功] 音声ファイルが作成されました: {saved_path}")
    except Exception as e:
        print(f"\n[エラー] 音声生成中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
