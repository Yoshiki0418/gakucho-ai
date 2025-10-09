'use client';
import styled from 'styled-components';
import React from 'react';

type StatusType = 'online' | 'offline' | 'busy';

type IconProps = {
  $variant?: 'symbol' | 'avatar';
  $icon?: React.ReactNode;
  $src?: string;
  $alt?: string;
  $name?: string;
  $status?: StatusType | false | null;
  $size?: number | string;
  $shape?: 'circle' | 'square';
  $backgroundColor?: string;
  $color?: string;
  $border?: string;
};

/* === 共通ラッパ === */
const IconWrapper = styled.div<{
  $size: number | string;
  $shape: 'circle' | 'square';
  $backgroundColor?: string;
  $border?: string;
}>`
  position: relative;
  width: ${({ $size }) =>
    typeof $size === 'number' ? `${$size}px` : $size};
  height: ${({ $size }) =>
    typeof $size === 'number' ? `${$size}px` : $size};
  border-radius: ${({ $shape }) => ($shape === 'circle' ? '50%' : '8px')};
  background-color: ${({ $backgroundColor }) => $backgroundColor || 'transparent'};
  border: ${({ $border }) => $border || 'none'};
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.2);
`;

/* === avatarモードの画像 === */
const AvatarImage = styled.img`
  width: 100%;
  height: 100%;
  object-fit: cover;
`;

/* === avatarモードのステータスドット === */
const StatusDot = styled.span<{ $status?: StatusType }>`
  position: absolute;
  bottom: 7px;
  right: 7px;
  transform: translate(25%, 25%);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  ${({ $status }) =>
    $status &&
    `
      background-color: ${
        $status === 'online'
          ? '#4CAF50'
          : $status === 'busy'
          ? '#FF9800'
          : '#9E9E9E'
      };
    `}
  border: 2px solid white;
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.2);
`;

/* === 本体コンポーネント === */
const Icon: React.FC<IconProps> = ({
  $variant = 'symbol',
  $icon,
  $src,
  $alt,
  $name,
  $status,
  $size = 40,
  $shape = 'circle',
  $backgroundColor,
  $color = '#000',
  $border,
}) => {
  const isStatusVisible =
    $status === 'online' || $status === 'offline' || $status === 'busy';

  return (
    <IconWrapper
      $size={$size}
      $shape={$shape}
      $backgroundColor={$backgroundColor}
      $border={$border}
    >
      {/* === avatarモード === */}
      {$variant === 'avatar' ? (
        <>
          {$src ? (
            <AvatarImage src={$src} alt={$alt || 'avatar'} />
          ) : (
            <span
              style={{
                color: $color,
                fontWeight: 'bold',
                fontSize:
                  typeof $size === 'number' ? $size * 0.4 : '1em',
              }}
            >
              {$name ? $name[0] : '?'}
            </span>
          )}
          {isStatusVisible && <StatusDot $status={$status} />}
        </>
      ) : (
        /* === symbolモード === */
        <span
          style={{
            fontSize:
              typeof $size === 'number' ? $size * 0.6 : '1.5em',
            color: $color,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {$icon}
        </span>
      )}
    </IconWrapper>
  );
};

export default Icon;
