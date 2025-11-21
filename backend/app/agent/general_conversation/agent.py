class GeneralConversationAgent:
    """
    各ドメインエージェントへのルーティングを司るトップエージェント。
    """

    def __init__(self, config):
        self.config = config

    def run(self, user_input: str):
        # TODO: 後で詳細実装
        return "Router placeholder: " + user_input
