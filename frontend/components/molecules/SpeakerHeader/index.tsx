import React from "react";
import { NameLabel } from "@/components/atoms/NameLabel";
import Icon from "@/components/atoms/Icon";
import Flex from "@/components/styles/Flex";

type SpeakerHeaderProps = {
  name: string;
  avatarSrc?: string;
  avatarAlt?: string;
  status?: "online" | "offline" | "busy" | false | null;
  color?: string;
  weight?: "normal" | "semibold" | "bold";
  suffix?: React.ReactNode;
  fontSize?: string;
  avatarSize?: number | string;
  width?: string;
};

export const SpeakerHeader: React.FC<SpeakerHeaderProps> = ({
  name,
  avatarSrc,
  avatarAlt = `${name}のアイコン`,
  status,
  color,
  weight,
  suffix,
  fontSize,
  avatarSize = 40,
  width,
}) => {
  return (
    <Flex $gap="12px" $alignItems="center" $width={width}>
      <Icon
        $variant="avatar"
        $src={avatarSrc}
        $alt={avatarAlt}
        $name={name}
        $status={status}
        $size={avatarSize}   
        $shape="circle"
      />
      <NameLabel
        name={name}
        color={color}
        weight={weight}
        suffix={suffix}
        fontSize={fontSize}
      />
    </Flex>
  );
};
