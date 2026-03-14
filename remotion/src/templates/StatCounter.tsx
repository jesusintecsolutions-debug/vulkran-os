import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import type { TemplateComponentProps } from "../contracts/types";

export const StatCounter: React.FC<TemplateComponentProps> = ({ slots, width, duration }) => {
  const frame = useCurrentFrame();
  const targetValue = Number(slots.value) || 0;
  const suffix = (slots.suffix as string) || "";
  const label = (slots.label as string) || "Metric";
  const bgColor = (slots.bg_color as string) || "#1a1a2e";
  const accentColor = (slots.accent_color as string) || "#10b981";

  const countUpEnd = Math.min(duration * 0.6, 45);
  const currentValue = Math.round(interpolate(frame, [0, countUpEnd], [0, targetValue], { extrapolateRight: "clamp" }));
  const opacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  const labelOpacity = interpolate(frame, [countUpEnd - 5, countUpEnd + 10], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, justifyContent: "center", alignItems: "center" }}>
      <div style={{ opacity, textAlign: "center" }}>
        <p
          style={{
            color: accentColor,
            fontSize: width > 1280 ? 120 : 80,
            fontWeight: 900,
            margin: 0,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {currentValue.toLocaleString()}{suffix}
        </p>
        <p
          style={{
            color: "#ffffff",
            opacity: labelOpacity * 0.7,
            fontSize: width > 1280 ? 28 : 20,
            fontWeight: 500,
            margin: "8px 0 0",
            textTransform: "uppercase",
            letterSpacing: 3,
          }}
        >
          {label}
        </p>
      </div>
    </AbsoluteFill>
  );
};
