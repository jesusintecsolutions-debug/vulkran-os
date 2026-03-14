import { AbsoluteFill, Img, interpolate, useCurrentFrame } from "remotion";
import type { TemplateComponentProps } from "../contracts/types";

export const ImageOverlay: React.FC<TemplateComponentProps> = ({ slots, width }) => {
  const frame = useCurrentFrame();
  const imageUrl = (slots.image_url as string) || "";
  const headline = (slots.headline as string) || "";
  const overlayOpacity = Number(slots.overlay_opacity) || 0.5;
  const position = (slots.text_position as string) || "bottom";

  const imgScale = interpolate(frame, [0, 90], [1, 1.05], { extrapolateRight: "clamp" });
  const textOpacity = interpolate(frame, [8, 20], [0, 1], { extrapolateRight: "clamp" });

  const positionStyle: React.CSSProperties =
    position === "top"
      ? { top: "10%", bottom: "auto" }
      : position === "center"
      ? { top: "50%", transform: "translateY(-50%)" }
      : { bottom: "10%", top: "auto" };

  return (
    <AbsoluteFill>
      {imageUrl && (
        <Img
          src={imageUrl}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${imgScale})`,
          }}
        />
      )}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundColor: `rgba(0, 0, 0, ${overlayOpacity})`,
        }}
      />
      {headline && (
        <div
          style={{
            position: "absolute",
            left: "8%",
            right: "8%",
            opacity: textOpacity,
            ...positionStyle,
          }}
        >
          <p
            style={{
              color: "#ffffff",
              fontSize: width > 1280 ? 48 : 32,
              fontWeight: 700,
              margin: 0,
              textShadow: "0 2px 20px rgba(0,0,0,0.5)",
            }}
          >
            {headline}
          </p>
        </div>
      )}
    </AbsoluteFill>
  );
};
