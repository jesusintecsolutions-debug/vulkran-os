/**
 * VULKRAN OS — SFX catalog and defaults.
 * Adapted from VideoFlow v2 SFXEngine.
 */

export interface SFXEntry {
  path: string;
  volume: number;
}

export const SFX_CATALOG: Record<string, SFXEntry> = {
  whoosh: { path: "/sfx/whoosh.mp3", volume: 0.3 },
  slide: { path: "/sfx/slide.mp3", volume: 0.25 },
  fade_in: { path: "/sfx/fade_in.mp3", volume: 0.2 },
  card_appear: { path: "/sfx/card_appear.mp3", volume: 0.3 },
  counter_tick: { path: "/sfx/counter_tick.mp3", volume: 0.15 },
};

export const TRANSITION_SFX: Record<string, string> = {
  fade: "fade_in",
  slide: "slide",
  wipe: "whoosh",
  flip: "whoosh",
};

export const TEMPLATE_SFX_DEFAULTS: Record<string, { sfx: string; delay: number }[]> = {
  title_card: [{ sfx: "card_appear", delay: 0 }],
  stat_counter: [{ sfx: "counter_tick", delay: 5 }],
};
