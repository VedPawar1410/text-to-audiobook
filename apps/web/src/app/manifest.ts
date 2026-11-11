import type { MetadataRoute } from "next";

// Makes Narrate installable with its own name, icon and full-screen look. On an iPhone an
// installed web app keeps playing while locked (measured in docs/research, E9).
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Narrate",
    short_name: "Narrate",
    description: "Every text, performed: multi-voice audiobooks with word-by-word read-along.",
    start_url: "/documents", // on a phone, your books are the useful place to open into
    display: "standalone",
    background_color: "#0b0908",
    theme_color: "#0b0908",
    icons: [
      { src: "/apple-icon", sizes: "180x180", type: "image/png" },
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
    ],
  };
}
