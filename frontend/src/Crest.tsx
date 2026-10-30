/** Our own police-style badge: a star in a laurel wreath, ringed in saffron, white and green.
 *  Original artwork, not the emblem of any police force or government. To use an official emblem later, replace this file and public/favicon.svg. */
const NAVY = '#0a2a66', SAFFRON = '#ff9933', GREEN = '#138808', GOLD = '#d9a63a', STAR = '#ffc857'

/** Laurel leaves along each side of the wreath, tilted outward, with a gap at the top and bottom. */
function leaves(side: 1 | -1) {
  const out = []
  for (let k = 0; k < 6; k++) {
    const deg = side === 1 ? -66 + k * 24 : 246 - k * 24         // position on the circle, counter-clockwise from +x
    const a = (deg * Math.PI) / 180
    const x = 50 + 31 * Math.cos(a), y = 50 - 31 * Math.sin(a)
    const rot = -deg + side * 32                                  // long axis along the arc, then leaning outward
    out.push(<ellipse key={`${side}${k}`} cx={x.toFixed(2)} cy={y.toFixed(2)} rx="3" ry="6.6" fill={GOLD} transform={`rotate(${rot} ${x.toFixed(2)} ${y.toFixed(2)})`} />)
  }
  return out
}

export default function Crest({ size = 24, className }: { size?: number; className?: string }) {
  const C = 2 * Math.PI * 44, seg = C / 3
  return (
    <svg className={className} viewBox="0 0 100 100" width={size} height={size} aria-hidden focusable="false">
      <circle cx="50" cy="50" r="46.5" fill="#fff" />
      <circle cx="50" cy="50" r="44" fill="none" stroke={NAVY} strokeWidth="6.5" />
      <g fill="none" strokeWidth="4" transform="rotate(-90 50 50)">
        <circle cx="50" cy="50" r="44" stroke={SAFFRON} strokeDasharray={`${seg} ${C - seg}`} strokeDashoffset="0" />
        <circle cx="50" cy="50" r="44" stroke="#fff" strokeDasharray={`${seg} ${C - seg}`} strokeDashoffset={-seg} />
        <circle cx="50" cy="50" r="44" stroke={GREEN} strokeDasharray={`${seg} ${C - seg}`} strokeDashoffset={-2 * seg} />
      </g>
      <circle cx="50" cy="50" r="39" fill={NAVY} />
      {leaves(1)}{leaves(-1)}
      <circle cx="50" cy="50" r="21" fill="#0e3a8c" stroke={STAR} strokeWidth="1.2" />
      <path d="m50 34.5 4.3 9 9.9 1.3-7.2 6.9 1.8 9.8L50 56l-8.8 4.9 1.8-9.8-7.2-6.9 9.9-1.3L50 34.5Z" fill={STAR} />
    </svg>
  )
}
