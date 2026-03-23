'use client'

import React from 'react'
import Flex from '@/components/styles/Flex'
import Box from '@/components/styles/Box'

import {
  Lightbulb,
  GraduationCap,
  BookOpen,
  School,
  MessageCircle,
  TrendingUp,
  Sparkles,
} from 'lucide-react'

type Template = {
  id: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  title: string
  description: string
}

const TEMPLATES: Template[] = [
  {
    id: 'news',
    icon: Lightbulb,
    title: '最近のKITのニュース教えて！',
    description: '金沢工業大学の最新情報やイベントについて',
  },
  {
    id: 'research',
    icon: GraduationCap,
    title: '研究テーマについて相談したいです。',
    description: 'あなたの興味に合った研究分野を一緒に考えます',
  },
  {
    id: 'exam',
    icon: BookOpen,
    title: '推薦入試の対策を教えて！',
    description: '入試に関する情報とアドバイスを提供します',
  },
  {
    id: 'campus-life',
    icon: School,
    title: '大学生活をうまく進めるコツは？',
    description: '充実したキャンパスライフのヒント',
  },
  {
    id: 'strength',
    icon: MessageCircle,
    title: 'あなたの得意な分野は？',
    description: '学長AIができることをご紹介します',
  },
  {
    id: 'torend',
    icon: TrendingUp,
    title: '最近のAI技術のトレンドを教えて！',
    description: '最新のトレンドを調査します。',
  },
]

interface InitialChatViewProps {
  onTemplateClick: (text: string) => void
}

export function InitialChatView({ onTemplateClick }: InitialChatViewProps) {
  return (
    <Box
      $width="100%"
      $height="100%"
      $overflow="visible"
    >
      {/* Intro Card */}
      <Box
        $borderRadius="20px"
        $padding="20px"
        $backgroundColor="transparent"
        style={{
          position: 'relative',
          overflow: 'hidden',
          background:
            'linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.9) 100%)',
          boxShadow:
            '0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)',
          border: '1px solid rgba(59,130,246,0.15)',
          backdropFilter: 'blur(16px)',
        }}
      >
        {/* ノイズ */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            opacity: 0.04,
            mixBlendMode: 'overlay',
            pointerEvents: 'none',
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' /%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' /%3E%3C/svg%3E\")",
          }}
        />
        {/* 右上グロー */}
        <div
          style={{
            position: 'absolute',
            top: -80,
            right: -80,
            width: 160,
            height: 160,
            borderRadius: '999px',
            opacity: 0.25,
            background:
              'radial-gradient(circle, rgba(59,130,246,0.5) 0%, transparent 70%)',
            filter: 'blur(40px)',
          }}
        />

        <Flex $gap="16px" style={{ position: 'relative' }}>
          <Box
            $display="flex"
            $alignItems="center"
            $justifyContent="center"
            $borderRadius="16px"
            $width="56px"
            $height="56px"
            style={{
              background:
                'linear-gradient(145deg, rgba(59,130,246,0.25), rgba(37,99,235,0.1))',
              border: '1px solid rgba(59,130,246,0.4)',
            }}
          >
            <Sparkles width={28} height={28} color="#60a5fa" />
          </Box>

          <Flex $flex_direction="column" $gap="6px">
            <h2
              style={{
                fontSize: '1.4rem',
                fontWeight: 600,
                color: '#fff',
                letterSpacing: '0.02em',
              }}
            >
              ようこそ、学長AIへ
            </h2>
            <p
              style={{
                fontSize: '0.9rem',
                color: '#e5e7eb',
                lineHeight: 1.6,
              }}
            >
              金沢工業大学の学長AIは、あなたの質問に答え、学業・研究・進路に関する相談をサポートします。
              <br />
              自然な対話を通して、あなたの学びや活動をより充実させるお手伝いをします。
            </p>
          </Flex>
        </Flex>
      </Box>

      {/* テンプレート群 */}
      <Box $marginTop="20px" $padding="4px 4px 0">
        <p
          style={{
            fontSize: '0.8rem',
            color: '#cbd5f5',
            marginBottom: '10px',
          }}
        >
          よくある質問
        </p>

        <Flex
          $flex_direction="row"
          $flex_wrap="wrap"
          $gap="10px"
          style={{ width: '100%' }}
        >
          {TEMPLATES.map((tpl, index) => {
            const Icon = tpl.icon
            return (
              <button
                key={tpl.id}
                type="button"
                onClick={() => onTemplateClick(tpl.title)}
                className="gakucho-template-card"
                style={{
                  animationDelay: `${0.15 + index * 0.04}s`,
                }}
              >
                {/* 1. 全体を包むホバー時のボーダー・背景オーバーレイ */}
                <div className="hover-overlay" />

                {/* 2. 左上からのスポットライト効果 */}
                <div className="hover-spotlight" />

                {/* コンテンツ */}
                <div className="card-content">
                  <div className="icon-box">
                    <Icon className="icon-svg" width={18} height={18} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="card-title">{tpl.title}</div>
                    <div className="card-desc">{tpl.description}</div>
                  </div>
                </div>
              </button>
            )
          })}
        </Flex>
      </Box>

      <style jsx>{`
        /* 登場アニメーション */
        @keyframes initial-card-fade-in {
          from {
            opacity: 0;
            transform: translateY(12px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        /* カードのベーススタイル */
        .gakucho-template-card {
          position: relative;
          flex: 1 1 calc(50% - 10px);
          min-width: 0;
          border-radius: 18px;
          padding: 12px;
          text-align: left;
          background: rgba(15, 23, 42, 0.65);
          backdrop-filter: blur(12px);
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
          border: 1px solid rgba(148, 163, 184, 0.15);
          cursor: pointer;
          overflow: hidden; /* 光のはみ出しをカット */
          
          /* トランジション設定（ホバー時の動き） */
          transition: transform 0.3s ease, box-shadow 0.3s ease, background 0.3s ease;
          
          /* 初期状態 */
          opacity: 0;
          animation: initial-card-fade-in 0.4s ease forwards;
        }

        /* ホバー時のカード本体の変化（拡大） */
        .gakucho-template-card:hover {
          transform: translateY(-2px) scale(1.02);
          box-shadow: 0 10px 28px rgba(0, 0, 0, 0.4);
        }

        /* ----------------------------------
           内部要素のレイアウト
           ---------------------------------- */
        .card-content {
          position: relative;
          z-index: 10; /* 光の上に配置 */
          display: flex;
          align-items: flex-start;
          gap: 10px;
        }

        /* ----------------------------------
           1. ホバーオーバーレイ
           (Exemplarの inset-0 group-hover:opacity-100 部分)
           ---------------------------------- */
        .hover-overlay {
          position: absolute;
          inset: 0;
          background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, transparent 100%);
          border-radius: 18px;
          border: 1px solid rgba(59, 130, 246, 0.3);
          opacity: 0;
          transition: opacity 0.3s ease;
          pointer-events: none;
        }
        .gakucho-template-card:hover .hover-overlay {
          opacity: 1;
        }

        /* ----------------------------------
           2. スポットライト
           (Exemplarの -top-10 -left-10 radial-gradient 部分)
           ---------------------------------- */
        .hover-spotlight {
          position: absolute;
          top: -40px;
          left: -40px;
          width: 80px;
          height: 80px;
          border-radius: 999px;
          background: radial-gradient(circle, rgba(59, 130, 246, 0.6) 0%, transparent 70%);
          filter: blur(20px);
          opacity: 0;
          transition: opacity 0.3s ease;
          pointer-events: none;
        }
        .gakucho-template-card:hover .hover-spotlight {
          opacity: 0.3;
        }

        /* ----------------------------------
           アイコンのスタイル
           ---------------------------------- */
        .icon-box {
          width: 36px;
          height: 36px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(145deg, rgba(59,130,246,0.15), rgba(37,99,235,0.08));
          transition: background 0.3s ease;
        }
        /* ホバー時にアイコン背景を少し濃く */
        .gakucho-template-card:hover .icon-box {
          background: linear-gradient(145deg, rgba(59,130,246,0.25), rgba(37,99,235,0.15));
        }

        /* アイコンSVGの色制御 (global css等で干渉しないようclass付与推奨だが、ここではカスケード利用) */
        :global(.icon-svg) {
          color: #60a5fa; /* blue-400 */
          transition: color 0.3s ease;
        }
        .gakucho-template-card:hover :global(.icon-svg) {
          color: #93c5fd; /* blue-300 (明るく) */
        }

        /* ----------------------------------
           テキストのスタイル
           ---------------------------------- */
        .card-title {
          font-size: 0.86rem;
          font-weight: 500;
          color: #f9fafb;
          margin-bottom: 4px;
          transition: color 0.3s ease;
        }
        /* ホバー時にタイトルを少し青白く */
        .gakucho-template-card:hover .card-title {
          color: #eff6ff;
        }

        .card-desc {
          font-size: 0.76rem;
          color: #9ca3af;
          line-height: 1.5;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </Box>
  )
}