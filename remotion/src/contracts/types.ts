/**
 * VULKRAN OS — Slot system types (adapted from VideoFlow v2).
 */

export type SlotType =
  | "text"
  | "textarea"
  | "image_url"
  | "color"
  | "number"
  | "select"
  | "boolean"
  | "text_array";

export interface SlotDefinition {
  key: string;
  type: SlotType;
  label: string;
  required: boolean;
  default?: unknown;
  options?: string[];
  min?: number;
  max?: number;
  group?: string;
  description?: string;
}

export interface TemplateContract {
  id: string;
  name: string;
  description: string;
  category: string;
  defaultDuration: number; // seconds
  slots: SlotDefinition[];
  tags: string[];
}

export interface MomentProps {
  id: string;
  template_id: string;
  slot_data: Record<string, unknown>;
  duration: number; // frames
  transition_type: string;
  transition_duration: number; // frames
  voiceover_url?: string;
}

export interface RenderInputProps {
  moments: MomentProps[];
  fps: number;
  width: number;
  height: number;
  audioSrc?: string;
}

export interface TemplateComponentProps {
  slots: Record<string, unknown>;
  width: number;
  height: number;
  duration: number; // frames
}
