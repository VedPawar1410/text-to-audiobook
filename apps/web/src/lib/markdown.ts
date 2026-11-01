/**
 * Just enough Markdown for chat answers: paragraphs, bulleted and numbered lists,
 * **bold**, *italic* and `code`. Hand-written rather than a dependency: the model is
 * asked for little more than this, and a small parser is easy to read and to test.
 * Underscore emphasis is left out on purpose (ids like speculative_evolution).
 */

export type Inline = { text: string; bold?: boolean; italic?: boolean; code?: boolean };
export type Block =
  | { kind: "paragraph"; inlines: Inline[] }
  | { kind: "list"; ordered: boolean; items: Inline[][] };

const BULLET = /^\s*(?:[-*•]|(\d+)[.)])\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;
const TOKEN = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)/;

/**
 * Mid-stream an answer can end inside "**bold" before its closing marker arrives.
 * Drop an unpaired marker so the reader never sees stray asterisks.
 */
function dropUnclosed(text: string): string {
  if ((text.match(/\*\*/g)?.length ?? 0) % 2) text = text.replace(/\*\*(?![\s\S]*\*\*)/, "");
  const singles = text.replace(/\*\*/g, "").replace(/(^|\s)\*(\s)/g, "$1$2"); // a lone "* " isn't emphasis
  if ((singles.match(/\*/g)?.length ?? 0) % 2) text = text.replace(/\*(?![\s\S]*\*)/, "");
  if ((text.match(/`/g)?.length ?? 0) % 2) text = text.replace(/`(?![\s\S]*`)/, "");
  return text;
}

export function parseInline(source: string): Inline[] {
  return dropUnclosed(source)
    .split(TOKEN)
    .filter(Boolean)
    .map((part) => {
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) return { text: part.slice(2, -2), bold: true };
      if (part.startsWith("`") && part.endsWith("`") && part.length > 2) return { text: part.slice(1, -1), code: true };
      if (part.startsWith("*") && part.endsWith("*") && part.length > 2) return { text: part.slice(1, -1), italic: true };
      return { text: part };
    });
}

type Draft = { paragraph: string[]; list: { ordered: boolean; items: string[] } | null };

export function parseMarkdown(source: string): Block[] {
  const blocks: Block[] = [];
  const draft: Draft = { paragraph: [], list: null };

  const flush = () => {
    if (draft.paragraph.length) blocks.push({ kind: "paragraph", inlines: parseInline(draft.paragraph.join("\n")) });
    if (draft.list) blocks.push({ kind: "list", ordered: draft.list.ordered, items: draft.list.items.map(parseInline) });
    draft.paragraph = [];
    draft.list = null;
  };

  for (const raw of source.split("\n")) {
    const line = raw.trimEnd();
    const bullet = line.match(BULLET);
    if (!line.trim()) {
      flush();
    } else if (bullet) {
      const ordered = bullet[1] !== undefined;
      if (draft.paragraph.length || (draft.list && draft.list.ordered !== ordered)) flush();
      draft.list ??= { ordered, items: [] };
      draft.list.items.push(bullet[2]);
    } else if (draft.list && /^\s+/.test(raw)) {
      draft.list.items[draft.list.items.length - 1] += ` ${line.trim()}`; // an indented continuation of the item
    } else {
      if (draft.list) flush();
      const heading = line.match(HEADING);
      draft.paragraph.push(heading ? `**${heading[1]}**` : line); // the prompt asks for no headings; bold if one slips in
    }
  }
  flush();
  return blocks;
}
