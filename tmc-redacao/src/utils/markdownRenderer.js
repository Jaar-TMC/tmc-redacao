/**
 * Markdown Renderer
 *
 * Converts markdown to HTML for preview display.
 * Supports: links, bold, italic, subtitles, lists, blockquotes, paragraphs
 */

/**
 * Convert markdown text to HTML
 * @param {string} text - Markdown text
 * @returns {string} HTML string
 */
export function markdownToHtml(text) {
  if (!text) return '';

  let html = text;

  // Step 0: NORMALIZE LINE ENDINGS (critical for regex anchors to work)
  // Windows uses \r\n, old Mac uses \r, Unix uses \n
  html = html.replace(/\r\n/g, '\n');  // Windows → Unix
  html = html.replace(/\r/g, '\n');     // Old Mac → Unix

  // Ensure headings (## and ###) start on their own line
  // This handles cases where AI outputs "text## Heading" on same line
  html = html.replace(/([^\n])(#{2,3}\s)/g, '$1\n\n$2');

  // Remove leading whitespace before heading markers (keeps the ##)
  html = html.replace(/^\s+(#{2,3}\s)/gm, '$1');

  // Ensure list markers (- item) are on their own line
  // Handle cases like "text- Item1 - Item2" converting to proper lines
  html = html.replace(/([^\n\s-])\s*-\s+/g, '$1\n- ');

  // Check if content already has HTML (to avoid double-processing)
  const hasExistingHtml = /<[a-z][^>]*>/i.test(html);

  // Step 1: Handle BLOCKQUOTES first (detect > at line start)
  // Only if not already HTML
  if (!hasExistingHtml) {
    html = html.replace(
      /^>\s+(.+)$/gm,
      '{{BLOCKQUOTE}}$1{{/BLOCKQUOTE}}'
    );
  }

  // Step 2: Escape & for HTML entities (only if not already HTML)
  if (!hasExistingHtml) {
    html = html.replace(/&(?!amp;|lt;|gt;|quot;|#)/g, '&amp;');
  }

  // Step 3: Handle MARKDOWN LINKS [text](url) - this is the primary link format
  // This should always run to catch any markdown links in the content
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );

  // Step 4: Handle URLs in parentheses (https://...) - fallback for AI output
  // Only match if not already part of a markdown link or href
  // Match pattern: (https://...) but not after ](
  html = html.replace(
    /(?<!\])\((https?:\/\/[^\s)]+)\)/g,
    '(<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>)'
  );

  // Step 5: Convert blockquote placeholders to HTML
  html = html.replace(
    /{{BLOCKQUOTE}}(.+?){{\/BLOCKQUOTE}}/g,
    '<blockquote class="border-l-4 border-tmc-orange pl-4 italic my-4 text-medium-gray">$1</blockquote>'
  );

  // Step 5b: Handle BOLD/ITALIC (always run, even with existing HTML)
  // Bold text `**text**` doesn't conflict with existing HTML tags
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong class="font-semibold">$1</strong>');
  // Italic: *text* or _text_ (careful not to match inside URLs or list markers)
  html = html.replace(/(?<![*\w])\*([^*\n]+?)\*(?![*\w])/g, '<em>$1</em>');
  html = html.replace(/(?<![_\w])_([^_\n]+?)_(?![_\w])/g, '<em>$1</em>');

  // Step 5c: Pre-process lists (always run, even with existing HTML)
  // This MUST run before the hasExistingHtml check

  // First, remove empty list markers (lines with just "- " or "* " and nothing else)
  // This prevents empty <li> items from being created
  html = html.replace(/^\s*[-*]\s*$/gm, '');

  // Split multiple items on same line
  // Example: "- Mato Grosso - Goiás - Paraná" should become 3 separate <li> items
  html = html.split('\n').map(line => {
    // Check if line starts with a list marker (with optional leading space)
    if (/^\s*[-*]\s+/.test(line)) {
      // Split on " - " pattern (space-dash-space) to separate multiple items
      // But preserve the first marker
      const parts = line.split(/\s+-\s+/);
      if (parts.length > 1) {
        // Filter out empty parts (from trailing " - " or edge cases)
        return parts
          .map((part, i) => i === 0 ? part : '- ' + part)
          .filter(part => part.trim() && part.trim() !== '-')
          .join('\n');
      }
    }
    return line;
  }).join('\n');

  // Remove any remaining empty lines that are just whitespace
  html = html.replace(/^\s*$/gm, '').replace(/\n{3,}/g, '\n\n');

  // Step 6: Handle HEADINGS - ALWAYS convert, even with existing HTML
  // This is critical for AI responses that mix HTML links with markdown headings
  // Only convert if the ## is at the start of a line (not inside HTML tags)
  html = html.replace(/^## (.+)$/gm, '<h2 class="text-lg font-bold text-dark-gray mt-6 mb-3">$1</h2>');
  html = html.replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold text-dark-gray mt-4 mb-2">$1</h3>');

  // Step 7: Handle LISTS - ALWAYS convert, even with existing HTML
  // Process bullet lists: - item or * item (with optional leading whitespace)
  html = html.replace(
    /^\s*[-*]\s+(.+)$/gm,
    '{{BULLET_ITEM}}$1{{/BULLET_ITEM}}'
  );

  // Process numbered lists: 1. item (with optional leading whitespace)
  html = html.replace(
    /^\s*\d+\.\s+(.+)$/gm,
    '{{NUMBERED_ITEM}}$1{{/NUMBERED_ITEM}}'
  );

  // Wrap consecutive bullet items in <ul>
  // IMPORTANT: No newlines inside <ul>/<li> structure - TipTap interprets them as content
  html = html.replace(
    /({{BULLET_ITEM}}[\s\S]*?{{\/BULLET_ITEM}}\n?)+/g,
    (match) => {
      const items = match
        .split(/{{BULLET_ITEM}}|{{\/BULLET_ITEM}}/)
        .filter(item => item.trim())
        .map(item => `<li class="ml-4">${item.trim()}</li>`)
        .join('');  // No newlines between items
      return `<ul class="list-disc list-inside my-4 space-y-1">${items}</ul>`;
    }
  );

  // Wrap consecutive numbered items in <ol>
  // IMPORTANT: No newlines inside <ol>/<li> structure - TipTap interprets them as content
  html = html.replace(
    /({{NUMBERED_ITEM}}[\s\S]*?{{\/NUMBERED_ITEM}}\n?)+/g,
    (match) => {
      const items = match
        .split(/{{NUMBERED_ITEM}}|{{\/NUMBERED_ITEM}}/)
        .filter(item => item.trim())
        .map(item => `<li class="ml-4">${item.trim()}</li>`)
        .join('');  // No newlines between items
      return `<ol class="list-decimal list-inside my-4 space-y-1">${items}</ol>`;
    }
  );

  // If content already has HTML, skip ONLY paragraph wrapping
  // (which can break existing HTML structure)
  if (hasExistingHtml) {
    return html;
  }

  // Step 8: Handle PARAGRAPHS (split by double newlines)
  html = html
    .split(/\n\n+/)
    .map(para => {
      const trimmed = para.trim();
      // Don't wrap elements that are already block-level
      if (
        trimmed.startsWith('<h2') ||
        trimmed.startsWith('<h3') ||
        trimmed.startsWith('<ul') ||
        trimmed.startsWith('<ol') ||
        trimmed.startsWith('<blockquote')
      ) {
        return trimmed;
      }
      // Wrap text in paragraphs
      if (trimmed) {
        return `<p class="mb-4 leading-relaxed">${trimmed.replace(/\n/g, '<br>')}</p>`;
      }
      return '';
    })
    .filter(Boolean)
    .join('\n');

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
    // Remove markdown links, keep text: [text](url) -> text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove bold
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    // Remove italic
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/_(.+?)_/g, '$1')
    // Remove subtitles markers
    .replace(/^#{1,3} /gm, '')
    // Remove list markers
    .replace(/^[-*]\s+/gm, '')
    .replace(/^\d+\.\s+/gm, '')
    // Remove blockquote markers
    .replace(/^>\s+/gm, '');
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
