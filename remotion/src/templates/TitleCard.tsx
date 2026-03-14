import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import type { TemplateComponentProps } from "../contracts/types";

export const TitleCard: React.FC<TemplateComponentProps> = ({ slots, width, height, duration }) => {
  const frame = useCurrentFrame();
  const headline = (slots.headline as string) || "Title";
  const subtitle = (slots.subtitle as string) || "";
  const bgColor = (slots.bg_color as string) || "#1a1a2e";
  const accentColor = (slots.accent_color as string) || "#7c3aed";
  const textColor = (slots.text_color as string) || "#ffffff";

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [0, 15], [30, 0], { extrapolateRight: "clamp" });
  const subtitleOpacity = interpolate(frame, [10, 25], [0, 1], { extrapolateRight: "clamp" });
  const lineWidth = interpolate(frame, [5, 25], [0, 120], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
        }}
      >
        <h1
          style={{
            color: textColor,
            fontSize: width > 1280 ? 72 : 48,
            fontWeight: 800,
            textAlign: "center",
            margin: 0,
            lineHeight: 1.1,
            maxWidth: "80%",
          }}
        >
          {headline}
        </h1>
        <div
          style={{
            width: lineWidth,
            height: 4,
            backgroundColor: accentColor,
            borderRadius: 2,
          }}
        />
        {subtitle && (
          <p
            style={{
              color: textColor,
              opacity: subtitleOpacity * 0.7,
              fontSize: width > 1280 ? 28 : 20,
              fontWeight: 400,
              textAlign: "center",
              margin: 0,
              maxWidth: "70%",
            }}
          >
            {subtitle}
          </p>
        )}
      </div>
    </AbsoluteFill>
  );
};
