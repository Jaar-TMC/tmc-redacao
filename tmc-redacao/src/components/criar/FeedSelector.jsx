import { useState, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import { X, Search, FileText, Check, RefreshCw, AlertCircle } from 'lucide-react';
import { getArticles, getSources } from '../../services/api';
import { formatRelativeTime } from '../../data/mockData';

/**
 * FeedSelector - Seletor inline de matérias do feed
 *
 * Permite buscar e selecionar múltiplas matérias
 * Agora conectado à API real de RSS
 */
const FeedSelector = ({ onClose, onSelect }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedArticles, setSelectedArticles] = useState([]);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterSource, setFilterSource] = useState('all');

  // API State
  const [articles, setArticles] = useState([]);
  const [sources, setSources] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch articles from API
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch articles and sources in parallel
        const [articlesResponse, sourcesResponse] = await Promise.all([
          getArticles({ limit: 100 }),
          getSources()
        ]);

        // Transform API response to match expected format
        const transformedArticles = (articlesResponse?.articles || []).map(article => ({
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

        setArticles(transformedArticles);
        setSources(sourcesResponse?.sources || []);
      } catch (err) {
        console.error('Error fetching articles:', err);
        setError(err.message || 'Erro ao carregar matérias');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Retry fetch
  const handleRetry = () => {
    setArticles([]);
    setSources([]);
    setIsLoading(true);
    setError(null);

    // Re-trigger the effect by updating state
    const fetchData = async () => {
      try {
        const [articlesResponse, sourcesResponse] = await Promise.all([
          getArticles({ limit: 100 }),
          getSources()
        ]);

        const transformedArticles = (articlesResponse?.articles || []).map(article => ({
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

        setArticles(transformedArticles);
        setSources(sourcesResponse?.sources || []);
      } catch (err) {
        setError(err.message || 'Erro ao carregar matérias');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  };

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

    // Filtro por busca
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(a =>
        a.title.toLowerCase().includes(query) ||
        a.preview.toLowerCase().includes(query)
      );
    }

    return filtered;
  }, [articles, searchQuery, filterCategory, filterSource]);

  // Categorias únicas dos artigos carregados
  const categories = useMemo(() => {
    const uniqueCategories = [...new Set(articles.map(a => a.category))].filter(Boolean);
    return uniqueCategories.sort();
  }, [articles]);

  // Fontes únicas dos artigos carregados
  const sourceNames = useMemo(() => {
    const uniqueSources = [...new Set(articles.map(a => a.source))].filter(Boolean);
    return uniqueSources.sort();
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

  const handleContinue = () => {
    if (selectedArticles.length > 0 && onSelect) {
      onSelect(selectedArticles);
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
            <div className="flex-1 relative">
              <select
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
                className="w-full px-3 py-2 pr-8 border border-light-gray rounded-lg text-sm bg-white appearance-none cursor-pointer focus:outline-none focus:border-tmc-orange transition-colors"
              >
                <option value="all">Todas as categorias</option>
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
              <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                <svg className="w-4 h-4 text-medium-gray" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
            <div className="flex-1 relative">
              <select
                value={filterSource}
                onChange={(e) => setFilterSource(e.target.value)}
                className="w-full px-3 py-2 pr-8 border border-light-gray rounded-lg text-sm bg-white appearance-none cursor-pointer focus:outline-none focus:border-tmc-orange transition-colors"
              >
                <option value="all">Todas as fontes</option>
                {sourceNames.map(source => (
                  <option key={source} value={source}>{source}</option>
                ))}
              </select>
              <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                <svg className="w-4 h-4 text-medium-gray" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
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
                      {/* Tags display */}
                      {article.tags && article.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {article.tags.slice(0, 3).map(tag => (
                            <span
                              key={tag}
                              className="text-xs bg-off-white text-medium-gray px-1.5 py-0.5 rounded"
                            >
                              #{tag}
                            </span>
                          ))}
                          {article.tags.length > 3 && (
                            <span className="text-xs text-medium-gray">
                              +{article.tags.length - 3}
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

          {/* Footer */}
          <div className="flex items-center justify-between pt-4 border-t border-light-gray">
            <span className="text-sm text-medium-gray">
              {selectedArticles.length} {selectedArticles.length === 1 ? 'matéria selecionada' : 'matérias selecionadas'}
            </span>
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
