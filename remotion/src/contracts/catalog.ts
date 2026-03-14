/**
 * VULKRAN OS — Template catalog.
 *
 * Templates are registered here with their slot schemas.
 * Jesus will design client-specific templates — this provides the base structure.
 */

import type { TemplateContract } from "./types";

export const TEMPLATE_CATALOG: TemplateContract[] = [
  {
    id: "title_card",
    name: "Title Card",
    description: "Full-screen title with subtitle and brand accent",
    category: "base",
    defaultDuration: 4,
    tags: ["intro", "title", "branding"],
    slots: [
      { key: "headline", type: "text", label: "Headline", required: true, default: "Title" },
      { key: "subtitle", type: "text", label: "Subtitle", required: false, default: "" },
      { key: "bg_color", type: "color", label: "Background Color", required: false, default: "#1a1a2e" },
      { key: "accent_color", type: "color", label: "Accent Color", required: false, default: "#7c3aed" },
      { key: "text_color", type: "color", label: "Text Color", required: false, default: "#ffffff" },
      { key: "logo_url", type: "image_url", label: "Logo", required: false },
    ],
  },
  {
    id: "text_highlight",
    name: "Text Highlight",
    description: "Key message with emphasis styling",
    category: "base",
    defaultDuration: 3,
    tags: ["text", "emphasis", "quote"],
    slots: [
      { key: "headline", type: "text", label: "Main Text", required: true },
      { key: "highlight_word", type: "text", label: "Highlight Word", required: false },
      { key: "bg_color", type: "color", label: "Background", required: false, default: "#0f0f23" },
      { key: "accent_color", type: "color", label: "Accent", required: false, default: "#7c3aed" },
    ],
  },
  {
    id: "stat_counter",
    name: "Stat Counter",
    description: "Animated number with label",
    category: "base",
    defaultDuration: 3,
    tags: ["data", "number", "stat"],
    slots: [
      { key: "value", type: "number", label: "Number", required: true, default: 0 },
      { key: "suffix", type: "text", label: "Suffix (%, +, etc.)", required: false, default: "" },
      { key: "label", type: "text", label: "Label", required: true, default: "Metric" },
      { key: "bg_color", type: "color", label: "Background", required: false, default: "#1a1a2e" },
      { key: "accent_color", type: "color", label: "Accent", required: false, default: "#10b981" },
    ],
  },
  {
    id: "image_overlay",
    name: "Image with Overlay",
    description: "Full-bleed image with text overlay",
    category: "base",
    defaultDuration: 4,
    tags: ["image", "visual", "overlay"],
    slots: [
      { key: "image_url", type: "image_url", label: "Image", required: true },
      { key: "headline", type: "text", label: "Overlay Text", required: false },
      { key: "overlay_opacity", type: "number", label: "Overlay Opacity", required: false, default: 0.5, min: 0, max: 1 },
      { key: "text_position", type: "select", label: "Text Position", required: false, default: "bottom", options: ["top", "center", "bottom"] },
    ],
  },
  {
    id: "bullet_reveal",
    name: "Bullet Points",
    description: "Sequential bullet point reveal",
    category: "base",
    defaultDuration: 5,
    tags: ["list", "bullets", "points"],
    slots: [
      { key: "title", type: "text", label: "Section Title", required: false },
      { key: "bullets", type: "text_array", label: "Bullet Points", required: true },
      { key: "bg_color", type: "color", label: "Background", required: false, default: "#1a1a2e" },
      { key: "accent_color", type: "color", label: "Accent", required: false, default: "#7c3aed" },
    ],
  },
  {
    id: "cta_card",
    name: "Call to Action",
    description: "Final CTA slide with button and contact info",
    category: "base",
    defaultDuration: 4,
    tags: ["cta", "closing", "contact"],
    slots: [
      { key: "headline", type: "text", label: "CTA Text", required: true, default: "Contact Us" },
      { key: "subtext", type: "text", label: "Supporting Text", required: false },
      { key: "button_text", type: "text", label: "Button Text", required: false, default: "Get Started" },
      { key: "bg_color", type: "color", label: "Background", required: false, default: "#1a1a2e" },
      { key: "accent_color", type: "color", label: "Accent", required: false, default: "#7c3aed" },
      { key: "website", type: "text", label: "Website URL", required: false },
    ],
  },
];

export function getTemplateContract(id: string): TemplateContract | undefined {
  return TEMPLATE_CATALOG.find((t) => t.id === id);
}
