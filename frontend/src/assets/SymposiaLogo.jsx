export default function SymposiaLogo({ size = 80, className = '' }) {
  const cx = 50;
  const cy = 50;
  const hexRadius = 20;
  const circleRadius = 5.5;
  const orbitRadius = 36;
  const numCircles = 8;
  const arcGap = 3;
  const lineGapInner = 2.5;
  const lineGapOuter = 3.5;
  const strokeWidth = 2.25;
  
  // Generate hexagon points
  const hexPoints = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    hexPoints.push({
      x: cx + hexRadius * Math.cos(angle),
      y: cy + hexRadius * Math.sin(angle)
    });
  }
  const hexPath = hexPoints.map((p, i) => 
    `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`
  ).join(' ') + ' Z';
  
  // Generate circle positions
  const circles = [];
  for (let i = 0; i < numCircles; i++) {
    const angle = (2 * Math.PI / numCircles) * i - Math.PI / 2;
    circles.push({
      x: cx + orbitRadius * Math.cos(angle),
      y: cy + orbitRadius * Math.sin(angle),
      angle
    });
  }
  
  // Generate arcs
  const arcs = [];
  for (let i = 0; i < numCircles; i++) {
    const c1 = circles[i];
    const c2 = circles[(i + 1) % numCircles];
    const angle1 = c1.angle;
    const angle2 = c2.angle + (i === numCircles - 1 ? 2 * Math.PI : 0);
    const gap = (circleRadius + arcGap) / orbitRadius;
    const a1 = angle1 + gap;
    const a2 = angle2 - gap;
    arcs.push({
      x1: cx + orbitRadius * Math.cos(a1),
      y1: cy + orbitRadius * Math.sin(a1),
      x2: cx + orbitRadius * Math.cos(a2),
      y2: cy + orbitRadius * Math.sin(a2)
    });
  }
  
  // Generate lines
  const lines = circles.map(c => {
    const innerDist = hexRadius + lineGapInner;
    const outerDist = orbitRadius - circleRadius - lineGapOuter;
    return {
      x1: cx + innerDist * Math.cos(c.angle),
      y1: cy + innerDist * Math.sin(c.angle),
      x2: cx + outerDist * Math.cos(c.angle),
      y2: cy + outerDist * Math.sin(c.angle)
    };
  });
  
  const filterId = `logo-shadow-${Math.random().toString(36).substr(2, 9)}`;
  
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Symposia Logo"
      style={{ color: 'var(--logo-color, #333)' }}
    >
      <defs>
        <filter id={filterId} x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="1" stdDeviation="2" floodOpacity="0.15" />
        </filter>
      </defs>
      
      <g filter={`url(#${filterId})`}>
        <path d={hexPath} fill="currentColor" />
        
        {lines.map((line, i) => (
          <line
            key={`line-${i}`}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        ))}
        
        {arcs.map((arc, i) => (
          <path
            key={`arc-${i}`}
            d={`M ${arc.x1} ${arc.y1} A ${orbitRadius} ${orbitRadius} 0 0 1 ${arc.x2} ${arc.y2}`}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            fill="none"
          />
        ))}
        
        {circles.map((c, i) => (
          <circle
            key={`circle-${i}`}
            cx={c.x}
            cy={c.y}
            r={circleRadius}
            fill="currentColor"
          />
        ))}
      </g>
    </svg>
  );
}
