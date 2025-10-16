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

type ChatListFuturisticProps = {
  messages: readonly ChatMessage[];
  width?: string;
  height?: string;
  autoScroll?: boolean;
  animateGlow?: boolean;
  speakingMessageId?: string | null;
};

export const ChatListFuturistic: React.FC<ChatListFuturisticProps> = ({
  messages,
  width = "100%",
  height = "400px",
  autoScroll = true,
  animateGlow = true,
  speakingMessageId = null,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);

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
      $gap="14px"
      $padding="20px"
      $overflow="auto"
      $backgroundColor="rgba(20, 20, 25, 0.7)"
      $borderRadius="20px"
      $boxShadow="inset 0 1px 6px rgba(255,255,255,0.08), 0 6px 25px rgba(0,0,0,0.6)"
      style={{
        position: "relative",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(0,150,255,0.3)",
      }}
    >
      {messages.map((msg, index) => {
        const prev = messages[index - 1];
        const hideHeader = prev?.role === msg.role;
        const assistantClass = [
          msg.role === "assistant" && msg.id === speakingMessageId
            ? "assistant-glow"
            : "",
          msg.role === "assistant" && animateGlow ? "assistant-hover-glow" : "",
        ]
          .filter(Boolean)
          .join(" ");
        const userClass =
          msg.role === "user" && animateGlow ? "user-hover-glow" : "";

        return (
          <div
            key={msg.id}
            className={`${assistantClass} ${userClass}`}
            style={{
              background:
                msg.role === "user"
                  ? "linear-gradient(145deg, #181818, #222)"
                  : "linear-gradient(145deg, #0d1115, #151b22)",
              padding: "12px 16px",
              borderRadius: "14px",
              border:
                msg.role === "assistant"
                  ? "1px solid rgba(0,122,255,0.25)"
                  : "1px solid rgba(255,255,255,0.06)",
              backdropFilter: "blur(6px)",
              boxShadow:
                msg.role === "assistant"
                  ? "0 0 20px rgba(0,122,255,0.3)"
                  : "0 4px 10px rgba(0,0,0,0.3)",
              transition: "all 0.3s ease",
            }}
          >
            <MessageItem
              name={msg.name}
              avatarSrc={msg.avatarSrc}
              text={msg.text}
              role={msg.role}
              hideHeader={hideHeader}
            />
          </div>
        );
      })}

      {/* 光とエフェクト群 */}
      <style jsx global>{`
        /* アシスタント発話ゆらぎ */
        @keyframes assistantGlow {
          0% {
            box-shadow: 0 0 14px rgba(0, 122, 255, 0.15),
              0 0 25px rgba(0, 122, 255, 0.1);
          }
          50% {
            box-shadow: 0 0 22px rgba(0, 180, 255, 0.35),
              0 0 40px rgba(0, 122, 255, 0.25);
          }
          100% {
            box-shadow: 0 0 14px rgba(0, 122, 255, 0.15),
              0 0 25px rgba(0, 122, 255, 0.1);
          }
        }

        .assistant-glow {
          animation: assistantGlow 3s ease-in-out infinite;
        }

        /* アシスタント発話ホバー時 */
        .assistant-hover-glow:hover {
          transform: scale(1.02);
          box-shadow:
            0 0 25px rgba(0, 150, 255, 0.5),
            0 0 60px rgba(0, 180, 255, 0.25);
          border-color: rgba(0, 180, 255, 0.3);
        }

        /* ユーザー発話ホバー時 */
        .user-hover-glow:hover {
          transform: scale(1.02);
          box-shadow:
            0 0 25px rgba(255, 255, 255, 0.4),
            0 0 60px rgba(255, 255, 255, 0.15);
          border-color: rgba(255, 255, 255, 0.2);
        }

        /* 光るスクロールバー */
        ::-webkit-scrollbar {
          width: 6px;
        }
        ::-webkit-scrollbar-thumb {
          background: linear-gradient(180deg, #007aff, #00c6ff);
          border-radius: 3px;
          box-shadow: 0 0 8px rgba(0, 122, 255, 0.5);
        }
        ::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
        }
      `}</style>
    </Flex>
  );
};
