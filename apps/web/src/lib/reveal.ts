/**
 * Pacing for streamed answers. The model sends text in bursts (often a whole sentence
 * or paragraph at once); showing it word by word at a steady pace reads like someone
 * talking, not like text popping in.
 */

/** The everyday pace: brisk, but you can follow it. */
export const WORDS_PER_SECOND = 22;
/** If the model gets further ahead than this, speed up just enough to catch up. */
export const MAX_LAG_SECONDS = 4;

const WORD = /\S+\s*/g;

/** How many words are still to show after `from`. */
export function wordsLeft(text: string, from: number): number {
  return text.slice(from).match(WORD)?.length ?? 0;
}

/** The index just after `count` more words (each with the space that follows it). */
export function advanceWords(text: string, from: number, count: number): number {
  if (count <= 0) return from;
  // Leading whitespace belongs to nobody: skip it so the count is in real words
  let index = from + (text.slice(from).match(/^\s*/)?.[0].length ?? 0);
  WORD.lastIndex = index;
  for (let i = 0; i < count; i++) {
    const match = WORD.exec(text);
    if (!match) return text.length;
    index = match.index + match[0].length;
  }
  return index;
}

/** Words per second for the current backlog: steady, unless it's falling too far behind. */
export function revealRate(backlogWords: number): number {
  return Math.max(WORDS_PER_SECOND, backlogWords / MAX_LAG_SECONDS);
}
