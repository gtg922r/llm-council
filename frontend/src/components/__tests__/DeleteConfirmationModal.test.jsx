import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import DeleteConfirmationModal from '../DeleteConfirmationModal';

describe('DeleteConfirmationModal', () => {
  it('renders with default warning text', () => {
    render(
      <DeleteConfirmationModal 
        isOpen={true} 
        onClose={vi.fn()} 
        onConfirm={vi.fn()} 
      />
    );
    expect(screen.getByText(/Are you sure you want to delete this conversation forever\?/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('renders with custom title for bulk delete', () => {
    render(
      <DeleteConfirmationModal 
        isOpen={true} 
        onClose={vi.fn()} 
        onConfirm={vi.fn()} 
        title="Delete All Archived"
        message="Are you sure you want to delete all archived conversations?"
      />
    );
    expect(screen.getByRole('heading', { name: /Delete All Archived/i })).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to delete all archived conversations\?/i)).toBeInTheDocument();
  });

  it('calls onConfirm when Delete is clicked', () => {
    const onConfirm = vi.fn();
    render(
      <DeleteConfirmationModal 
        isOpen={true} 
        onClose={vi.fn()} 
        onConfirm={onConfirm} 
      />
    );
    
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when Cancel is clicked', () => {
    const onClose = vi.fn();
    render(
      <DeleteConfirmationModal 
        isOpen={true} 
        onClose={onClose} 
        onConfirm={vi.fn()} 
      />
    );
    
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
