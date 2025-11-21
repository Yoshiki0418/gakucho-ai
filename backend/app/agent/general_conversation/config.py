class GeneralConversationConfig:
    """
    instructions, MCPツール、function callツールなどの設定を保持するクラス。
    """

    def __init__(self):
        self.instructions = ""
        self.tools = []
        self.handoffs = []
