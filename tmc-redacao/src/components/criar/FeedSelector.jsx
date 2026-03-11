import { useState, useMemo, useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
import { X, Search, FileText, Check, RefreshCw, AlertCircle, Tag } from 'lucide-react';
import { getFeedArticlesCached, getSourcesCached } from '../../services/api';
import { formatRelativeTime } from '../../data/mockData';
import SearchableSelect from '../ui/SearchableSelect';

/**
 * FeedSelector - Seletor inline de matérias do feed
 *
 * Permite buscar e selecionar múltiplas matérias
 * Agora conectado à API real de RSS
 */
const FeedSelector = ({ onClose, onSelect }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedArticles, setSelectedArticles] = useState([]);
  const [selectedTags, setSelectedTags] = useState(new Set());
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterSource, setFilterSource] = useState('all');
  const [filterTag, setFilterTag] = useState('all');

  // API State
  const [articles, setArticles] = useState([]);
  const [, setSources] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Minimum content length required for article generation (matches backend MIN_SOURCE_CHARS)
  const MIN_CONTENT_CHARS = 300;

  // Transform API articles to local format (shared between fetch and retry)
  // Filters out articles with content shorter than MIN_CONTENT_CHARS
  const transformApiArticles = useCallback((items) => {
    return (items || [])
      .filter(article => {
        // Use contentLength from backend if available, otherwise measure content
        const len = article.contentLength ?? (article.content || '').length;
        return len >= MIN_CONTENT_CHARS;
      })
      .map(article => ({
        id: article.id,
        title: article.title,
        preview: article.summary || article.content?.substring(0, 200) || '',
        content: article.content,
        category: article.category || 'Geral',
        source: article.source_name || article.source,
        url: article.link || article.url,
        favicon: article.favicon_url || `https://www.google.com/s2/favicons?domain=${new URL(article.link || article.url || 'https://example.com').hostname}`,
        publishedAt: article.published_at ? new Date(article.published_at) : new Date(),
        tags: article.tags || []
      }));
  }, []);

  // Shared fetch logic (used by effect and retry)
  const fetchData = useCallback(async (options = {}) => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch articles and sources in parallel with caching
      const [articlesResponse, sourcesResponse] = await Promise.all([
        getFeedArticlesCached({ limit: 100 }, { forceRefresh: options.forceRefresh }),
        getSourcesCached({ forceRefresh: options.forceRefresh })
      ]);

      const transformedArticles = transformApiArticles(articlesResponse?.items);
      setArticles(transformedArticles);
      setSources(sourcesResponse?.sources || []);
    } catch (err) {
      if (err.name === 'AbortError') return;
      setError(err.message || 'Erro ao carregar matérias');
    } finally {
      setIsLoading(false);
    }
  }, [transformApiArticles]);

  // Fetch articles from API (cached - instant if data is warm)
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Retry fetch (force refresh to bypass cache)
  const handleRetry = useCallback(() => {
    setArticles([]);
    setSources([]);
    fetchData({ forceRefresh: true });
  }, [fetchData]);

  // Filtrar matérias
  const filteredArticles = useMemo(() => {
    let filtered = [...articles];

    // Filtro por categoria
    if (filterCategory !== 'all') {
      filtered = filtered.filter(a => a.category === filterCategory);
    }

    // Filtro por fonte
    if (filterSource !== 'all') {
      filtered = filtered.filter(a => a.source === filterSource);
    }

    // Filtro por tag
    if (filterTag !== 'all') {
      filtered = filtered.filter(a => a.tags && a.tags.includes(filterTag));
    }

    // Filtro por busca
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(a =>
        a.title.toLowerCase().includes(query) ||
        a.preview.toLowerCase().includes(query)
      );
    }

    return filtered;
  }, [articles, searchQuery, filterCategory, filterSource, filterTag]);

  // Categorias únicas dos artigos carregados (formato para SearchableSelect)
  const categoryOptions = useMemo(() => {
    const uniqueCategories = [...new Set(articles.map(a => a.category))].filter(Boolean);
    return uniqueCategories.sort().map(cat => ({ value: cat, label: cat }));
  }, [articles]);

  // Fontes únicas dos artigos carregados (formato para SearchableSelect)
  const sourceOptions = useMemo(() => {
    const uniqueSources = [...new Set(articles.map(a => a.source))].filter(Boolean);
    return uniqueSources.sort().map(source => ({ value: source, label: source }));
  }, [articles]);

  // Tags únicas dos artigos carregados (formato para SearchableSelect)
  const tagOptions = useMemo(() => {
    const tagsSet = new Set();
    articles.forEach(a => {
      (a.tags || []).forEach(tag => tagsSet.add(tag));
    });
    return Array.from(tagsSet).sort().map(tag => ({ value: tag, label: `#${tag}` }));
  }, [articles]);

  const handleToggleArticle = (article) => {
    setSelectedArticles(prev => {
      const isSelected = prev.some(a => a.id === article.id);
      if (isSelected) {
        return prev.filter(a => a.id !== article.id);
      } else {
        return [...prev, article];
      }
    });
  };

  const handleTagToggle = useCallback((tag) => {
    setSelectedTags(prev => {
      const newSet = new Set(prev);
      if (newSet.has(tag)) {
        newSet.delete(tag);
      } else {
        newSet.add(tag);
      }
      return newSet;
    });
  }, []);

  // Get all unique tags from selected articles
  const availableTags = useMemo(() => {
    const allTags = new Set();
    selectedArticles.forEach(article => {
      (article.tags || []).forEach(tag => allTags.add(tag));
    });
    return Array.from(allTags).sort();
  }, [selectedArticles]);

  const handleContinue = () => {
    if (selectedArticles.length > 0 && onSelect) {
      onSelect(selectedArticles, Array.from(selectedTags));
    }
  };

  return (
    <div className="bg-white rounded-xl border border-light-gray shadow-lg p-6 animate-in slide-in-from-bottom duration-300">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText size={20} className="text-tmc-orange" />
          <h3 className="text-lg font-semibold text-dark-gray">
            Matérias do Feed
          </h3>
          {!isLoading && !error && (
            <span className="text-xs text-medium-gray bg-off-white px-2 py-1 rounded">
              {articles.length} matérias
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-off-white rounded-lg transition-colors"
          aria-label="Fechar seletor"
        >
          <X size={18} className="text-medium-gray" />
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-12">
          <RefreshCw size={32} className="text-tmc-orange animate-spin mb-4" />
          <p className="text-sm text-medium-gray">Carregando matérias do feed...</p>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="flex flex-col items-center justify-center py-12">
          <AlertCircle size={32} className="text-red-500 mb-4" />
          <p className="text-sm text-dark-gray font-medium mb-2">Erro ao carregar matérias</p>
          <p className="text-xs text-medium-gray mb-4">{error}</p>
          <button
            onClick={handleRetry}
            className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors text-sm font-medium flex items-center gap-2"
          >
            <RefreshCw size={16} />
            Tentar novamente
          </button>
        </div>
      )}

      {/* Content - Only show when loaded */}
      {!isLoading && !error && (
        <>
          {/* Busca */}
          <div className="mb-4">
            <div className="relative">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 text-medium-gray"
                size={18}
              />
              <input
                type="search"
                placeholder="Buscar matéria..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
              />
            </div>
          </div>

          {/* Filtros */}
          <div className="flex gap-3 mb-4">
            <SearchableSelect
              value={filterCategory}
              onChange={setFilterCategory}
              options={categoryOptions}
              placeholder="Buscar categoria..."
              allLabel="Todas as categorias"
              className="flex-1"
            />
            <SearchableSelect
              value={filterSource}
              onChange={setFilterSource}
              options={sourceOptions}
              placeholder="Buscar fonte..."
              allLabel="Todas as fontes"
              className="flex-1"
            />
            <SearchableSelect
              value={filterTag}
              onChange={setFilterTag}
              options={tagOptions}
              placeholder="Buscar tag..."
              allLabel="Todas as tags"
              className="flex-1"
            />
          </div>

          {/* Lista de Matérias */}
          <div className="max-h-96 overflow-y-auto space-y-2 mb-4">
            {filteredArticles.length === 0 ? (
              <div className="text-center py-8 text-medium-gray">
                <p className="text-sm">Nenhuma matéria encontrada</p>
                {articles.length === 0 && (
                  <p className="text-xs mt-2">
                    O feed RSS ainda não possui matérias coletadas.
                  </p>
                )}
              </div>
            ) : (
              filteredArticles.map((article) => {
                const isSelected = selectedArticles.some(a => a.id === article.id);

                return (
                  <div
                    key={article.id}
                    role="checkbox"
                    aria-checked={isSelected}
                    tabIndex={0}
                    onClick={() => handleToggleArticle(article)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleToggleArticle(article);
                      }
                    }}
                    className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                      isSelected
                        ? 'border-tmc-orange bg-orange-50'
                        : 'border-light-gray bg-white hover:border-tmc-orange/50 hover:bg-off-white'
                    }`}
                  >
                    {/* Custom Checkbox */}
                    <div
                      className={`
                        mt-0.5 w-5 h-5 rounded border-2 flex-shrink-0
                        flex items-center justify-center transition-colors
                        ${isSelected
                          ? 'bg-tmc-orange border-tmc-orange'
                          : 'border-medium-gray bg-white'
                        }
                      `}
                    >
                      {isSelected && (
                        <Check className="w-3 h-3 text-white" strokeWidth={3} />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className={`font-medium text-sm mb-1 ${
                        isSelected ? 'text-tmc-orange' : 'text-dark-gray'
                      }`}>
                        {article.title}
                      </h4>
                      <div className="flex items-center gap-2 text-xs text-medium-gray">
                        <img
                          src={article.favicon}
                          alt=""
                          className="w-4 h-4"
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                        <span>{article.source}</span>
                        <span>•</span>
                        <span>{formatRelativeTime(article.publishedAt)}</span>
                        {article.category && (
                          <>
                            <span>•</span>
                            <span className="text-tmc-orange">{article.category}</span>
                          </>
                        )}
                      </div>
                      <p className="text-xs text-medium-gray mt-1 line-clamp-2">
                        {article.preview}
                      </p>
                      {/* Tags display - Clickable */}
                      {article.tags && article.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {article.tags.slice(0, 5).map(tag => {
                            const isTagSelected = selectedTags.has(tag);
                            return (
                              <button
                                key={tag}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleTagToggle(tag);
                                }}
                                className={`text-xs px-1.5 py-0.5 rounded-full flex items-center gap-0.5 transition-all ${
                                  isTagSelected
                                    ? 'bg-tmc-orange text-white'
                                    : 'bg-off-white text-medium-gray hover:bg-tmc-orange/10 hover:text-tmc-orange'
                                }`}
                                aria-pressed={isTagSelected}
                              >
                                {isTagSelected && <Check size={8} strokeWidth={3} />}
                                #{tag}
                              </button>
                            );
                          })}
                          {article.tags.length > 5 && (
                            <span className="text-xs text-medium-gray">
                              +{article.tags.length - 5}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Selected Tags Summary */}
          {selectedTags.size > 0 && (
            <div className="mb-4 p-3 bg-orange-50 border border-tmc-orange/20 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Tag size={14} className="text-tmc-orange" />
                <span className="text-xs font-semibold text-dark-gray uppercase">
                  Tags selecionadas para SEO ({selectedTags.size})
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {Array.from(selectedTags).map(tag => (
                  <button
                    key={tag}
                    onClick={() => handleTagToggle(tag)}
                    className="text-xs bg-tmc-orange text-white px-2 py-1 rounded-full flex items-center gap-1 hover:bg-tmc-orange/80 transition-colors"
                  >
                    #{tag}
                    <X size={10} />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Available Tags from Selected Articles */}
          {availableTags.length > 0 && selectedTags.size === 0 && selectedArticles.length > 0 && (
            <div className="mb-4 p-3 bg-off-white rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Tag size={14} className="text-medium-gray" />
                <span className="text-xs font-medium text-medium-gray">
                  Clique nas tags para selecionar para SEO
                </span>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between pt-4 border-t border-light-gray">
            <div className="text-sm text-medium-gray">
              <span>{selectedArticles.length} {selectedArticles.length === 1 ? 'matéria' : 'matérias'}</span>
              {selectedTags.size > 0 && (
                <span className="ml-2">• {selectedTags.size} {selectedTags.size === 1 ? 'tag' : 'tags'}</span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 border border-light-gray text-medium-gray rounded-lg hover:bg-off-white transition-colors font-medium"
              >
                Cancelar
              </button>
              <button
                onClick={handleContinue}
                disabled={selectedArticles.length === 0}
                className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center gap-2"
              >
                Continuar com seleção
                <svg className="w-4 h-4" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor">
                  <path d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

FeedSelector.propTypes = {
  onClose: PropTypes.func.isRequired,
  onSelect: PropTypes.func.isRequired,
};

export default FeedSelector;
