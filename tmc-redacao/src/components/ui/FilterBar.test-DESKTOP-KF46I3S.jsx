/**
 * Unit tests for FilterBar search debounce behavior.
 *
 * Verifies the Phase 2 change: debounce delay changed from 300ms to 500ms.
 * Tests:
 *  1. updateFilter is called after exactly 500ms (not 300ms, not 400ms)
 *  2. Rapid typing cancels the previous timer — only the last value is flushed
 *  3. Unmounting before 500ms elapses prevents the delayed call
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import FilterBar from './FilterBar';

// ---------------------------------------------------------------------------
// Module-level mocks
// ---------------------------------------------------------------------------

// Mock useFilters from context — will be overridden per test via mockReturnValue
const mockUpdateFilter = vi.fn();

vi.mock('../../context', () => ({
  useFilters: vi.fn(),
}));

// Mock getSourcesCached — returns empty sources so the component mounts cleanly
vi.mock('../../services/api', () => ({
  getSourcesCached: vi.fn(() => Promise.resolve({ items: [] })),
}));

// Mock UrgencyChips — a leaf component not under test here
vi.mock('./UrgencyChips', () => ({
  default: () => null,
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

import { useFilters } from '../../context';

/** Minimal prop set that satisfies FilterBar's PropTypes. */
const defaultProps = {
  urgencyCounts: {},
  facets: { categories: [], tags: [] },
};

/**
 * Render FilterBar and flush the initial async getSourcesCached microtask so
 * the `setSources` state update is wrapped in act, eliminating React 19 warnings.
 */
async function renderFilterBar(props = defaultProps) {
  let result;
  await act(async () => {
    result = render(<FilterBar {...props} />);
    // Let the getSourcesCached Promise resolve inside act
    await Promise.resolve();
  });
  return result;
}

/**
 * Configure the useFilters mock with a given searchQuery value.
 * Reuses the module-level mockUpdateFilter spy.
 */
function setupFilters(searchQuery = '') {
  useFilters.mockReturnValue({
    filters: {
      searchQuery,
      tag: null,
      category: null,
      source: null,
      urgency: 1,
      scoreClassification: null,
      sortOrder: 'newest',
    },
    updateFilter: mockUpdateFilter,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('FilterBar — search debounce (500ms)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockUpdateFilter.mockReset();
    setupFilters('');
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // -------------------------------------------------------------------------
  it('does not call updateFilter immediately on input change', async () => {
    await renderFilterBar();
    const input = screen.getByRole('searchbox');

    act(() => { fireEvent.change(input, { target: { value: 'test' } }); });

    expect(mockUpdateFilter).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------------
  it('does not call updateFilter at 400ms (debounce is 500ms, not 300ms)', async () => {
    await renderFilterBar();
    const input = screen.getByRole('searchbox');

    act(() => { fireEvent.change(input, { target: { value: 'test' } }); });
    act(() => { vi.advanceTimersByTime(400); });

    expect(mockUpdateFilter).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------------
  it('calls updateFilter with the typed value after exactly 500ms', async () => {
    await renderFilterBar();
    const input = screen.getByRole('searchbox');

    act(() => { fireEvent.change(input, { target: { value: 'test' } }); });

    // 400ms elapsed — still silent
    act(() => { vi.advanceTimersByTime(400); });
    expect(mockUpdateFilter).not.toHaveBeenCalled();

    // 100ms more (total 500ms) — fires now
    act(() => { vi.advanceTimersByTime(100); });
    expect(mockUpdateFilter).toHaveBeenCalledTimes(1);
    expect(mockUpdateFilter).toHaveBeenCalledWith('searchQuery', 'test');
  });

  // -------------------------------------------------------------------------
  it('cancels the previous timer when new input arrives — only last value is flushed', async () => {
    await renderFilterBar();
    const input = screen.getByRole('searchbox');

    // Type "a", advance 300ms (not enough to flush)
    act(() => { fireEvent.change(input, { target: { value: 'a' } }); });
    act(() => { vi.advanceTimersByTime(300); });

    // Type "b" — resets the 500ms clock
    act(() => { fireEvent.change(input, { target: { value: 'b' } }); });

    // Advance 500ms from "b"
    act(() => { vi.advanceTimersByTime(500); });

    // Only one call, with the last value
    expect(mockUpdateFilter).toHaveBeenCalledTimes(1);
    expect(mockUpdateFilter).toHaveBeenCalledWith('searchQuery', 'b');
    expect(mockUpdateFilter).not.toHaveBeenCalledWith('searchQuery', 'a');
  });

  // -------------------------------------------------------------------------
  it('does not call updateFilter after unmount (cleanup cancels pending timer)', async () => {
    const { unmount } = await renderFilterBar();
    const input = screen.getByRole('searchbox');

    // Type something — starts the 500ms timer
    act(() => { fireEvent.change(input, { target: { value: 'hello' } }); });

    // Unmount before 500ms
    unmount();

    // Advance past the debounce window
    act(() => { vi.advanceTimersByTime(600); });

    // Timer was cleared on unmount — updateFilter must not have been called
    expect(mockUpdateFilter).not.toHaveBeenCalled();
  });
});
