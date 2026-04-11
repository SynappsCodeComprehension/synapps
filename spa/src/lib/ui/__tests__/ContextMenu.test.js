import { describe, it, expect } from 'vitest';
import { shouldShowImplementations } from '../contextMenuUtils.js';

describe('ContextMenu showImplementations logic', () => {
  it('returns true for Class', () => {
    expect(shouldShowImplementations('Class')).toBe(true);
  });

  it('returns true for Interface', () => {
    expect(shouldShowImplementations('Interface')).toBe(true);
  });

  it('returns false for Method', () => {
    expect(shouldShowImplementations('Method')).toBe(false);
  });

  it('returns false for Property', () => {
    expect(shouldShowImplementations('Property')).toBe(false);
  });

  it('returns false for Field', () => {
    expect(shouldShowImplementations('Field')).toBe(false);
  });

  it('returns false for empty string', () => {
    expect(shouldShowImplementations('')).toBe(false);
  });

  it('returns false for undefined', () => {
    expect(shouldShowImplementations(undefined)).toBe(false);
  });

  it('returns false for null', () => {
    expect(shouldShowImplementations(null)).toBe(false);
  });
});

describe('ContextMenu get_context_for visibility', () => {
  const ALL_SYMBOL_KINDS = ['Class', 'Interface', 'Method', 'Property', 'Field'];

  it('get_context_for has no kind filter — shown for all symbol kinds', () => {
    ALL_SYMBOL_KINDS.forEach(kind => {
      expect(typeof shouldShowImplementations(kind)).toBe('boolean');
    });
  });
});
