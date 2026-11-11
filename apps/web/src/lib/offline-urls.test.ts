import assert from "node:assert/strict";
import test from "node:test";
import { bookUrls, estimateBytes, formatSize } from "./offline-urls.ts";

const chapters = [
  { section_id: 20, version: "abc", duration_s: 100 },
  { section_id: 21, version: "def", duration_s: 50 },
];

test("a saved book covers its data, every manifest and every chapter's audio", () => {
  const urls = bookUrls("book", chapters);
  assert.deepEqual(urls.data, [
    "/api/documents/book",
    "/api/documents/book/render",
    "/api/documents/book/chapters/20/manifest?v=abc",
    "/api/documents/book/chapters/21/manifest?v=def",
  ]);
  assert.deepEqual(urls.audio, ["/api/documents/book/chapters/20/audio?v=abc", "/api/documents/book/chapters/21/audio?v=def"]);
});

test("size is estimated from duration at 64 kbps and shown readably", () => {
  assert.equal(estimateBytes(chapters), 1_200_000);
  assert.equal(formatSize(1_200_000), "1 MB");
  assert.equal(formatSize(2_500_000_000), "2.5 GB");
});
