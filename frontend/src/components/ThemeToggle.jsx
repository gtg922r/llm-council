import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import './ThemeToggle.css';

const options = [
  { value: 'light', label: 'Light', Icon: Sun },
  { value: 'dark', label: 'Dark', Icon: Moon },
  { value: 'system', label: 'System', Icon: Monitor },
];

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="theme-toggle" role="group" aria-label="Theme toggle">
      {options.map(({ value, label, Icon }) => {
        const isActive = theme === value;
        return (
          <button
            key={value}
            type="button"
            className={`theme-toggle-button ${isActive ? 'active' : ''}`}
            onClick={() => setTheme(value)}
            aria-pressed={isActive}
            aria-label={`${label} mode`}
            title={`${label} mode`}
          >
            <Icon size={16} />
          </button>
        );
      })}
    </div>
  );
}
