/**
 * Determine whether the "Find Implementations" option should be shown
 * in the context menu. Only Class and Interface kinds have meaningful
 * implementations to find.
 */
export function shouldShowImplementations(kind) {
  return kind === 'Class' || kind === 'Interface';
}

/** @deprecated Use shouldShowImplementations instead */
export const shouldShowHierarchy = shouldShowImplementations;
