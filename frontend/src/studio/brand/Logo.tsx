import { useId } from "react";
import "./logo.css";

/**
 * Re::Source rotor mark. Eight swept blades form one continuous "renew" loop
 * around a two-dot hub (the "::" of the wordmark). The thermal gradient runs
 * from cool intake cyan to hot exhaust amber, like a turbofan's flow path.
 * Derived from generated concept design/logo-concepts/a-rotor-loop.png.
 */
const BLADES = 8;
const D = 19.5; // circle-centre distance from the hub
const R = 25.5; // blade circle radius
const GAP = 2.4; // slit width between neighbouring blades

type P = [number, number];
const C: P = [50, 50];
const add = (a: P, b: P): P => [a[0] + b[0], a[1] + b[1]];
const f = (p: P) => `${p[0].toFixed(2)} ${p[1].toFixed(2)}`;
const centre = (i: number): P => {
  const a = ((360 / BLADES) * i * Math.PI) / 180;
  return add(C, [D * Math.cos(a), D * Math.sin(a)]);
};

function intersect(a: P, ra: number, b: P, rb: number): [P, P] {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const d = Math.hypot(dx, dy);
  const l = (ra * ra - rb * rb + d * d) / (2 * d);
  const h = Math.sqrt(Math.max(0, ra * ra - l * l));
  const m: P = [a[0] + (l * dx) / d, a[1] + (l * dy) / d];
  return [
    [m[0] + (h * dy) / d, m[1] - (h * dx) / d],
    [m[0] - (h * dy) / d, m[1] + (h * dx) / d],
  ];
}

/** SVG arc on circle (c, r) from p to q whose midpoint satisfies `keep`. */
function arc(c: P, r: number, p: P, q: P, keep: (m: P) => boolean): string {
  const a0 = Math.atan2(p[1] - c[1], p[0] - c[0]);
  const a1 = Math.atan2(q[1] - c[1], q[0] - c[0]);
  for (const sweep of [1, 0]) {
    let span = sweep ? a1 - a0 : a0 - a1;
    while (span < 0) span += Math.PI * 2;
    const mid = a0 + (sweep ? span / 2 : -span / 2);
    if (keep([c[0] + r * Math.cos(mid), c[1] + r * Math.sin(mid)])) {
      return `A ${r} ${r} 0 ${span > Math.PI ? 1 : 0} ${sweep} ${f(q)}`;
    }
  }
  return `L ${f(q)}`;
}

/** Blade i = disc i minus (slightly enlarged) disc i+1: a swept crescent. */
function bladePath(i: number): string {
  const a = centre(i);
  const b = centre(i + 1);
  const rb = R + GAP;
  const [p, q] = intersect(a, R, b, rb);
  const outsideB = (m: P) => Math.hypot(m[0] - b[0], m[1] - b[1]) > rb;
  const insideA = (m: P) => Math.hypot(m[0] - a[0], m[1] - a[1]) < R;
  return `M ${f(p)} ${arc(a, R, p, q, outsideB)} ${arc(b, rb, q, p, insideA)} Z`;
}

const PATHS = Array.from({ length: BLADES }, (_, i) => bladePath(i));

export function LogoMark({
  size = 28,
  spinning = false,
  title,
}: {
  size?: number;
  spinning?: boolean;
  title?: string;
}) {
  const id = useId().replace(/:/g, "");
  return (
    <svg
      className={`rs-logo-mark${spinning ? " is-spinning" : ""}`}
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      <defs>
        <linearGradient id={`g${id}`} x1="8" y1="14" x2="92" y2="88" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#38BDF8" />
          <stop offset="0.4" stopColor="#8B5CF6" />
          <stop offset="0.72" stopColor="#EC4899" />
          <stop offset="1" stopColor="#FB923C" />
        </linearGradient>
      </defs>
      <mask id={`m${id}`}>
        <rect width="100" height="100" fill="#fff" />
        <circle cx="50" cy="50" r="16" fill="#000" />
      </mask>
      <g className="rs-logo-rotor" fill={`url(#g${id})`} mask={`url(#m${id})`}>
        {PATHS.map((d, i) => (
          <path key={i} d={d} />
        ))}
      </g>
      <circle cx="50" cy="44" r="4.3" fill={`url(#g${id})`} />
      <circle cx="50" cy="56" r="4.3" fill={`url(#g${id})`} />
    </svg>
  );
}

/** Horizontal lockup: mark + "Re::Source" with a gradient double colon. */
export function Logo({ size = 26, className = "" }: { size?: number; className?: string }) {
  return (
    <span className={`rs-logo ${className}`}>
      <LogoMark size={size} />
      <span className="rs-logo-word" aria-label="Re::Source">
        Re<span className="rs-logo-colon">::</span>Source
      </span>
    </span>
  );
}
