'use client';
import React from "react";
import Flex from "@/components/styles/Flex";
import { SpeakerHeader } from "@/components/molecules/SpeakerHeader";
import { MessageContent } from "@/components/molecules/MessageContent";

type MessageItemProps = {
  name?: string;
  avatarSrc?: string;
  status?: "online" | "offline" | "busy" | false | null;
  nameColor?: string;
  text: string;
  role?: "user" | "assistant";
  variant?: "plain" | "chat" | "livechat";
  hideHeader?: boolean;
  marginBottom?: string;
};

export const MessageItem: React.FC<MessageItemProps> = ({
  avatarSrc,
  status,
  nameColor,
  text,
  role = "assistant",
  variant = "plain",
  hideHeader = false,
  marginBottom = "24px",
  name,
}) => {
  // role に応じてデフォルト設定を上書き
  const isAssistant = role === "assistant";
  const effectiveAvatar =
    avatarSrc || (isAssistant ? "/avatars/gakucho.png" : "/avatars/user.png");
  const backgroundColor = isAssistant ? "#D7CBBF" : "#D7CBBF";
  const effectiveColor =
    nameColor || (isAssistant ? "#10B981" : "#d4d4d8");
  const displayName = name || (isAssistant ? "大澤敏" : "あなた");

  return (
    <Flex
      $flex_direction="column"
      $gap="4px"
      $width="100%"
      $marginBottom={marginBottom}
    >
      {/* ヘッダー（話者名 + アバター） */}
      {!hideHeader && (
        <SpeakerHeader
          name={displayName}
          avatarSrc={effectiveAvatar}
          status={status}
          color={effectiveColor}
          backgroundColor={backgroundColor}
        />
      )}

      {/* 発話本文 */}
      <MessageContent
        text={text}
        role={role}
        variant={variant}
        $marginTop="16px"
        $marginLeft="20px"
      />
    </Flex>
  );
};
