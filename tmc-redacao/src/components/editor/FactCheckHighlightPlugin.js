import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import { Extension } from '@tiptap/core';

export const factCheckPluginKey = new PluginKey('factCheckHighlight');

export const FactCheckHighlightPlugin = Extension.create({
  name: 'factCheckHighlight',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: factCheckPluginKey,

        state: {
          init() {
            return { decorations: DecorationSet.empty, visible: true };
          },

          apply(tr, oldState) {
            const meta = tr.getMeta(factCheckPluginKey);

            if (meta) {
              if (meta.type === 'setDecorations') {
                return { decorations: meta.decorations, visible: true };
              }

              if (meta.type === 'toggleVisibility') {
                return { decorations: oldState.decorations, visible: !oldState.visible };
              }

              if (meta.type === 'clear') {
                return { decorations: DecorationSet.empty, visible: true };
              }
            }

            if (tr.docChanged) {
              return {
                decorations: oldState.decorations.map(tr.mapping, tr.doc),
                visible: oldState.visible,
              };
            }

            return oldState;
          },
        },

        props: {
          decorations(state) {
            const pluginState = factCheckPluginKey.getState(state);
            if (!pluginState) return DecorationSet.empty;
            return pluginState.visible ? pluginState.decorations : DecorationSet.empty;
          },
        },
      }),
    ];
  },
});

/**
 * Build a text index from the ProseMirror document, mapping character offsets
 * in the concatenated plaintext back to ProseMirror positions.
 */
function buildTextIndex(doc) {
  const segments = [];
  let offset = 0;

  doc.descendants((node, pos) => {
    if (node.isText) {
      segments.push({ from: pos, to: pos + node.nodeSize, text: node.text, offset });
      offset += node.text.length;
    } else if (node.isBlock && segments.length > 0) {
      // Add a space between blocks to avoid false matches across paragraphs
      offset += 1;
    }
    return true;
  });

  return segments;
}

/**
 * Find the ProseMirror from/to positions for a given search string within
 * the document, using the pre-built text index.
 *
 * Uses case-insensitive matching on raw text (no whitespace normalization)
 * to ensure character offsets map correctly back to ProseMirror positions.
 *
 * Returns { from, to } or null if not found.
 */
function findTextInDoc(segments, searchStr) {
  if (!searchStr || segments.length === 0) return null;

  // Build the concatenated plaintext (raw, no normalization)
  const fullText = segments.reduce((acc, seg) => {
    const gap = seg.offset - acc.length;
    return acc + ' '.repeat(Math.max(0, gap)) + seg.text;
  }, '');

  // Case-insensitive search on raw text
  const charIndex = fullText.toLowerCase().indexOf(searchStr.toLowerCase());
  if (charIndex === -1) return null;

  const charEnd = charIndex + searchStr.length;

  // Map character positions back to ProseMirror positions
  let pmFrom = null;
  let pmTo = null;

  for (const seg of segments) {
    const segStart = seg.offset;
    const segEnd = seg.offset + seg.text.length;

    // Find the segment containing charIndex
    if (pmFrom === null && charIndex >= segStart && charIndex < segEnd) {
      pmFrom = seg.from + (charIndex - segStart);
    }

    // Find the segment containing charEnd
    if (pmTo === null && charEnd > segStart && charEnd <= segEnd) {
      pmTo = seg.from + (charEnd - segStart);
    }

    if (pmFrom !== null && pmTo !== null) break;
  }

  if (pmFrom === null || pmTo === null) return null;
  return { from: pmFrom, to: pmTo };
}

/**
 * Apply fact-check highlight decorations to the editor.
 *
 * @param {import('@tiptap/core').Editor} editor - TipTap editor instance
 * @param {Array<{text: string, verdict: string, severity?: string, category?: string, evidence?: string, position_hint?: string}>} claims
 */
const VALID_VERDICTS = new Set(['grounded', 'fabricated', 'unverifiable', 'opinion']);

export function applyFactCheckDecorations(editor, claims) {
  if (!editor || !claims || claims.length === 0) return;

  const { state } = editor;
  const { doc, tr } = state;
  const segments = buildTextIndex(doc);
  const decorations = [];

  claims.forEach((claim, index) => {
    // Skip grounded claims — they are safe
    if (claim.verdict === 'grounded') return;

    // Validate verdict against whitelist for safe CSS class construction
    const safeVerdict = VALID_VERDICTS.has(claim.verdict) ? claim.verdict : 'unverifiable';

    // Try position_hint first, fall back to claim text
    const searchText = claim.position_hint || claim.text;
    const result = findTextInDoc(segments, searchText);

    // If position_hint failed and it's different from text, try text as fallback
    if (!result && claim.position_hint && claim.position_hint !== claim.text) {
      const fallbackResult = findTextInDoc(segments, claim.text);
      if (fallbackResult) {
        decorations.push(
          Decoration.inline(fallbackResult.from, fallbackResult.to, {
            class: `fc-highlight fc-${safeVerdict}`,
            'data-claim-index': String(index),
            'data-verdict': claim.verdict,
            'data-severity': claim.severity || 'medium',
          })
        );
      }
      return;
    }

    if (result) {
      decorations.push(
        Decoration.inline(result.from, result.to, {
          class: `fc-highlight fc-${safeVerdict}`,
          'data-claim-index': String(index),
          'data-verdict': claim.verdict,
          'data-severity': claim.severity || 'medium',
        })
      );
    }
  });

  const decorationSet = DecorationSet.create(doc, decorations);

  editor.view.dispatch(
    tr.setMeta(factCheckPluginKey, { type: 'setDecorations', decorations: decorationSet })
  );
}

/**
 * Clear all fact-check decorations from the editor.
 *
 * @param {import('@tiptap/core').Editor} editor
 */
export function clearFactCheckDecorations(editor) {
  if (!editor) return;

  const { tr } = editor.state;
  editor.view.dispatch(tr.setMeta(factCheckPluginKey, { type: 'clear' }));
}

/**
 * Toggle visibility of fact-check decorations without removing them.
 *
 * @param {import('@tiptap/core').Editor} editor
 */
export function toggleFactCheckVisibility(editor) {
  if (!editor) return;

  const { tr } = editor.state;
  editor.view.dispatch(tr.setMeta(factCheckPluginKey, { type: 'toggleVisibility' }));
}
