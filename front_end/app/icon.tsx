import { ImageResponse } from "next/og";

// The header's brand mark (a Duke circle and a TECO diamond overlapping) as the browser-tab
// icon, so the favicon isn't a generic default. Built from plain divs, not the header's SVG -
// next/og's renderer (Satori) supports flexbox/borderRadius/transform, not arbitrary SVG paths.
export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", position: "relative", background: "#f7f8f5" }}>
        <div
          style={{
            position: "absolute",
            left: 3,
            top: 7,
            width: 18,
            height: 18,
            borderRadius: 9999,
            background: "#2456b8",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 16,
            top: 8,
            width: 13,
            height: 13,
            background: "#e08a12",
            transform: "rotate(45deg)",
          }}
        />
      </div>
    ),
    { ...size },
  );
}
