/**
 * Simple Markdown Renderer
 *
 * Converts basic markdown to HTML for preview display.
 * Supports: bold, italic, subtitles, paragraphs
 */

/**
 * Convert markdown text to HTML
 * @param {string} text - Markdown text
 * @returns {string} HTML string
 */
export function markdownToHtml(text) {
  if (!text) return '';

  let html = text
    // Escape HTML first
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Bold: **text** or __text__
    .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-dark-gray">$1</strong>')
    .replace(/__(.+?)__/g, '<strong class="font-semibold text-dark-gray">$1</strong>')
    // Italic: *text* or _text_
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/_(.+?)_/g, '<em>$1</em>')
    // Subtitles: ## text
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-bold text-dark-gray mt-6 mb-3">$1</h2>')
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold text-dark-gray mt-4 mb-2">$1</h3>')
    // Paragraphs: double newlines
    .split(/\n\n+/)
    .map(para => {
      // Don't wrap headings in paragraphs
      if (para.startsWith('<h2') || para.startsWith('<h3')) {
        return para;
      }
      return `<p class="mb-4 leading-relaxed">${para.replace(/\n/g, '<br>')}</p>`;
    })
    .join('');

  return html;
}

/**
 * Strip markdown formatting from text
 * @param {string} text - Markdown text
 * @returns {string} Plain text without markdown
 */
export function stripMarkdown(text) {
  if (!text) return '';

  return text
    // Remove bold
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    // Remove italic
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/_(.+?)_/g, '$1')
    // Remove subtitles markers
    .replace(/^#{1,3} /gm, '');
}

/**
 * Count words in text (ignoring markdown)
 * @param {string} text - Text with potential markdown
 * @returns {number} Word count
 */
export function countWords(text) {
  const plain = stripMarkdown(text);
  return plain.split(/\s+/).filter(Boolean).length;
}
