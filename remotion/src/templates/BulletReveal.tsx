import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import type { TemplateComponentProps } from "../contracts/types";

export const BulletReveal: React.FC<TemplateComponentProps> = ({ slots, width, duration }) => {
  const frame = useCurrentFrame();
  const title = (slots.title as string) || "";
  const bullets = (slots.bullets as string[]) || [];
  const bgColor = (slots.bg_color as string) || "#1a1a2e";
  const accentColor = (slots.accent_color as string) || "#7c3aed";

  const titleOpacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const framesPerBullet = Math.floor((duration - 15) / Math.max(bullets.length, 1));

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, justifyContent: "center", padding: "8% 10%" }}>
      {title && (
        <h2
          style={{
            color: "#ffffff",
            fontSize: width > 1280 ? 42 : 28,
            fontWeight: 700,
            margin: "0 0 32px",
            opacity: titleOpacity,
          }}
        >
          {title}
        </h2>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {bullets.map((bullet, i) => {
          const startFrame = 12 + i * framesPerBullet;
          const opacity = interpolate(frame, [startFrame, startFrame + 10], [0, 1], { extrapolateRight: "clamp" });
          const x = interpolate(frame, [startFrame, startFrame + 10], [20, 0], { extrapolateRight: "clamp" });

          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 16,
                opacity,
                transform: `translateX(${x}px)`,
              }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  backgroundColor: accentColor,
                  marginTop: 10,
                  flexShrink: 0,
                }}
              />
              <p
                style={{
                  color: "#ffffff",
                  fontSize: width > 1280 ? 28 : 20,
                  fontWeight: 500,
                  margin: 0,
                  lineHeight: 1.4,
                }}
              >
                {bullet}
              </p>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
