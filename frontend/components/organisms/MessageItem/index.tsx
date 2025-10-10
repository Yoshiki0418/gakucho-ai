'use client';
import React from "react";
import Flex from "@/components/styles/Flex";
import { SpeakerHeader } from "@/components/molecules/SpeakerHeader";
import { MessageContent } from "@/components/molecules/MessageContent";

type MessageItemProps = {
  name: string;
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
  name,
  avatarSrc,
  status,
  nameColor,
  text,
  role = "assistant",
  variant = "plain",
  hideHeader = false,
  marginBottom = "24px",
}) => {
  return (
    <Flex
      $flex_direction="column"
      $gap="4px"
      $width="100%"
      $marginBottom={marginBottom}
    >
      {!hideHeader && (
        <SpeakerHeader
          name={name}
          avatarSrc={avatarSrc}
          status={status}
          color={nameColor}
        />
      )}

      <MessageContent
        text={text}
        role={role}
        variant={variant}
        marginTop="16px"
        marginLeft="20px"
      />
    </Flex>
  );
};
