'use client';
import React from "react";
import Box from "@/components/styles/Box";
import Text from "@/components/atoms/Text";

type MessageContentProps = {
  text: string;
  role?: "user" | "assistant";
  maxWidth?: string;
  $marginTop?: string;
  $marginBottom?: string;
  $marginLeft?: string;
  /** テキストスタイルバリアント */
  variant?: "plain" | "chat" | "livechat";
};

/**
 * 💬 MessageContent
 * 発話本文部分（吹き出し or シンプルテキスト）
 */
export const MessageContent: React.FC<MessageContentProps> = ({
  text,
  role = "assistant",
  maxWidth,
  $marginTop,
  $marginBottom,
  $marginLeft,
  variant = "plain",
}) => {
  return (
    <Box
      $display="flex"
      $justifyContent="flex-start"
      $width="100%"
      $maxWidth={maxWidth || "90%"}
      $marginTop={$marginTop || "4px"}
      $marginBottom={$marginBottom || "0px"}
      $marginLeft={$marginLeft || "0px"}
    >
      <Text
        $variants={
          variant === "chat"
            ? "chat"
            : variant === "livechat"
            ? "livechat"
            : undefined
        }
        $isUser={role === "user"}
        $align="left"
        $fontSize="clamp(16px, 1.2vw, 20px)"
        $color={variant === "plain" ? "#f5f5f5" : undefined}
        style={{ whiteSpace: "pre-wrap" }}
      >
        {text}
      </Text>
    </Box>
  );
};
