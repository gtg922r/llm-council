export default function SymposiaLogo({ size = 80, className = '' }) {
  // 8 circles evenly distributed around a central hexagon
  // with solid connecting arcs (with gaps) and radial lines
  
  const cx = 50; // center x
  const cy = 50; // center y
  const hexRadius = 18; // radius of hexagon
  const circleRadius = 5.5; // radius of outer circles
  const orbitRadius = 38; // distance from center to outer circles (increased)
  const numCircles = 8;
  
  // Generate hexagon points (flat-top orientation)
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
  
  // Generate arc segments between adjacent circles (solid with larger gaps at circles)
  const arcs = [];
  for (let i = 0; i < numCircles; i++) {
    const c1 = circles[i];
    const c2 = circles[(i + 1) % numCircles];
    
    // Calculate start and end angles for the arc
    const angle1 = c1.angle;
    const angle2 = c2.angle + (i === numCircles - 1 ? 2 * Math.PI : 0);
    
    // Larger gap so the connecting lines are more visible
    const gap = (circleRadius + 4) / orbitRadius;
    const a1 = angle1 + gap;
    const a2 = angle2 - gap;
    
    const x1 = cx + orbitRadius * Math.cos(a1);
    const y1 = cy + orbitRadius * Math.sin(a1);
    const x2 = cx + orbitRadius * Math.cos(a2);
    const y2 = cy + orbitRadius * Math.sin(a2);
    
    arcs.push({ x1, y1, x2, y2, large: 0 });
  }
  
  // Generate lines from hexagon edge midpoints toward outer circles
  const lines = circles.map((c) => {
    // Line from a point closer to hexagon edge toward the circle
    const innerDist = hexRadius + 2;
    const outerDist = orbitRadius - circleRadius - 2;
    return {
      x1: cx + innerDist * Math.cos(c.angle),
      y1: cy + innerDist * Math.sin(c.angle),
      x2: cx + outerDist * Math.cos(c.angle),
      y2: cy + outerDist * Math.sin(c.angle)
    };
  });
  
  // Unique ID for this instance's filter
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
        {/* Central hexagon */}
        <path d={hexPath} fill="currentColor" />
        
        {/* Radial connecting lines */}
        {lines.map((line, i) => (
          <line
            key={`line-${i}`}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        ))}
        
        {/* Solid arcs between circles (with gaps at the dots) */}
        {arcs.map((arc, i) => (
          <path
            key={`arc-${i}`}
            d={`M ${arc.x1} ${arc.y1} A ${orbitRadius} ${orbitRadius} 0 ${arc.large} 1 ${arc.x2} ${arc.y2}`}
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            fill="none"
          />
        ))}
        
        {/* Outer circles */}
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
