/**
 * Walking-person SVG avatar.
 *
 * Stylized but readable: a head, a body, two arms, two legs. The "walking"
 * animation is a CSS bob (vertical bounce) — Framer Motion handles the
 * horizontal/vertical travel between rooms separately.
 *
 * Color is derived deterministically from `seed` (the journey id), so the
 * same patient looks the same across all stages of the simulation.
 */
import { memo } from "react";

interface AvatarProps {
  size?: number;
  seed?: number;
  /** Tweak hue offset for variety. */
  walking?: boolean;
  label?: string;
}

const HAIR_PALETTE = [
  "#3f2d20", "#5b3a29", "#8a4b2a", "#b87333", "#d6a86a",
  "#9b9b9b", "#544a3a", "#2c1810", "#7c5e3c", "#4a3220",
];

const SHIRT_PALETTE = [
  "#2563eb", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#6366f1",
];

const SKIN_PALETTE = [
  "#f4d4ad", "#e5b48b", "#c9966b", "#a37749", "#7a5a3c",
  "#5c4129", "#fce2c9", "#d8a679", "#b88456", "#3d2814",
];

function pick<T>(arr: readonly T[], seed: number): T {
  const i = Math.abs(Math.floor(seed)) % arr.length;
  return arr[i] as T;
}

export const PersonAvatar = memo(function PersonAvatar({
  size = 28,
  seed = 0,
  walking = false,
  label,
}: AvatarProps) {
  const hair = pick(HAIR_PALETTE, seed);
  const shirt = pick(SHIRT_PALETTE, seed * 7 + 3);
  const skin = pick(SKIN_PALETTE, seed * 11 + 5);
  // Slight color jitter so adjacent avatars don't look identical when seeds collide.
  const accent = pick(SHIRT_PALETTE, seed * 13 + 17);

  return (
    <div
      className={walking ? "avatar-walk" : ""}
      style={{ width: size, height: size * 1.5 }}
      aria-label={label}
      title={label}
    >
      <svg
        viewBox="0 0 32 48"
        width={size}
        height={size * 1.5}
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Hair / cap */}
        <ellipse cx="16" cy="10" rx="7" ry="6" fill={hair} />
        {/* Head */}
        <circle cx="16" cy="12" r="5" fill={skin} />
        {/* Hair front fringe */}
        <path d="M 11 10 Q 16 6 21 10 Q 18 9 16 9 Q 14 9 11 10 Z" fill={hair} />
        {/* Neck */}
        <rect x="14.5" y="16.5" width="3" height="2" fill={skin} />
        {/* Body / shirt */}
        <path
          d="M 8 19 Q 16 16 24 19 L 24 32 L 8 32 Z"
          fill={shirt}
        />
        {/* Shirt accent stripe */}
        <rect x="8" y="22" width="16" height="1.5" fill={accent} opacity="0.6" />
        {/* Arms */}
        <rect x="6" y="19" width="3" height="11" rx="1.5" fill={shirt} />
        <rect x="23" y="19" width="3" height="11" rx="1.5" fill={shirt} />
        {/* Hands */}
        <circle cx="7.5" cy="31" r="1.6" fill={skin} />
        <circle cx="24.5" cy="31" r="1.6" fill={skin} />
        {/* Legs (pants) */}
        <rect x="10" y="32" width="5" height="13" rx="1.5" fill="#1f2937" />
        <rect x="17" y="32" width="5" height="13" rx="1.5" fill="#1f2937" />
        {/* Shoes */}
        <ellipse cx="12.5" cy="46" rx="2.7" ry="1.3" fill="#0f172a" />
        <ellipse cx="19.5" cy="46" rx="2.7" ry="1.3" fill="#0f172a" />
      </svg>
    </div>
  );
});
