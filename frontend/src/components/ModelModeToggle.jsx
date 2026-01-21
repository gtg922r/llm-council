import { Zap, Brain } from 'lucide-react';
import { useModelMode } from '../context/SettingsContext';
import './ModelModeToggle.css';

const options = [
  { value: 'fast', label: 'Fast', Icon: Zap, description: 'Quick responses' },
  { value: 'smart', label: 'Smart', Icon: Brain, description: 'Best quality' },
];

export default function ModelModeToggle() {
  const { mode, setMode } = useModelMode();

  return (
    <div className="model-mode-toggle" role="group" aria-label="Model mode toggle">
      {options.map(({ value, label, Icon }) => {
        const isActive = mode === value;
        return (
          <button
            key={value}
            type="button"
            className={`model-mode-toggle-button ${isActive ? 'active' : ''}`}
            onClick={() => setMode(value)}
            aria-pressed={isActive}
            aria-label={`${label} mode`}
            title={`${label} mode`}
          >
            <Icon size={16} />
            <span className="model-mode-label">{label}</span>
          </button>
        );
      })}
    </div>
  );
}
