'use client';
import React, { useEffect, useRef } from "react";
import Flex from "@/components/styles/Flex";
import { MessageItem } from "@/components/organisms/MessageItem";

type ChatMessage = {
  id: string;
  name?: string;
  text: string;
  avatarSrc?: string;
  role?: "user" | "assistant";
};

type ChatListProps = {
  messages: readonly ChatMessage[];
  width?: string;
  height?: string;
  autoScroll?: boolean;
};

export const ChatListStandard: React.FC<ChatListProps> = ({
  messages,
  width = "100%",
  height = "400px",
  autoScroll = true,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // 新しいメッセージが追加されたら最下部へ自動スクロール
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, autoScroll]);

  return (
    <Flex
      ref={scrollRef}
      $flex_direction="column"
      $width={width}
      $height={height}
      $gap="12px"
      $padding="16px"
      $overflow="auto"
      $backgroundColor="#2e2e2e"
      $borderRadius="12px"
      $boxShadow="0 4px 12px rgba(0, 0, 0, 0.3)"
    >
      {messages.map((msg, index) => {
        const prev = messages[index - 1];
        // 同じrole（発話者タイプ）が連続する場合はヘッダーを省略
        const hideHeader = prev?.role === msg.role;

        return (
          <MessageItem
            key={msg.id}
            name={msg.name}
            avatarSrc={msg.avatarSrc}
            text={msg.text}
            role={msg.role}
            hideHeader={hideHeader}
          />
        );
      })}
    </Flex>
  );
};
