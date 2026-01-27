/**
 * Article Transformers
 *
 * Reusable transformation functions to convert API responses
 * to the format expected by frontend components.
 */

/**
 * Transform a single article from API format to frontend format
 * @param {Object} article - Raw article from API
 * @returns {Object} Transformed article for frontend use
 */
export const transformArticle = (article) => {
  // Always use Google's favicon API for reliability (handles 404s, caching, etc.)
  // API-provided favicons are often broken or inaccessible
  let favicon;
  try {
    const url = article.link || article.url || 'https://example.com';
    const hostname = new URL(url).hostname;
    favicon = `https://www.google.com/s2/favicons?domain=${hostname}&sz=32`;
  } catch {
    favicon = 'https://www.google.com/s2/favicons?domain=example.com&sz=32';
  }

  // API returns 'publishedAt', legacy format uses 'published_at'
  // Also check 'collectedAt' as fallback since some articles might not have publishedAt
  const publishedAtRaw = article.publishedAt || article.published_at || article.collectedAt || article.collected_at;

  // Parse the date - API returns UTC dates without 'Z' suffix, so add it if missing
  let publishedAt = new Date();
  if (publishedAtRaw) {
    // If the date string doesn't end with Z or timezone offset, treat it as UTC
    const dateStr = typeof publishedAtRaw === 'string' && !publishedAtRaw.endsWith('Z') && !publishedAtRaw.match(/[+-]\d{2}:\d{2}$/)
      ? publishedAtRaw + 'Z'
      : publishedAtRaw;
    const parsed = new Date(dateStr);
    if (!isNaN(parsed.getTime())) {
      publishedAt = parsed;
    }
  }

  return {
    id: article.id,
    title: article.title,
    preview: article.preview || article.summary || article.content?.substring(0, 200) || '',
    content: article.content,
    category: article.category || 'Geral',
    source: article.source_name || article.source,
    url: article.link || article.url,
    favicon,
    publishedAt,
    tags: article.tags || []
  };
};

/**
 * Transform an array of articles from API format to frontend format
 * @param {Array} articles - Array of raw articles from API
 * @returns {Array} Array of transformed articles
 */
export const transformArticles = (articles) => (articles || []).map(transformArticle);

/**
 * Transform sources from API format to frontend format
 * @param {Array} sources - Array of sources from API
 * @returns {Array} Array of transformed sources
 */
export const transformSources = (sources) => (sources || []).map((source, index) => {
  // Always use Google's favicon API for reliability (handles 404s, caching, etc.)
  // Extract domain from source URL for best results
  let domain = '';
  try {
    if (source.url) {
      domain = new URL(source.url).hostname;
    }
  } catch {
    // Fallback: generate domain from source name
    domain = `${source.name.toLowerCase().replace(/[^a-z0-9]/g, '')}.com`;
  }

  // Google's favicon API is more reliable than direct favicon.ico URLs
  const favicon = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;

  return {
    id: source.id || index + 1,
    name: source.name,
    url: source.url || source.feed_url,
    favicon,
    active: source.active !== false,
    category: source.category || null,
    frequency: source.frequency || '1h',
    last_fetch: source.last_fetch || source.lastFetch || null
  };
});

/**
 * Transform categories from API format to frontend format
 * @param {Array} categories - Array of categories from API
 * @returns {Array} Array of transformed categories with counts
 */
export const transformCategories = (categories) => (categories || []).map((cat, index) => ({
  id: index + 1,
  name: typeof cat === 'string' ? cat : (cat.name || cat.category),
  count: typeof cat === 'object' ? (cat.count || 0) : 0
}));

/**
 * Compute trending themes from articles by counting DISTINCT articles per tag
 * @param {Array} articles - Array of articles
 * @returns {Array} Array of theme objects sorted by count (distinct article count per tag)
 */
export const computeFeedThemes = (articles) => {
  if (!articles || articles.length === 0) return [];

  // Track distinct articles per tag using Sets
  // Key: normalized tag, Value: Set of article IDs
  const tagArticles = {};

  articles.forEach(article => {
    if (article.tags && article.tags.length > 0) {
      // Use a Set to avoid counting the same tag multiple times for the same article
      const seenTags = new Set();

      article.tags.forEach(tag => {
        // Skip very short tags, generic source names, and empty tags
        if (tag && tag.length > 2 && !isGenericTag(tag)) {
          // Normalize tag: lowercase, trim
          const normalizedTag = tag.toLowerCase().trim();

          // Only count this tag once per article
          if (!seenTags.has(normalizedTag)) {
            seenTags.add(normalizedTag);

            // Add article ID to the tag's Set
            if (!tagArticles[normalizedTag]) {
              tagArticles[normalizedTag] = new Set();
            }
            tagArticles[normalizedTag].add(article.id);
          }
        }
      });
    }
  });

  // Convert to array with distinct article counts, sorted by count
  const themes = Object.entries(tagArticles)
    .map(([theme, articleIds], index) => ({
      id: index + 1,
      theme: formatTagForDisplay(theme),
      count: articleIds.size, // Distinct article count
      trend: 'stable'
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 15); // Top 15 trending tags

  return themes;
};

/**
 * Check if a tag is generic (source name, etc) and should be excluded
 * @param {string} tag - Tag to check
 * @returns {boolean} True if tag should be excluded
 */
const isGenericTag = (tag) => {
  const genericTags = [
    'g1', 'globo', 'folha', 'uol', 'estadao', 'cnn', 'bbc',
    'r7', 'terra', 'ig', 'globoesporte', 'tecmundo', 'infomoney'
  ];
  return genericTags.includes(tag.toLowerCase().trim());
};

/**
 * Format a tag for display (capitalize first letter of each word)
 * @param {string} tag - Tag to format
 * @returns {string} Formatted tag
 */
const formatTagForDisplay = (tag) => {
  return tag
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};
