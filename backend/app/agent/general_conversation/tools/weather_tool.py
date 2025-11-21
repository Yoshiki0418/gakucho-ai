from agents import function_tool


@function_tool
def get_weather(city: str) -> str:
    """
    指定都市の天気を返します（モック実装）。
    将来的には外部天気APIと連携することが想定されています。
    """
    # TODO: 実API呼び出し実装
    return f"{city} の現在の天気は “晴れ” です。"
