/**
 * useVersionHistory Hook
 *
 * Manages version history for article content with undo/redo support.
 * Enables non-destructive editing where users can revert to any previous version.
 *
 * @example
 * const {
 *   currentVersion,
 *   canUndo,
 *   canRedo,
 *   undo,
 *   redo,
 *   pushVersion,
 *   versionCount
 * } = useVersionHistory(initialContent);
 */

import { useState, useCallback, useMemo } from 'react';

/**
 * Generate a unique ID for versions
 * @returns {string} UUID-like identifier
 */
function generateId() {
  return `v-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Version history hook for managing article content versions
 *
 * @param {Object} initialContent - Initial article content
 * @param {string} initialContent.title - Article title
 * @param {string} initialContent.linhaFina - Article subtitle
 * @param {string} initialContent.body - Article body content
 * @param {string[]} initialContent.tags - Article tags
 * @param {Object} options - Hook options
 * @param {number} [options.maxVersions=50] - Maximum versions to keep in history
 * @returns {Object} Version history state and controls
 */
export function useVersionHistory(initialContent, options = {}) {
  const maxVersions = options.maxVersions || 50;

  // Initialize history with the initial content as first version
  const [history, setHistory] = useState(() => ({
    versions: [
      {
        id: generateId(),
        timestamp: Date.now(),
        source: 'initial',
        label: 'Versão inicial',
        chatMessageId: null,
        content: {
          title: initialContent?.title || '',
          tituloCurto: initialContent?.tituloCurto || '',
          linhaFina: initialContent?.linhaFina || '',
          body: initialContent?.body || initialContent?.content || '',
          tags: initialContent?.tags || []
        }
      }
    ],
    currentIndex: 0
  }));

  // Current version content
  const currentVersion = useMemo(() => {
    return history.versions[history.currentIndex];
  }, [history.versions, history.currentIndex]);

  // Navigation state
  const canUndo = history.currentIndex > 0;
  const canRedo = history.currentIndex < history.versions.length - 1;

  /**
   * Go to previous version (undo)
   */
  const undo = useCallback(() => {
    if (!canUndo) return;

    setHistory((prev) => ({
      ...prev,
      currentIndex: prev.currentIndex - 1
    }));
  }, [canUndo]);

  /**
   * Go to next version (redo)
   */
  const redo = useCallback(() => {
    if (!canRedo) return;

    setHistory((prev) => ({
      ...prev,
      currentIndex: prev.currentIndex + 1
    }));
  }, [canRedo]);

  /**
   * Jump to a specific version by ID
   * @param {string} versionId - ID of the version to restore
   */
  const goToVersion = useCallback((versionId) => {
    setHistory((prev) => {
      const targetIndex = prev.versions.findIndex((v) => v.id === versionId);
      if (targetIndex === -1) return prev;

      return {
        ...prev,
        currentIndex: targetIndex
      };
    });
  }, []);

  /**
   * Create a new version with updated content
   *
   * @param {Object} content - New content for the version
   * @param {string} content.title - Article title
   * @param {string} content.linhaFina - Article subtitle
   * @param {string} content.body - Article body content
   * @param {string[]} content.tags - Article tags
   * @param {string} source - Source of the change: 'ai' | 'user' | 'initial'
   * @param {string} label - Human-readable label for the version
   * @param {string} [chatMessageId] - Optional ID linking to chat message that triggered this change
   */
  const pushVersion = useCallback((content, source, label, chatMessageId = null) => {
    setHistory((prev) => {
      // Truncate any "future" versions if we're not at the end
      // (user made edits after undoing, discarding redo history)
      const truncatedVersions = prev.versions.slice(0, prev.currentIndex + 1);

      // Create new version
      const newVersion = {
        id: generateId(),
        timestamp: Date.now(),
        source,
        label,
        chatMessageId,
        content: {
          title: content.title ?? '',
          tituloCurto: content.tituloCurto ?? '',
          linhaFina: content.linhaFina ?? '',
          body: content.body ?? content.content ?? '',
          tags: content.tags ?? []
        }
      };

      // Add new version
      let newVersions = [...truncatedVersions, newVersion];

      // Limit to maxVersions (remove oldest, keeping initial)
      if (newVersions.length > maxVersions) {
        // Keep the first version (initial) and the most recent ones
        newVersions = [
          newVersions[0],
          ...newVersions.slice(-(maxVersions - 1))
        ];
      }

      return {
        versions: newVersions,
        currentIndex: newVersions.length - 1
      };
    });
  }, [maxVersions]);

  /**
   * Update the current version content without creating a new version
   * Useful for real-time user edits before an AI edit is applied
   *
   * @param {Object} content - Updated content
   */
  const updateCurrentContent = useCallback((content) => {
    setHistory((prev) => {
      const newVersions = [...prev.versions];
      const currentIndex = prev.currentIndex;

      // Only update if we're on a user-editable version
      // and the source is 'user' or 'initial'
      newVersions[currentIndex] = {
        ...newVersions[currentIndex],
        content: {
          ...newVersions[currentIndex].content,
          ...content
        },
        timestamp: Date.now()
      };

      return {
        ...prev,
        versions: newVersions
      };
    });
  }, []);

  /**
   * Reset history to initial state with new content
   * @param {Object} newInitialContent - New initial content
   */
  const resetHistory = useCallback((newInitialContent) => {
    setHistory({
      versions: [
        {
          id: generateId(),
          timestamp: Date.now(),
          source: 'initial',
          label: 'Versão inicial',
          chatMessageId: null,
          content: {
            title: newInitialContent?.title || '',
            tituloCurto: newInitialContent?.tituloCurto || '',
            linhaFina: newInitialContent?.linhaFina || '',
            body: newInitialContent?.body || newInitialContent?.content || '',
            tags: newInitialContent?.tags || []
          }
        }
      ],
      currentIndex: 0
    });
  }, []);

  return {
    // Current state
    currentVersion,
    currentContent: currentVersion?.content,

    // Navigation
    canUndo,
    canRedo,
    undo,
    redo,
    goToVersion,

    // Version management
    pushVersion,
    updateCurrentContent,
    resetHistory,

    // History info
    versions: history.versions,
    versionCount: history.versions.length,
    currentIndex: history.currentIndex
  };
}

export default useVersionHistory;
