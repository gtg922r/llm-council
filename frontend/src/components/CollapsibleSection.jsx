import { useState } from 'react';
import './CollapsibleSection.css';

export default function CollapsibleSection({ 
  title, 
  children, 
  defaultExpanded = false,
  className = ''
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className={`collapsible-section ${className} ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <div 
        className="collapsible-header" 
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        aria-expanded={isExpanded}
      >
        <span className="collapsible-icon">{isExpanded ? '▼' : '▶'}</span>
        <span className="collapsible-title">{title}</span>
      </div>
      {isExpanded && (
        <div className="collapsible-content">
          {children}
        </div>
      )}
    </div>
  );
}
