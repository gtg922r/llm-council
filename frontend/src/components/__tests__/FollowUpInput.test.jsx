import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FollowUpInput from '../FollowUpInput';

describe('FollowUpInput', () => {
  it('renders trigger button', () => {
    render(<FollowUpInput onActivate={vi.fn()} isLoading={false} />);
    expect(screen.getByRole('button', { name: /Send Message to Chairman/i })).toBeInTheDocument();
  });

  it('calls onActivate when clicked', () => {
    const onActivate = vi.fn();
    render(<FollowUpInput onActivate={onActivate} isLoading={false} />);
    fireEvent.click(screen.getByRole('button', { name: /Send Message to Chairman/i }));
    expect(onActivate).toHaveBeenCalled();
  });

  it('is disabled when isLoading is true', () => {
    render(<FollowUpInput onActivate={vi.fn()} isLoading={true} />);
    expect(screen.getByRole('button', { name: /Send Message to Chairman/i })).toBeDisabled();
  });
});