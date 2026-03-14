import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import type { TemplateComponentProps } from "../contracts/types";

export const CTACard: React.FC<TemplateComponentProps> = ({ slots, width }) => {
  const frame = useCurrentFrame();
  const headline = (slots.headline as string) || "Contact Us";
  const subtext = (slots.subtext as string) || "";
  const buttonText = (slots.button_text as string) || "Get Started";
  const bgColor = (slots.bg_color as string) || "#1a1a2e";
  const accentColor = (slots.accent_color as string) || "#7c3aed";
  const website = (slots.website as string) || "";

  const contentOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const contentY = interpolate(frame, [0, 15], [20, 0], { extrapolateRight: "clamp" });
  const buttonScale = interpolate(frame, [20, 30], [0, 1], { extrapolateRight: "clamp" });
  const buttonPulse = interpolate(frame, [35, 45, 55, 65], [1, 1.05, 1, 1.02], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          opacity: contentOpacity,
          transform: `translateY(${contentY}px)`,
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
        }}
      >
        <h1
          style={{
            color: "#ffffff",
            fontSize: width > 1280 ? 56 : 38,
            fontWeight: 800,
            margin: 0,
          }}
        >
          {headline}
        </h1>
        {subtext && (
          <p style={{ color: "rgba(255,255,255,0.7)", fontSize: width > 1280 ? 24 : 18, margin: 0, maxWidth: "60%" }}>
            {subtext}
          </p>
        )}
        <div
          style={{
            transform: `scale(${buttonScale * buttonPulse})`,
            marginTop: 8,
          }}
        >
          <div
            style={{
              backgroundColor: accentColor,
              color: "#ffffff",
              padding: "16px 48px",
              borderRadius: 12,
              fontSize: width > 1280 ? 24 : 18,
              fontWeight: 700,
              boxShadow: `0 4px 30px ${accentColor}40`,
            }}
          >
            {buttonText}
          </div>
        </div>
        {website && (
          <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 16, margin: "8px 0 0" }}>
            {website}
          </p>
        )}
      </div>
    </AbsoluteFill>
  );
};
