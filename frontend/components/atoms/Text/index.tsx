'use client'
import styled, { css } from "styled-components"

type TextProps = {
  $variants?: "title" | "subtitle" | "body" | "caption" | "chat" | "livechat";
  $color?: string;
  $align?: "left" | "center" | "right";
  $weight?: "normal" | "bold";
  $fontSize?: string;
  $width?: string;
  $height?: string;
  $padding?: string;
  $paddingTop?: string;
  $paddingRight?: string;
  $paddingLeft?: string;
  $paddingBottom?: string;
  $margin?: string;
  $marginTop?: string;
  $marginRight?: string;
  $marginLeft?: string;
  $marginBottom?: string;
  $fontFamily?: string;
  $fontWeight?: string;
  $letterSpacing?: string;
  $lineHeight?: string;
  $backgroundColor?: string;
  $borderRadius?: string;
  $isUser?: boolean; // チャットでユーザー側かどうか
  $username?: string; // コメント欄風にユーザー名を扱う場合
};

const Text = styled.p<TextProps>`
  ${({ $variants, theme, $isUser }) => {
    switch ($variants) {
      case "title":
        return css`
          font-size: ${theme.fontSize.flexible.ExtraLarge};
          line-height: clamp(2.28rem, calc(2.28rem + 1.72*((100vw - 23.4375rem) / 66.5625)), 4rem);
          width: 70%;
          letter-spacing: -0.03em;
          font-weight: 460;
          text-align: center;
        `;
      case "subtitle":
        return css`
          font-size: ${theme.fontSize.Large};
          letter-spacing: -0.03em;
        `;
      case "body":
        return css`
          font-size: ${theme.fontSize.Medium};
        `;
      case "caption":
        return css`
          font-size: ${theme.fontSize.Small};
          line-height: 1.25rem;
        `;
      case "chat":
        return css`
          font-size: ${theme.fontSize.Medium};
          max-width: 60%;
          padding: 0.75rem 1rem;
          border-radius: 12px;
          background-color: ${$isUser ? "#DCF8C6" : "#E9E9EB"};
          align-self: ${$isUser ? "flex-end" : "flex-start"};
          text-align: left;
          word-break: break-word;
        `;
      case "livechat":
        return css`
          font-size: ${theme.fontSize.Medium};
          color: ${$isUser ? "#4FC3F7" : "#F1F1F1"}; /* ユーザー: 青系, アシスタント: 白系 */
          background: transparent;
          display: flex;
          flex-direction: row;
          align-items: baseline;
          gap: 0.25rem;
          text-align: left;
          width: 100%;
          white-space: pre-wrap;
          word-break: break-word;
          font-weight: 400;
        `;
    }
  }};
  color: ${({ $color }) => $color};
  font-size: ${({ $fontSize }) => $fontSize};
  font-weight: ${({ $fontWeight }) => $fontWeight};
  letter-spacing: ${({ $letterSpacing }) => $letterSpacing};
  font-family: ${({ $fontFamily }) => $fontFamily};
  width: ${({ $width }) => $width};
  height: ${({ $height }) => $height};
  padding: ${({ $padding }) => $padding};
  padding-top: ${({ $paddingTop }) => $paddingTop};
  padding-right: ${({ $paddingRight }) => $paddingRight};
  padding-left: ${({ $paddingLeft }) => $paddingLeft};
  padding-bottom: ${({ $paddingBottom }) => $paddingBottom};
  margin: ${({ $margin }) => $margin};
  margin-top: ${({ $marginTop }) => $marginTop};
  margin-right: ${({ $marginRight }) => $marginRight};
  margin-left: ${({ $marginLeft }) => $marginLeft};
  margin-bottom: ${({ $marginBottom }) => $marginBottom};
  text-align: ${({ $align }) => $align || "left"};
  display: inline-block;
  line-height: ${({ $lineHeight }) => $lineHeight};
  background-color: ${({ $backgroundColor }) => $backgroundColor};
  border-radius: ${({ $borderRadius }) => $borderRadius};
`;

export default Text;
