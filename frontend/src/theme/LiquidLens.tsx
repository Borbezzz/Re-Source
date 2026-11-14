import { useEffect, useId, useRef, useState } from "react";
import type { RefObject } from "react";

const WIDTH = 192;
const HEIGHT = 144;

// A rounded optical surface, encoded as red/green displacement vectors.
// Generated locally, with no external images or continuously rendered canvas.
function opticalMap() {
  const canvas = document.createElement("canvas");
  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  const context = canvas.getContext("2d");
  if (!context) return "";
  const pixels = context.createImageData(WIDTH, HEIGHT);
  for (let y = 0; y < HEIGHT; y++) {
    for (let x = 0; x < WIDTH; x++) {
      const nx = (x - WIDTH / 2) / (WIDTH / 2);
      const ny = (y - HEIGHT / 2) / (HEIGHT / 2);
      const radius = Math.min(1, Math.hypot(nx, ny));
      const bend =
        Math.pow(radius, 3) * Math.sqrt(Math.max(0, 1 - radius * radius));
      const offset = (y * WIDTH + x) * 4;
      pixels.data[offset] = 128 + nx * bend * 116;
      pixels.data[offset + 1] = 128 + ny * bend * 116;
      pixels.data[offset + 2] = 128;
      pixels.data[offset + 3] = 255;
    }
  }
  context.putImageData(pixels, 0, 0);
  return canvas.toDataURL();
}

export function LiquidLens({
  targetRef,
}: {
  targetRef: RefObject<HTMLElement | null>;
}) {
  const filterId = `title-lens-${useId().replace(/:/g, "")}`;
  const lensRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState("");

  useEffect(() => {
    const target = targetRef.current;
    const lens = lensRef.current;
    if (!target || !lens) return;
    setMap(opticalMap());
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    let x = 0;
    let y = 0;
    const hide = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      lens.dataset.active = "false";
    };
    const move = (event: PointerEvent) => {
      if (media.matches || event.pointerType === "touch") return hide();
      const rect = target.getBoundingClientRect();
      x = event.clientX - rect.left;
      y = event.clientY - rect.top;
      lens.dataset.active = "true";
      if (!frame)
        frame = requestAnimationFrame(() => {
          lens.style.transform = `translate3d(${x - WIDTH / 2}px, ${y - HEIGHT / 2}px, 0)`;
          frame = 0;
        });
    };
    const visibility = () => {
      if (document.hidden) hide();
    };
    target.addEventListener("pointermove", move);
    target.addEventListener("pointerleave", hide);
    target.addEventListener("pointercancel", hide);
    window.addEventListener("blur", hide);
    document.addEventListener("visibilitychange", visibility);
    media.addEventListener("change", hide);
    return () => {
      hide();
      target.removeEventListener("pointermove", move);
      target.removeEventListener("pointerleave", hide);
      target.removeEventListener("pointercancel", hide);
      window.removeEventListener("blur", hide);
      document.removeEventListener("visibilitychange", visibility);
      media.removeEventListener("change", hide);
    };
  }, [targetRef]);

  return (
    <>
      <svg className="glass-optics" aria-hidden="true" width="0" height="0">
        <defs>
          <filter
            id={filterId}
            x="0"
            y="0"
            width="100%"
            height="100%"
            colorInterpolationFilters="sRGB"
          >
            {map ? (
              <feImage
                href={map}
                width="100%"
                height="100%"
                preserveAspectRatio="none"
                result="optics"
              />
            ) : null}
            <feDisplacementMap
              in="SourceGraphic"
              in2="optics"
              scale="64"
              xChannelSelector="R"
              yChannelSelector="G"
            />
          </filter>
        </defs>
      </svg>
      <div
        ref={lensRef}
        className="wordmark-liquid-lens"
        data-active="false"
        aria-hidden="true"
        style={{
          width: WIDTH,
          height: HEIGHT,
          WebkitBackdropFilter: "blur(1px) saturate(125%)",
          backdropFilter: `url(#${filterId}) blur(0.3px) saturate(125%)`,
        }}
      />
    </>
  );
}
