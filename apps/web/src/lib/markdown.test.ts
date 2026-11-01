import assert from "node:assert/strict";
import test from "node:test";
import { parseInline, parseMarkdown } from "./markdown.ts";

test("bold, italic and code become styled runs", () => {
  assert.deepEqual(parseInline("The **Golden Hind** was *his* ship, see `log`."), [
    { text: "The " },
    { text: "Golden Hind", bold: true },
    { text: " was " },
    { text: "his", italic: true },
    { text: " ship, see " },
    { text: "log", code: true },
    { text: "." },
  ]);
});

test("a marker still waiting for its partner mid-stream is hidden", () => {
  assert.deepEqual(parseInline("Drake's cousin **John Haw"), [{ text: "Drake's cousin John Haw" }]);
  assert.deepEqual(parseInline("aboard the *Golden"), [{ text: "aboard the Golden" }]);
});

test("underscores are left alone", () => {
  assert.deepEqual(parseInline("History · speculative_evolution_notes"), [{ text: "History · speculative_evolution_notes" }]);
});

// The shape of the answer that showed raw asterisks in testing
test("paragraphs and a starred bullet list", () => {
  const answer = [
    "The text mentions a few key people:",
    "",
    "* **William Hawkins:** A Plymouth sea captain.",
    "* **Queen Elizabeth I:** The English monarch who knighted Drake aboard the *Golden Hind*.",
    "",
    "That's everyone so far.",
  ].join("\n");

  const blocks = parseMarkdown(answer);

  assert.deepEqual(
    blocks.map((b) => b.kind),
    ["paragraph", "list", "paragraph"],
  );
  const list = blocks[1];
  assert.ok(list.kind === "list" && !list.ordered && list.items.length === 2);
  assert.deepEqual(list.items[0], [{ text: "William Hawkins:", bold: true }, { text: " A Plymouth sea captain." }]);
  assert.deepEqual(list.items[1].at(-2), { text: "Golden Hind", italic: true });
});

test("numbered lists, list items that wrap, and a list right after a sentence", () => {
  const blocks = parseMarkdown("Three reasons:\n1. Gold\n2. Glory,\n   and fame\n- a different list");

  assert.deepEqual(
    blocks.map((b) => (b.kind === "list" ? `list:${b.ordered}:${b.items.length}` : b.kind)),
    ["paragraph", "list:true:2", "list:false:1"],
  );
  const numbered = blocks[1];
  assert.ok(numbered.kind === "list");
  assert.deepEqual(numbered.items[1], [{ text: "Glory, and fame" }]);
});

test("a heading the model slips in reads as a bold line", () => {
  assert.deepEqual(parseMarkdown("## Summary\nShort."), [
    { kind: "paragraph", inlines: [{ text: "Summary", bold: true }, { text: "\nShort." }] },
  ]);
});
