import { Composition } from "remotion";
import { z } from "zod";
import { MomentRenderer } from "./compositions/MomentRenderer";

const momentSchema = z.object({
  id: z.string(),
  template_id: z.string(),
  slot_data: z.record(z.unknown()),
  duration: z.number(),
  transition_type: z.string().default("fade"),
  transition_duration: z.number().default(12),
  voiceover_url: z.string().optional(),
});

const renderInputSchema = z.object({
  moments: z.array(momentSchema),
  fps: z.number().default(30),
  width: z.number().default(1920),
  height: z.number().default(1080),
  audioSrc: z.string().optional(),
});

const DEFAULT_MOMENTS = [
  {
    id: "1",
    template_id: "title_card",
    slot_data: {
      headline: "VULKRAN OS",
      subtitle: "Business Operating System",
      accent_color: "#7c3aed",
    },
    duration: 120,
    transition_type: "fade",
    transition_duration: 12,
  },
  {
    id: "2",
    template_id: "text_highlight",
    slot_data: {
      headline: "AI-Powered Content Engine",
      highlight_word: "AI-Powered",
    },
    duration: 90,
    transition_type: "slide",
    transition_duration: 12,
  },
  {
    id: "3",
    template_id: "stat_counter",
    slot_data: { value: 50, suffix: "+", label: "Agent Tools" },
    duration: 90,
    transition_type: "fade",
    transition_duration: 12,
  },
  {
    id: "4",
    template_id: "cta_card",
    slot_data: {
      headline: "Transform Your Business",
      button_text: "Get Started",
      website: "vulkran.es",
    },
    duration: 120,
    transition_type: "wipe",
    transition_duration: 12,
  },
];

function calculateDuration(moments: typeof DEFAULT_MOMENTS): number {
  return moments.reduce((total, m, i) => {
    const dur = m.duration;
    const overlap = i < moments.length - 1 ? m.transition_duration : 0;
    return total + dur - overlap;
  }, 0);
}

export const RemotionRoot: React.FC = () => {
  const totalFrames = calculateDuration(DEFAULT_MOMENTS);

  return (
    <>
      <Composition
        id="MomentRenderer"
        component={MomentRenderer}
        durationInFrames={totalFrames}
        fps={30}
        width={1920}
        height={1080}
        schema={renderInputSchema}
        defaultProps={{
          moments: DEFAULT_MOMENTS,
          fps: 30,
          width: 1920,
          height: 1080,
        }}
        calculateMetadata={({ props }) => {
          const dur = calculateDuration(props.moments);
          return {
            durationInFrames: dur,
            fps: props.fps,
            width: props.width,
            height: props.height,
          };
        }}
      />
      <Composition
        id="MomentRendererVertical"
        component={MomentRenderer}
        durationInFrames={totalFrames}
        fps={30}
        width={1080}
        height={1920}
        schema={renderInputSchema}
        defaultProps={{
          moments: DEFAULT_MOMENTS,
          fps: 30,
          width: 1080,
          height: 1920,
        }}
        calculateMetadata={({ props }) => {
          const dur = calculateDuration(props.moments);
          return {
            durationInFrames: dur,
            fps: props.fps,
            width: props.width,
            height: props.height,
          };
        }}
      />
    </>
  );
};
