import React from "react";

type NameLabelWeight = "normal" | "semibold" | "bold";

type NameLabelProps = {
  name: string;
  color?: string;
  weight?: NameLabelWeight;
  suffix?: React.ReactNode;
  className?: string;
  fontSize?: string;
};

const weightClasses: Record<NameLabelWeight, string> = {
  normal: "font-normal",
  semibold: "font-semibold",
  bold: "font-bold",
};

export const NameLabel: React.FC<NameLabelProps> = ({
  name,
  color = "#f5f5f5",
  weight = "semibold",
  suffix,
  fontSize,
}) => {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`${weightClasses[weight]}`}
        style={{
          color,
          fontSize: fontSize ?? "clamp(20px, 1.7vw, 30px)", 
        }}
      >
        {name}
      </span>
      {suffix}
    </div>
  );
};
