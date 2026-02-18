from datetime import datetime

from agents import function_tool


@function_tool
def get_current_time() -> str:
    """
    現在の日時時刻を「YYYY-MM-DD HH:MM:SS」形式で返します。
    """
    now = datetime.now()
    return now.strftime("%Y年%m月%d日 %H時%M分%S秒")
