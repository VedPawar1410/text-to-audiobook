import assert from "node:assert/strict";
import test from "node:test";
import { MAX_LAG_SECONDS, WORDS_PER_SECOND, advanceWords, revealRate, wordsLeft } from "./reveal.ts";

const TEXT = "So far, the main  figure is\nDrake.";

test("words advance one at a time, each with the space after it", () => {
  assert.equal(TEXT.slice(0, advanceWords(TEXT, 0, 1)), "So ");
  assert.equal(TEXT.slice(0, advanceWords(TEXT, 0, 4)), "So far, the main  ");
  assert.equal(advanceWords(TEXT, 0, 99), TEXT.length);
  assert.equal(advanceWords(TEXT, 3, 0), 3);
});

test("counting what's left", () => {
  assert.equal(wordsLeft(TEXT, 0), 7);
  assert.equal(wordsLeft(TEXT, advanceWords(TEXT, 0, 5)), 2);
  assert.equal(wordsLeft(TEXT, TEXT.length), 0);
});

test("the pace is steady until the backlog grows, then never falls too far behind", () => {
  assert.equal(revealRate(5), WORDS_PER_SECOND);
  assert.equal(revealRate(WORDS_PER_SECOND * MAX_LAG_SECONDS), WORDS_PER_SECOND);
  assert.equal(revealRate(400), 400 / MAX_LAG_SECONDS); // a long answer arriving at once
});
