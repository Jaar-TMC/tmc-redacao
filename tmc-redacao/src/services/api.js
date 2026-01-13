/**
 * API Service Layer for TMC Redação
 *
 * Centralized API calls with error handling and configuration.
 * Connects frontend to the Azure Functions backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:7071/api';

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
  const url = `${API_BASE_URL}${endpoint}`;

  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };

  const config = { ...defaultOptions, ...options };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
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
 * @param {number} [params.limit=50] - Max articles to return
 * @param {number} [params.offset=0] - Pagination offset
 * @param {string} [params.search] - Search query
 * @returns {Promise<{articles: Array, total: number}>}
 */
export async function getArticles(params = {}) {
  const queryParams = new URLSearchParams();

  if (params.source) queryParams.append('source', params.source);
  if (params.category) queryParams.append('category', params.category);
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.offset) queryParams.append('offset', params.offset.toString());
  if (params.search) queryParams.append('search', params.search);

  const queryString = queryParams.toString();
  const endpoint = `/articles${queryString ? `?${queryString}` : ''}`;

  return fetchApi(endpoint);
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
 * @returns {Promise<{sources: Array}>}
 */
export async function getSources() {
  return fetchApi('/sources');
}

/**
 * Get available categories
 * @returns {Promise<{categories: Array<string>}>}
 */
export async function getCategories() {
  return fetchApi('/categories');
}

// ============================================
// AI Generation API
// ============================================

/**
 * Generate article using AI
 * @param {Object} params - Generation parameters
 * @param {string} params.texto_base - Source text content
 * @param {string} params.persona - Writer persona (imparcial|especialista|colunista|influencer)
 * @param {string} params.tom - Writing tone (formal|informal|tecnico|persuasivo|neutro)
 * @param {string} [params.orientacao_lide] - Lead paragraph guidance
 * @param {string[]} [params.citacoes] - Quotes to include
 * @param {string} [params.contexto] - Background context
 * @param {string} [params.creditos] - Source credits
 * @param {string} [params.tipo_materia] - Article type (destaque|coluna|servico|etc)
 * @param {string[]} [params.tags] - Tags for SEO
 * @returns {Promise<{titulo: string, linha_fina: string, conteudo: string, tags_sugeridas: string[]}>}
 */
export async function generateArticle(params) {
  return fetchApi('/generate', {
    method: 'POST',
    body: JSON.stringify(params),
  });
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
 * Get the API base URL (for debugging)
 * @returns {string}
 */
export function getApiBaseUrl() {
  return API_BASE_URL;
}

// Export error class for type checking
export { ApiError };

// Default export with all functions
export default {
  checkHealth,
  getArticles,
  getArticle,
  getSources,
  getCategories,
  generateArticle,
  extractTopics,
  generateTags,
  isApiAvailable,
  getApiBaseUrl,
  ApiError,
};
