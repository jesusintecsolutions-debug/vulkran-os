/**
 * VULKRAN OS — MomentRenderer composition.
 *
 * Adapted from VideoFlow v2 TransitionSeries pattern.
 * Sequences moments with configurable transitions.
 */

import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  useVideoConfig,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import { flip } from "@remotion/transitions/flip";

import type { MomentProps, RenderInputProps } from "../contracts/types";
import { getTemplateComponent } from "../templates";

const TRANSITION_MAP: Record<string, (duration: number) => any> = {
  fade: (d) => fade({ exitTiming: linearTiming({ durationInFrames: d }) }),
  slide: (d) => slide({ direction: "from-right", exitTiming: linearTiming({ durationInFrames: d }) }),
  wipe: (d) => wipe({ direction: "from-right", exitTiming: linearTiming({ durationInFrames: d }) }),
  flip: (d) => flip({ direction: "from-right", exitTiming: linearTiming({ durationInFrames: d }) }),
};

const FallbackTemplate: React.FC<{ templateId: string }> = ({ templateId }) => (
  <AbsoluteFill
    style={{
      backgroundColor: "#1a1a2e",
      justifyContent: "center",
      alignItems: "center",
    }}
  >
    <p style={{ color: "#ef4444", fontSize: 24, fontWeight: 600 }}>
      Template not found: {templateId}
    </p>
  </AbsoluteFill>
);

export const MomentRenderer: React.FC<RenderInputProps> = ({
  moments,
  fps,
  width,
  height,
  audioSrc,
}) => {
  const { durationInFrames } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      <TransitionSeries>
        {moments.map((moment, i) => {
          const TemplateComponent = getTemplateComponent(moment.template_id);
          const transitionDuration = moment.transition_duration || 12;
          const getTransition = TRANSITION_MAP[moment.transition_type] || TRANSITION_MAP.fade;

          return (
            <React.Fragment key={moment.id || i}>
              <TransitionSeries.Sequence durationInFrames={moment.duration}>
                {TemplateComponent ? (
                  <TemplateComponent
                    slots={moment.slot_data}
                    width={width}
                    height={height}
                    duration={moment.duration}
                  />
                ) : (
                  <FallbackTemplate templateId={moment.template_id} />
                )}
                {moment.voiceover_url && (
                  <Audio src={moment.voiceover_url} />
                )}
              </TransitionSeries.Sequence>

              {i < moments.length - 1 && moment.transition_type !== "none" && (
                <TransitionSeries.Transition
                  presentation={getTransition(transitionDuration)}
                  timing={linearTiming({ durationInFrames: transitionDuration })}
                />
              )}
            </React.Fragment>
          );
        })}
      </TransitionSeries>

      {audioSrc && <Audio src={audioSrc} />}
    </AbsoluteFill>
  );
};
