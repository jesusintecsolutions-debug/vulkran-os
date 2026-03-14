import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import type { TemplateComponentProps } from "../contracts/types";

export const TextHighlight: React.FC<TemplateComponentProps> = ({ slots, width }) => {
  const frame = useCurrentFrame();
  const headline = (slots.headline as string) || "";
  const highlightWord = (slots.highlight_word as string) || "";
  const bgColor = (slots.bg_color as string) || "#0f0f23";
  const accentColor = (slots.accent_color as string) || "#7c3aed";

  const opacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const scale = interpolate(frame, [0, 12], [0.95, 1], { extrapolateRight: "clamp" });

  const renderText = () => {
    if (!highlightWord || !headline.includes(highlightWord)) {
      return <span>{headline}</span>;
    }
    const parts = headline.split(highlightWord);
    return (
      <>
        {parts[0]}
        <span style={{ color: accentColor, fontWeight: 900 }}>{highlightWord}</span>
        {parts.slice(1).join(highlightWord)}
      </>
    );
  };

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          opacity,
          transform: `scale(${scale})`,
          padding: "0 10%",
          textAlign: "center",
        }}
      >
        <p
          style={{
            color: "#ffffff",
            fontSize: width > 1280 ? 56 : 36,
            fontWeight: 700,
            lineHeight: 1.3,
            margin: 0,
          }}
        >
          {renderText()}
        </p>
      </div>
    </AbsoluteFill>
  );
};
