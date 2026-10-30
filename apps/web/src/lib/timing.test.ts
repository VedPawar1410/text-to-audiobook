import assert from "node:assert/strict";
import test from "node:test";
import { buildCues, displayWords, formatClock, lastStartingAt, position, type Manifest } from "./timing.ts";

// A slice of a real manifest (PR 7): a scene heading said differently from how it's shown,
// two lines of dialogue, and a silent transition.
const MANIFEST: Manifest = {
  duration: 9,
  segments: [
    { segment_id: 1, start: 0.25, end: 2.4, words: [
      { text: "Interior.", start: 0.25, end: 0.79 }, { text: "Citadel.", start: 0.79, end: 1.4 }, { text: "Night.", start: 1.6, end: 2.4 },
    ] },
    { segment_id: 2, start: 3.0, end: 4.0, words: [
      { text: "You", start: 3.0, end: 3.4 }, { text: "came.", start: 3.4, end: 4.0 },
    ] },
    { segment_id: 3, start: 4.5, end: 6.0, words: [
      { text: "They", start: 4.5, end: 4.8 }, { text: "always", start: 4.8, end: 5.3 }, { text: "come.", start: 5.3, end: 6.0 },
    ] },
    { segment_id: 4, start: 6.5, end: 7.7, words: [] },
  ],
};

const TEXT: Record<number, string> = {
  1: "INT. CITADEL - NIGHT",
  2: "You came.",
  3: "They always come.",
  4: "CUT TO:",
};

const cues = buildCues(MANIFEST, (id) => TEXT[id]);

test("lastStartingAt finds the item playing at a given time", () => {
  const items = [{ start: 0 }, { start: 1 }, { start: 2.5 }];
  assert.equal(lastStartingAt(items, -0.1), -1);
  assert.equal(lastStartingAt(items, 0), 0);
  assert.equal(lastStartingAt(items, 2.49), 1);
  assert.equal(lastStartingAt(items, 99), 2);
  assert.equal(lastStartingAt([], 1), -1);
});

test("words align with the displayed text when they match", () => {
  assert.deepEqual(cues[1].words?.map((w) => w.text), ["You", "came."]);
  assert.deepEqual(displayWords("  They  always\ncome. "), ["They", "always", "come."]);
});

test("lines spoken differently from how they are shown fall back to whole-line highlighting", () => {
  assert.equal(cues[0].words, null); // "INT. CITADEL - NIGHT" vs "Interior. Citadel. Night."
  assert.equal(cues[3].words, null); // a transition: silence, no words
});

test("position follows the voice word by word", () => {
  assert.deepEqual(position(cues, 0), { cue: -1, word: -1 }); // before the first line
  assert.deepEqual(position(cues, 1.0), { cue: 0, word: -1 }); // whole-line cue
  assert.deepEqual(position(cues, 3.1), { cue: 1, word: 0 });
  assert.deepEqual(position(cues, 5.0), { cue: 2, word: 1 }); // "always"
});

test("position holds the last word through pauses instead of flickering", () => {
  assert.deepEqual(position(cues, 4.2), { cue: 1, word: 1 }); // the pause after "came."
  assert.deepEqual(position(cues, 7.0), { cue: 3, word: -1 }); // the silent transition
});

test("formatClock", () => {
  assert.equal(formatClock(0), "0:00");
  assert.equal(formatClock(65.9), "1:05");
  assert.equal(formatClock(3725), "1:02:05");
});
