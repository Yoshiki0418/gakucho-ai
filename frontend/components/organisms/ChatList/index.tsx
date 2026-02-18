'use client';
import React from 'react';
import { ChatListStandard } from './standard';
import { ChatListFuturistic } from './futuristic';

export type ChatMessage = {
  id: string;
  name?: string;
  text: string;
  avatarSrc?: string;
  role?: 'user' | 'assistant';
};

type ChatListProps = {
  messages: readonly ChatMessage[];
  width?: string;
  height?: string;
  autoScroll?: boolean;
  /** variant指定: "standard" | "futuristic" */
  variant?: 'standard' | 'futuristic';
  animateGlow?: boolean;
  speakingMessageId?: string | null;
};

export const ChatList: React.FC<ChatListProps> = ({
  variant = 'standard',
  ...props
}) => {
  switch (variant) {
    case 'futuristic':
      return <ChatListFuturistic {...props} />;
    default:
      return <ChatListStandard {...props} />;
  }
};