import asyncio
import time
import os
import sys

# プロジェクトルートにパスを通す
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.agent_factory import build_conversation_orchestrator

async def main():
    print("--- フィラー速度テスト (gpt-4o-mini) ---")
    print("初期化中...")
    orchestrator = build_conversation_orchestrator()
    
    # テストするクエリ（わざとRAG検索が必要で時間のかかるもの）
    query = "金沢工業大学の入試日程と、図書館の開館時間を教えてください。"
    print(f"\n質問: {query}")
    
    start_time = time.time()
    first_token_time = None
    
    print("\n[応答ストリーム開始]")
    try:
        # mode="multi_agent" で提案手法（フィラー並列生成）を実行
        async for chunk in orchestrator.stream_response(user_id="test_user", text=query, history=[], mode="multi_agent"):
            if first_token_time is None:
                first_token_time = time.time()
                ttft = (first_token_time - start_time) * 1000
                print(f"\n\n>>> 最初のトークン到着！ (TTFT: {ttft:.1f} ms) <<<\n")
            
            # ストリーム出力
            print(chunk, end="", flush=True)
            
    except Exception as e:
        print(f"\nエラー発生: {e}")
        return

    end_time = time.time()
    total_time = (end_time - start_time) * 1000
    
    print(f"\n\n[ストリーム完了]")
    print("-" * 40)
    print(f"TTFT (体感応答時間): {ttft:.1f} ms")
    print(f"合計処理時間: {total_time:.1f} ms")
    print("-" * 40)
    print("※ フィラーが gpt-4o-mini に変更されたことで、TTFTが1,000ms前後に収まっているか確認してください！")

if __name__ == "__main__":
    asyncio.run(main())
