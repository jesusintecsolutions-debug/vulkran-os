/**
 * VULKRAN OS — Template registry.
 *
 * Maps template_id strings to React components.
 * New templates are registered here.
 */

import React from "react";
import type { TemplateComponentProps } from "../contracts/types";

// Base templates
import { TitleCard } from "./TitleCard";
import { TextHighlight } from "./TextHighlight";
import { StatCounter } from "./StatCounter";
import { ImageOverlay } from "./ImageOverlay";
import { BulletReveal } from "./BulletReveal";
import { CTACard } from "./CTACard";

type TemplateComponent = React.FC<TemplateComponentProps>;

const TEMPLATE_REGISTRY: Record<string, TemplateComponent> = {
  title_card: TitleCard,
  text_highlight: TextHighlight,
  stat_counter: StatCounter,
  image_overlay: ImageOverlay,
  bullet_reveal: BulletReveal,
  cta_card: CTACard,
};

export function getTemplateComponent(templateId: string): TemplateComponent | undefined {
  return TEMPLATE_REGISTRY[templateId];
}

export function registerTemplate(id: string, component: TemplateComponent): void {
  TEMPLATE_REGISTRY[id] = component;
}

export function getRegisteredTemplateIds(): string[] {
  return Object.keys(TEMPLATE_REGISTRY);
}

export { TEMPLATE_REGISTRY };
