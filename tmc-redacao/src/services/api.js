/**
 * API Service Layer for TMC Redação
 *
 * Centralized API calls with error handling and configuration.
 * Connects frontend to the Azure Functions backend.
 * Supports both standalone development and WordPress plugin contexts.
 */

/**
 * Get the API base URL from WordPress config or environment variable
 * @returns {string} API base URL
 */
function getBaseUrl() {
  // First, check WordPress configuration (set via wp_localize_script)
  if (typeof window !== 'undefined' && window.tmcRedacaoConfig?.apiBaseUrl) {
    return window.tmcRedacaoConfig.apiBaseUrl;
  }

  // Fallback to environment variable (standalone development)
  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:7071/api';
}

// API Base URL - evaluated on each call to support dynamic WordPress config
const getApiBaseUrl = () => getBaseUrl();

// Auth handler registration (avoids circular import with auth.js)
let _getAuthToken = null;
let _onUnauthorized = null;

/**
 * Register auth handlers for token injection and 401 handling.
 * Called by AuthContext on mount to wire up auth without circular imports.
 * @param {() => string|null} getToken - Returns current access token
 * @param {() => void} onUnauth - Called on 401 response
 */
export function registerAuthHandlers(getToken, onUnauth) {
  _getAuthToken = getToken;
  _onUnauthorized = onUnauth;
}

/**
 * Get current auth token via registered handler.
 * Exported so AuthContext can pass it to registerAuthHandlers without circular ref.
 * @returns {string|null}
 */
export function getAuthToken() {
  return _getAuthToken ? _getAuthToken() : null;
}

/**
 * Custom error class for API errors
 */
class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Base fetch wrapper with error handling
 * @param {string} endpoint - API endpoint (without base URL)
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<any>} Response data
 */
async function fetchApi(endpoint, options = {}) {
  const url = `${getApiBaseUrl()}${endpoint}`;

  // Extract signal separately to ensure it's passed through
  const { signal, headers: customHeaders, ...restOptions } = options;

  // Only add Content-Type for requests with body (POST, PUT, etc.)
  const headers = { ...customHeaders };
  if (restOptions.body) {
    headers['Content-Type'] = 'application/json';
  }

  // Inject Authorization header if token is available
  const token = _getAuthToken ? _getAuthToken() : null;
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = { ...restOptions, headers, signal, credentials: 'include' };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      if (response.status === 401 && _onUnauthorized) {
        _onUnauthorized();
      }
      const errorData = await response.json().catch(() => null);
      throw new ApiError(
        errorData?.error || `HTTP error ${response.status}`,
        response.status,
        errorData
      );
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }

    return null;
  } catch (error) {
    // Re-throw AbortError without wrapping
    if (error.name === 'AbortError') {
      throw error;
    }

    if (error instanceof ApiError) {
      throw error;
    }

    // Network error or other issues
    throw new ApiError(
      error.message || 'Erro de conexão com o servidor',
      0,
      null
    );
  }
}

// ============================================
// Health Check
// ============================================

/**
 * Check API health status
 * @returns {Promise<{status: string, timestamp: string}>}
 */
export async function checkHealth() {
  return fetchApi('/health');
}

// ============================================
// RSS Articles API
// ============================================

/**
 * Get articles from RSS feed
 * @param {Object} params - Query parameters
 * @param {string} [params.source] - Filter by source name
 * @param {string} [params.category] - Filter by category
 * @param {number} [params.limit=20] - Max articles to return (max: 100)
 * @param {number} [params.page=1] - Page number for pagination
 * @param {string} [params.search] - Search query
 * @param {string} [params.tag] - Filter by exact tag match
 * @param {Object} [options] - Fetch options
 * @param {AbortSignal} [options.signal] - AbortController signal for cancellation
 * @returns {Promise<{items: Array, total: number, page: number, pages: number}>}
 */
export async function getArticles(params = {}, options = {}) {
  const queryParams = new URLSearchParams();

  if (params.source) queryParams.append('source', params.source);
  if (params.category) queryParams.append('category', params.category);
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.search) queryParams.append('search', params.search);
  if (params.tag) queryParams.append('tag', params.tag);
  if (params.max_hours) queryParams.append('max_hours', params.max_hours.toString());

  const queryString = queryParams.toString();
  const endpoint = `/articles${queryString ? `?${queryString}` : ''}`;

  return fetchApi(endpoint, options);
}

/**
 * Get a single article by ID
 * @param {number} articleId - Article ID
 * @returns {Promise<Object>} Article data
 */
export async function getArticle(articleId) {
  return fetchApi(`/articles/${articleId}`);
}

// ============================================
// RSS Sources API
// ============================================

/**
 * Get all RSS sources
 * @returns {Promise<{items: Array, total: number}>}
 */
export async function getSources() {
  return fetchApi('/sources');
}

/**
 * Create a new RSS source
 * @param {Object} sourceData - Source data
 * @param {string} sourceData.name - Source name
 * @param {string} sourceData.url - RSS feed URL
 * @param {string} [sourceData.category] - Category
 * @param {string} [sourceData.frequency] - Collection frequency (15min, 30min, 1h, 2h, 6h)
 * @param {boolean} [sourceData.active] - Whether source is active
 * @returns {Promise<Object>} Created source
 */
export async function createSource(sourceData) {
  return fetchApi('/sources', {
    method: 'POST',
    body: JSON.stringify(sourceData),
  });
}

/**
 * Update an existing RSS source
 * @param {string} sourceId - Source ID
 * @param {Object} sourceData - Fields to update
 * @returns {Promise<Object>} Updated source
 */
export async function updateSource(sourceId, sourceData) {
  return fetchApi(`/sources/${sourceId}`, {
    method: 'PUT',
    body: JSON.stringify(sourceData),
  });
}

/**
 * Delete (deactivate) an RSS source
 * @param {string} sourceId - Source ID
 * @returns {Promise<{message: string}>}
 */
export async function deleteSource(sourceId) {
  return fetchApi(`/sources/${sourceId}`, {
    method: 'DELETE',
  });
}

/**
 * Trigger manual collection for a source
 * @param {string} sourceId - Source ID
 * @returns {Promise<Object>} Collection result
 */
export async function collectSource(sourceId) {
  return fetchApi(`/sources/${sourceId}/collect`, {
    method: 'POST',
  });
}

/**
 * Get available categories with article counts.
 * Accepts optional filter params for contextual counts.
 * @param {Object} [params] - Optional filter context
 * @param {string} [params.search] - Active search filter
 * @param {string} [params.tag] - Active tag filter
 * @param {string} [params.source] - Active source filter
 * @param {number} [params.max_hours] - Active urgency filter
 * @returns {Promise<{categories: Array<{name: string, count: number}>}>}
 */
export async function getCategories(params = {}) {
  const queryParams = new URLSearchParams();

  if (params.search) queryParams.append('search', params.search);
  if (params.tag) queryParams.append('tag', params.tag);
  if (params.source) queryParams.append('source', params.source);
  if (params.max_hours) queryParams.append('max_hours', params.max_hours.toString());

  const queryString = queryParams.toString();
  return fetchApi(`/categories${queryString ? `?${queryString}` : ''}`);
}

/**
 * Get trending tags with article counts from ALL articles in database
 * This is the source of truth for "Feed em Alta" / "Temas Quentes"
 * @param {Object} params - Query parameters
 * @param {number} [params.limit=20] - Maximum tags to return (max: 50)
 * @param {number} [params.period] - Optional filter for articles within last N hours
 * @returns {Promise<{items: Array<{id: number, theme: string, tag: string, count: number, trend: string}>, total: number}>}
 */
export async function getTrendingTags(params = {}) {
  const queryParams = new URLSearchParams();

  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.period) queryParams.append('period', params.period.toString());

  const queryString = queryParams.toString();
  const endpoint = `/trending-tags${queryString ? `?${queryString}` : ''}`;

  return fetchApi(endpoint);
}

/**
 * Get ALL unique tags with article counts
 * Use for tag filter dropdown
 * @param {Object} params - Query parameters
 * @param {string} [params.search] - Optional search term to filter tags
 * @returns {Promise<{items: Array<{id: number, theme: string, tag: string, count: number}>, total: number}>}
 */
export async function getAllTags(params = {}) {
  const queryParams = new URLSearchParams();

  if (params.search) queryParams.append('search', params.search);
  if (params.category) queryParams.append('category', params.category);
  if (params.source) queryParams.append('source', params.source);
  if (params.max_hours) queryParams.append('max_hours', params.max_hours.toString());

  const queryString = queryParams.toString();
  const endpoint = `/tags${queryString ? `?${queryString}` : ''}`;

  return fetchApi(endpoint);
}

// ============================================
// AI Generation API
// ============================================

/**
 * Generate article using AI
 * @param {Object} params - Generation parameters
 * @param {string} params.texto_base - Source text content
 * @param {string} [params.persona] - Writer persona - LEGACY (imparcial|especialista|colunista|influencer)
 * @param {string} params.tom - Writing tone (varies by category)
 * @param {string} [params.orientacao_lide] - Lead paragraph guidance
 * @param {string[]} [params.citacoes] - Quotes to include
 * @param {string} [params.contexto] - Background context
 * @param {string} [params.creditos] - Source credits
 * @param {string} [params.tipo_materia] - Article type (destaque|coluna|servico|etc)
 * @param {string[]} [params.tags] - User-selected tags for SEO optimization
 * @param {string} [params.categoria] - Editorial category (esportes|entretenimento|politica|economia|geral) - NEW
 * @param {boolean} [params.modo_opinativo] - Enable opinion mode for categories that allow it - NEW
 * @returns {Promise<{titulo: string, linha_fina: string, conteudo: string, tags_sugeridas: string[]}>}
 */
export async function generateArticle(params) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 90000);

  try {
    const response = await fetchApi('/generate', {
      method: 'POST',
      body: JSON.stringify(params),
      signal: controller.signal,
    });
    return response;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('A geracao demorou mais que o esperado. Tente novamente.');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Generate topics from source text
 * @param {Object} params - Extraction parameters
 * @param {string} params.texto - Source text
 * @returns {Promise<{topics: Array<{type: string, content: string}>}>}
 */
export async function extractTopics(params) {
  return fetchApi('/extract-topics', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

/**
 * Generate suggested tags for content
 * @param {Object} params - Tag generation parameters
 * @param {string} params.texto - Content to analyze
 * @returns {Promise<{tags: string[]}>}
 */
export async function generateTags(params) {
  return fetchApi('/generate-tags', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

/**
 * Edit an existing article using AI
 *
 * Allows incremental edits to article content via chat with AI.
 * Supports version history (undo/redo) on the frontend.
 *
 * @param {Object} params - Edit parameters
 * @param {Object} params.currentArticle - Current article state
 * @param {string} params.currentArticle.title - Current title
 * @param {string} params.currentArticle.linhaFina - Current subtitle
 * @param {string} params.currentArticle.content - Current body content
 * @param {string[]} params.currentArticle.tags - Current tags
 * @param {string} params.instruction - User's edit instruction (e.g., "Melhore o SEO do título")
 * @param {string} [params.editScope="full"] - Scope: "full"|"title"|"linha_fina"|"content"|"tags"
 * @param {string} [params.categoria="geral"] - Editorial category
 * @param {string} [params.tom="conversacional"] - Writing tone
 * @returns {Promise<{
 *   titulo: string,
 *   linha_fina: string,
 *   conteudo: string,
 *   tags: string[],
 *   changes_summary: string
 * }>}
 */
export async function editArticle({
  currentArticle,
  instruction,
  editScope = 'full',
  categoria = 'geral',
  tom = 'conversacional'
}) {
  return fetchApi('/edit-article', {
    method: 'POST',
    body: JSON.stringify({
      current_article: {
        title: currentArticle.title,
        linha_fina: currentArticle.linhaFina,
        content: currentArticle.content,
        tags: currentArticle.tags || []
      },
      instruction,
      edit_scope: editScope,
      categoria,
      tom
    })
  });
}

/**
 * Merge topics from multiple articles into a story-centric structure.
 *
 * Transforms article-by-article view into unified story view,
 * grouping content by story element (fact, context, reaction, etc.)
 * instead of by source.
 *
 * @param {Object[]} articles - Articles to merge (max 3)
 * @param {string|number} articles[].id - Article identifier
 * @param {string} articles[].title - Article title
 * @param {string} articles[].content - Article content
 * @param {string} [articles[].preview] - Article preview (fallback for content)
 * @param {string} articles[].source - Source name
 * @returns {Promise<{
 *   groups: Array<{
 *     id: string,
 *     type: string,
 *     label: string,
 *     versions: Array<{id: string, articleId: string, content: string, source: string, wordCount: number, isRecommended: boolean}>,
 *     aiSuggestion: {recommendedId: string, reason: string}
 *   }>,
 *   exclusives: Array<{id: string, type: string, content: string, source: string, articleId: string, wordCount: number}>,
 *   quotes: Array<{id: string, text: string, speaker: string, role: string, source: string, articleId: string}>,
 *   summary: {mainTopic: string, totalElements: number, commonElements: number, exclusiveCount: number}
 * }>}
 */
export async function mergeTopics(articles) {
  return fetchApi('/merge-topics', {
    method: 'POST',
    body: JSON.stringify({ articles }),
  });
}

// ============================================
// User Articles API (Minhas Matérias)
// ============================================

/**
 * Get user articles (drafts and published)
 * @param {Object} params - Query parameters
 * @param {number} [params.page=1] - Page number
 * @param {number} [params.limit=20] - Items per page
 * @param {string} [params.status] - Filter by status ('draft' | 'published')
 * @param {string} [params.category] - Filter by category
 * @param {string} [params.search] - Search in title/content
 * @param {string} [params.dateRange] - Filter by date ('24h', '7d', '30d', '3m', 'year')
 * @returns {Promise<{items: Array, total: number, page: number, pages: number}>}
 */
export async function getUserArticles(params = {}) {
  const queryParams = new URLSearchParams();

  if (params.page) queryParams.append('page', params.page.toString());
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.status) queryParams.append('status', params.status);
  if (params.category) queryParams.append('category', params.category);
  if (params.search) queryParams.append('search', params.search);
  if (params.dateRange) queryParams.append('dateRange', params.dateRange);

  const queryString = queryParams.toString();
  const endpoint = `/user-articles${queryString ? `?${queryString}` : ''}`;

  return fetchApi(endpoint);
}

/**
 * Get a single user article by ID
 * @param {string} articleId - Article UUID
 * @returns {Promise<Object>} Article data
 */
export async function getUserArticle(articleId) {
  return fetchApi(`/user-articles/${articleId}`);
}

/**
 * Create a new user article
 * @param {Object} articleData - Article data
 * @param {string} articleData.title - Article title
 * @param {string} [articleData.linhaFina] - Subtitle
 * @param {string} articleData.content - Article content
 * @param {string} [articleData.status='draft'] - 'draft' or 'published'
 * @param {string} [articleData.category] - Category
 * @param {string[]} [articleData.tags] - Tags
 * @param {string} [articleData.authorName] - Author name
 * @param {string[]} [articleData.sourceArticleIds] - IDs of source RSS articles
 * @param {Object} [articleData.generationConfig] - AI generation settings
 * @returns {Promise<Object>} Created article
 */
export async function createUserArticle(articleData) {
  return fetchApi('/user-articles', {
    method: 'POST',
    body: JSON.stringify(articleData),
  });
}

/**
 * Update an existing user article
 * @param {string} articleId - Article UUID
 * @param {Object} articleData - Fields to update (partial)
 * @returns {Promise<Object>} Updated article
 */
export async function updateUserArticle(articleId, articleData) {
  return fetchApi(`/user-articles/${articleId}`, {
    method: 'PUT',
    body: JSON.stringify(articleData),
  });
}

/**
 * Delete a user article (soft delete)
 * @param {string} articleId - Article UUID
 * @returns {Promise<{message: string}>}
 */
export async function deleteUserArticle(articleId) {
  return fetchApi(`/user-articles/${articleId}`, {
    method: 'DELETE',
  });
}

// ============================================
// Utility Functions
// ============================================

/**
 * Check if the API is available
 * @returns {Promise<boolean>}
 */
export async function isApiAvailable() {
  try {
    await checkHealth();
    return true;
  } catch {
    return false;
  }
}

/**
 * Get the current API base URL (for debugging)
 * @returns {string}
 */
export { getApiBaseUrl };

// Export error class for type checking
export { ApiError };

// Export fetchApi for use by auth service
export { fetchApi };

// Default export with all functions
export default {
  checkHealth,
  getArticles,
  getArticle,
  getSources,
  createSource,
  updateSource,
  deleteSource,
  collectSource,
  getCategories,
  getTrendingTags,
  generateArticle,
  extractTopics,
  generateTags,
  mergeTopics,
  editArticle,
  getUserArticles,
  getUserArticle,
  createUserArticle,
  updateUserArticle,
  deleteUserArticle,
  isApiAvailable,
  getApiBaseUrl,
  registerAuthHandlers,
  getAuthToken,
  ApiError,
  fetchApi,
};
