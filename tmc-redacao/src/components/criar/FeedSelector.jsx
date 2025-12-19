import { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import { X, Search, FileText, Check } from 'lucide-react';
import { mockArticles } from '../../data/mockData';
import { formatRelativeTime } from '../../data/mockData';

/**
 * FeedSelector - Seletor inline de matérias do feed
 *
 * Permite buscar e selecionar múltiplas matérias
 */
const FeedSelector = ({ onClose, onSelect }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedArticles, setSelectedArticles] = useState([]);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterSource, setFilterSource] = useState('all');

  // Filtrar matérias
  const filteredArticles = useMemo(() => {
    let articles = [...mockArticles];

    // Filtro por categoria
    if (filterCategory !== 'all') {
      articles = articles.filter(a => a.category === filterCategory);
    }

    // Filtro por fonte
    if (filterSource !== 'all') {
      articles = articles.filter(a => a.source === filterSource);
    }

    // Filtro por busca
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      articles = articles.filter(a =>
        a.title.toLowerCase().includes(query) ||
        a.preview.toLowerCase().includes(query)
      );
    }

    return articles;
  }, [searchQuery, filterCategory, filterSource]);

  // Categorias únicas
  const categories = useMemo(() => {
    const uniqueCategories = [...new Set(mockArticles.map(a => a.category))];
    return uniqueCategories;
  }, []);

  // Fontes únicas
  const sources = useMemo(() => {
    const uniqueSources = [...new Set(mockArticles.map(a => a.source))];
    return uniqueSources;
  }, []);

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
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-off-white rounded-lg transition-colors"
          aria-label="Fechar seletor"
        >
          <X size={18} className="text-medium-gray" />
        </button>
      </div>

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
            {sources.map(source => (
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
                    />
                    <span>{article.source}</span>
                    <span>•</span>
                    <span>{formatRelativeTime(article.publishedAt)}</span>
                  </div>
                  <p className="text-xs text-medium-gray mt-1 line-clamp-2">
                    {article.preview}
                  </p>
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
    </div>
  );
};

FeedSelector.propTypes = {
  onClose: PropTypes.func.isRequired,
  onSelect: PropTypes.func.isRequired,
};

export default FeedSelector;
