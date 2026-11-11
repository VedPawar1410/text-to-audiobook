import { ImageResponse } from "next/og";

// The iPhone home-screen icon (and lock-screen artwork). iOS ignores SVG icons and wants an
// opaque 180×180 PNG; it rounds the corners itself. Drawn at build time from the same tungsten
// orb as icon.svg, so there's no binary file to keep in sync.
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: "#0b0908" }}>
        <div
          style={{
            width: 108,
            height: 108,
            borderRadius: "50%",
            background: "radial-gradient(circle at 38% 32%, #ffe2ad 0%, #ffb547 45%, #6b3f0c 100%)",
            boxShadow: "0 0 48px rgba(255, 181, 71, 0.35)",
          }}
        />
      </div>
    ),
    size,
  );
}
