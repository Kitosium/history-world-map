import type { HTMLAttributes } from "react";

export type IconName =
  | "search"
  | "check"
  | "sun"
  | "moon"
  | "plus"
  | "minus"
  | "layers"
  | "locate"
  | "play"
  | "pause"
  | "close"
  | "chevron"
  | "external"
  | "globe"
  | "info"
  | "arrow-left"
  | "arrow-right"
  | "sparkle"
  | "book"
  | "tag";

/**
 * Google Material Symbols Rounded, rendered through a locally hosted subset.
 * Codepoints come from the official Material Symbols Rounded font.
 */
const GLYPHS: Record<IconName, string> = {
  search: "\uEF7A",
  check: "\uE668",
  sun: "\uE518",
  moon: "\uE51C",
  plus: "\uE145",
  minus: "\uE15B",
  layers: "\uE53B",
  locate: "\uE87A",
  play: "\uE037",
  pause: "\uE034",
  close: "\uE5CD",
  chevron: "\uE5CF",
  external: "\uE89E",
  globe: "\uE80B",
  info: "\uE88E",
  "arrow-left": "\uE5C4",
  "arrow-right": "\uE5C8",
  sparkle: "\uE65F",
  book: "\uEA19",
  tag: "\uF05B"
};

interface IconProps extends Omit<HTMLAttributes<HTMLSpanElement>, "children"> {
  name: IconName;
  size?: number;
}

export function Icon({ name, size = 18, className = "", style, ...props }: IconProps) {
  return (
    <span
      {...props}
      aria-hidden
      className={`material-symbols-rounded shrink-0 ${className}`}
      style={{ fontSize: size, width: size, height: size, ...style }}
    >
      {GLYPHS[name]}
    </span>
  );
}

export function LogoMark({ size = 34 }: { size?: number }) {
  return <Icon name="globe" size={size} />;
}
