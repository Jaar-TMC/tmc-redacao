import { useState, useMemo, useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
import { X, Search, Flame, TrendingUp, Twitter, RefreshCw, AlertCircle } from 'lucide-react';
import { getFeedArticlesCached } from '../../services/api';
import { transformArticles, computeFeedThemes } from '../../utils/transformers';

/**
 * TemaSelector - Seletor inline de temas em alta
 *
 * Abas: Feed em Alta, Google Trends, Twitter
 * Permite buscar e selecionar temas
 */
const TemaSelector = ({ onClose, onSelect }) => {
  const [activeTab, setActiveTab] = useState('feed'); // 'feed' | 'google' | 'twitter'
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTheme, setSelectedTheme] = useState(null);

  // API State
  const [feedThemes, setFeedThemes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Google Trends and Twitter are post-MVP features - use empty arrays
  const googleTrends = [];
  const twitterTrends = [];

  // Fetch articles and compute themes (uses cached data when available)
  const fetchThemes = useCallback(async (forceRefresh = false) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getFeedArticlesCached({ limit: 100 }, { forceRefresh });
      const articles = transformArticles(response?.items || response?.articles);
      const themes = computeFeedThemes(articles);
      setFeedThemes(themes);
    } catch (err) {
      console.error('Error fetching themes:', err);
      setError(err.message || 'Erro ao carregar temas');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch on mount
  useEffect(() => {
    fetchThemes();
  }, [fetchThemes]);

  // Obter dados baseado na tab ativa
  const getThemesData = () => {
    switch (activeTab) {
      case 'feed':
        return feedThemes.map(t => ({
          id: `feed-${t.id}`,
          name: t.theme,
          count: `${t.count} matérias`,
          trend: t.trend,
          source: 'feed'
        }));
      case 'google':
        return googleTrends.map(t => ({
          id: `google-${t.id}`,
          name: t.topic,
          count: t.searches,
          growth: t.growth,
          source: 'google'
        }));
      case 'twitter':
        return twitterTrends.map(t => ({
          id: `twitter-${t.id}`,
          name: t.hashtag,
          count: `${t.mentions} menções`,
          source: 'twitter'
        }));
      default:
        return [];
    }
  };

  // Filtrar temas pela busca
  const filteredThemes = useMemo(() => {
    const themes = getThemesData();
    if (!searchQuery.trim()) return themes;

    return themes.filter(t =>
      t.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [activeTab, searchQuery, feedThemes]);

  const handleThemeClick = (theme) => {
    setSelectedTheme(theme);
  };

  const handleContinue = () => {
    if (selectedTheme && onSelect) {
      onSelect(selectedTheme);
    }
  };

  const getTrendIcon = (trend) => {
    if (trend === 'up') return '↑';
    if (trend === 'down') return '↓';
    return '→';
  };

  const getTrendColor = (trend) => {
    if (trend === 'up') return 'text-green-600';
    if (trend === 'down') return 'text-red-500';
    return 'text-medium-gray';
  };

  return (
    <div className="bg-white rounded-xl border border-light-gray shadow-lg p-6 animate-in slide-in-from-bottom duration-300">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Flame size={20} className="text-orange-500" />
          <h3 className="text-lg font-semibold text-dark-gray">
            Tema em Alta
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
            placeholder="Buscar tema..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4 border-b border-light-gray">
        <button
          onClick={() => setActiveTab('feed')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'feed'
              ? 'border-tmc-orange text-tmc-orange'
              : 'border-transparent text-medium-gray hover:text-dark-gray'
          }`}
        >
          <Flame size={16} />
          Feed em Alta
        </button>
        <button
          onClick={() => setActiveTab('google')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'google'
              ? 'border-tmc-orange text-tmc-orange'
              : 'border-transparent text-medium-gray hover:text-dark-gray'
          }`}
        >
          <TrendingUp size={16} />
          Google Trends
        </button>
        <button
          onClick={() => setActiveTab('twitter')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'twitter'
              ? 'border-tmc-orange text-tmc-orange'
              : 'border-transparent text-medium-gray hover:text-dark-gray'
          }`}
        >
          <Twitter size={16} />
          Twitter
        </button>
      </div>

      {/* Lista de Temas */}
      <div className="max-h-80 overflow-y-auto space-y-2 mb-4">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-8">
            <RefreshCw size={24} className="text-tmc-orange animate-spin mb-2" />
            <p className="text-sm text-medium-gray">Carregando temas...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <AlertCircle size={24} className="text-red-500 mb-2" />
            <p className="text-sm text-medium-gray mb-3">{error}</p>
            <button
              onClick={fetchThemes}
              className="text-sm text-tmc-orange hover:underline flex items-center gap-1"
            >
              <RefreshCw size={14} />
              Tentar novamente
            </button>
          </div>
        ) : filteredThemes.length === 0 ? (
          <div className="text-center py-8 text-medium-gray">
            <p className="text-sm">Nenhum tema encontrado</p>
          </div>
        ) : (
          filteredThemes.map((theme) => {
            const isSelected = selectedTheme?.id === theme.id;

            return (
              <button
                key={theme.id}
                onClick={() => handleThemeClick(theme)}
                className={`w-full p-3 rounded-lg border text-left transition-all ${
                  isSelected
                    ? 'border-tmc-orange bg-orange-50'
                    : 'border-light-gray bg-white hover:border-tmc-orange/50 hover:bg-off-white'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`font-medium ${
                    isSelected ? 'text-tmc-orange' : 'text-dark-gray'
                  }`}>
                    {theme.name}
                  </span>
                  {theme.trend && (
                    <span className={`text-sm font-semibold ${getTrendColor(theme.trend)}`}>
                      {getTrendIcon(theme.trend)}
                    </span>
                  )}
                  {theme.growth && (
                    <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-0.5 rounded">
                      {theme.growth}
                    </span>
                  )}
                </div>
                <span className="text-sm text-medium-gray">
                  {theme.count}
                </span>
              </button>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t border-light-gray">
        <button
          onClick={onClose}
          className="px-4 py-2 border border-light-gray text-medium-gray rounded-lg hover:bg-off-white transition-colors font-medium"
        >
          Cancelar
        </button>
        <button
          onClick={handleContinue}
          disabled={!selectedTheme}
          className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center gap-2"
        >
          Continuar com tema
          <svg className="w-4 h-4" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor">
            <path d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  );
};

TemaSelector.propTypes = {
  onClose: PropTypes.func.isRequired,
  onSelect: PropTypes.func.isRequired,
};

export default TemaSelector;
