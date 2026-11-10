/**
 * The showcase build (NEXT_PUBLIC_DEMO=1, deployed on Vercel) has no backend: one pre-recorded
 * public-domain book is served from static files (see next.config.ts), and anything that
 * would write or needs the servers explains itself instead.
 */
export const DEMO = process.env.NEXT_PUBLIC_DEMO === "1";

export const REPO_URL = "https://github.com/VedPawar1410/text-to-audiobook";

// The book in public/demo (The Gift of the Magi). Exporting another book? Update this id.
export const SHOWCASE_BOOK = "996983bd-4f9d-444b-9c47-be19e97c33ce";

export const DEMO_MESSAGE =
  "This is a read-only showcase. Run Narrate on your own computer to import, direct and record your own books.";
