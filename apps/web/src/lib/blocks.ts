import type { Segment } from "./api";

/** Consecutive segments of the same block (a paragraph, one character's speech…). */
export function groupBlocks(segments: Segment[]): Segment[][] {
  const blocks: Segment[][] = [];
  for (const segment of segments) {
    const current = blocks.at(-1);
    if (current && current[0].block_index === segment.block_index) current.push(segment);
    else blocks.push([segment]);
  }
  return blocks;
}
