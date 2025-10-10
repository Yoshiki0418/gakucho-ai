'use client';
import React from "react";
import styled from "styled-components";
import Text from "@/components/atoms/Text";

type MessageContentProps = {
  text: string;
  role?: "user" | "assistant";
  maxWidth?: string;
  marginTop?: string;
  marginBottom?: string;
  marginLeft?: string;
  variant?: "plain" | "chat" | "livechat";
};

const Container = styled.div<Pick<MessageContentProps, "maxWidth" | "marginTop" | "marginBottom" | "marginLeft">>`
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  width: 100%;
  max-width: ${({ maxWidth }) => maxWidth || "90%"};
  margin-top: ${({ marginTop }) => marginTop || "4px"};
  margin-bottom: ${({ marginBottom }) => marginBottom || "0px"};
  margin-left: ${({ marginLeft }) => marginLeft || "0px"};
`;

export const MessageContent: React.FC<MessageContentProps> = ({
  text,
  role = "assistant",
  maxWidth,
  marginTop,
  marginBottom,
  marginLeft,
  variant = "plain",
}) => {
  return (
    <Container maxWidth={maxWidth} marginTop={marginTop} marginBottom={marginBottom} marginLeft={marginLeft}>
      <Text
        $variants={variant === "chat" ? "chat" : variant === "livechat" ? "livechat" : undefined}
        $isUser={role === "user"}
        $align="left"
        $fontSize="clamp(16px, 1.2vw, 20px)"
        $color={variant === "plain" ? "#f5f5f5" : undefined}
        style={{ whiteSpace: "pre-wrap" }}
      >
        {text}
      </Text>
    </Container>
  );
};
