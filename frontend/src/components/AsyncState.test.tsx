import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EmptyState, ErrorState, LoadingState } from './AsyncState';

describe('async states', () => {
  it('announces loading progress', () => {
    render(<LoadingState label="Loading evidence" />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading evidence');
  });

  it('announces server failures', () => {
    render(<ErrorState error={new Error('Service unavailable')} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Service unavailable');
  });

  it('describes empty results without fabricated data', () => {
    render(<EmptyState title="No scans" detail="Start the first scan." />);
    expect(screen.getByText('No scans')).toBeVisible();
    expect(screen.getByText('Start the first scan.')).toBeVisible();
  });
});
