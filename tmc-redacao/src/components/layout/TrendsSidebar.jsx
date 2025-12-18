import { useState, useCallback } from 'react';
import { TrendingUp, Twitter, RefreshCw, Pause, Play, Flame, Info, Filter } from 'lucide-react';
import { mockGoogleTrends, mockTwitterTrends, mockFeedThemes } from '../../data/mockData';
import { useFilters } from '../../context';
import Skeleton from '../ui/Skeleton';
import EmptyState from '../ui/EmptyState';
import PropTypes from 'prop-types';

/**
 * TrendsSidebar Component
 *
 * WCAG 2.1 Compliance:
 * - Pause, Stop, Hide (2.2.2): Auto-refresh can be paused via pause button
 * - Timing Adjustable (2.2.1): Users can pause automatic updates
 * - No Keyboard Trap (2.1.2): All interactive elements can be navigated with keyboard
 */
const TrendsSidebar = ({ isOpen, onClose }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [googleTrends] = useState(mockGoogleTrends);
  const [twitterTrends] = useState(mockTwitterTrends);
  const [feedThemes] = useState(mockFeedThemes);
  const { filters, updateFilter } = useFilters();

  const handleRefresh = useCallback(() => {
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
    }, 1000);
  }, []);

  // Filtra o feed RSS pelo tema selecionado
  const handleThemeClick = useCallback((theme) => {
    updateFilter('searchQuery', theme);
  }, [updateFilter]);

  // Limpa o filtro de tema
  const handleClearThemeFilter = useCallback(() => {
    updateFilter('searchQuery', '');
  }, [updateFilter]);

  // Verifica se algum tema está ativo no filtro
  const activeTheme = feedThemes.find(t => t.theme === filters.searchQuery);
  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          w-72 bg-white shadow-sm border border-light-gray overflow-hidden
          lg:block lg:h-full lg:rounded-none lg:border-l lg:border-r-0 lg:border-t-0 lg:border-b-0
          ${isOpen ? 'fixed top-16 left-0 bottom-0 z-50 rounded-none border-l-0' : 'hidden lg:block'}
        `}
        role="complementary"
        aria-label="Temas em alta"
      >
        {/* Header */}
        <div className="bg-tmc-orange text-white px-4 py-3">
          <div className="flex items-center justify-between mb-1">
            <h2 className="font-bold text-sm uppercase tracking-wide">TENDÊNCIAS</h2>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setIsPaused(!isPaused)}
                className="p-1 hover:bg-white/20 rounded transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                aria-label={isPaused ? "Retomar atualização automática de tendências" : "Pausar atualização automática de tendências"}
                aria-pressed={isPaused}
                title={isPaused ? "Retomar" : "Pausar"}
              >
                {isPaused ? <Play size={16} aria-hidden="true" /> : <Pause size={16} aria-hidden="true" />}
              </button>
              <button
                type="button"
                onClick={handleRefresh}
                className={`p-1 hover:bg-white/20 rounded transition-all min-h-[44px] min-w-[44px] flex items-center justify-center ${isLoading ? 'animate-spin' : ''}`}
                aria-label="Atualizar tendências manualmente"
                title="Atualizar"
                disabled={isLoading || isPaused}
              >
                <RefreshCw size={16} aria-hidden="true" />
              </button>
            </div>
          </div>
          <p className="text-xs text-white/80">
            Temas mais buscados e discutidos agora
            {isPaused && <span className="ml-2 font-semibold">(Atualização pausada)</span>}
          </p>
        </div>

        <div
          className="space-y-6 overflow-y-auto h-[calc(100%-120px)] pb-4"
          aria-live="polite"
          aria-atomic="false"
          tabIndex={0}
          role="region"
          aria-label="Lista de tendências (navegável com teclado)"
        >
          {/* Feed Themes Trending - Temas Quentes dos Concorrentes (PRIORIDADE) */}
          <section aria-labelledby="feed-themes-heading" className="bg-gradient-to-br from-orange-50 to-red-50 px-4 py-3 border-b border-orange-100">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-gradient-to-br from-orange-500 to-red-500 rounded-lg">
                  <Flame size={16} className="text-white" aria-hidden="true" />
                </div>
                <div>
                  <h3 id="feed-themes-heading" className="font-bold text-dark-gray text-sm">Temas Quentes</h3>
                </div>
              </div>
              {/* Tooltip de Informação */}
              <div className="relative group/tooltip">
                <button
                  type="button"
                  className="p-1 text-medium-gray hover:text-tmc-orange transition-colors rounded-full hover:bg-white/50"
                  aria-label="Informações sobre temas quentes"
                >
                  <Info size={16} aria-hidden="true" />
                </button>
                <div className="absolute right-0 top-full mt-2 w-56 p-3 bg-dark-gray text-white text-xs rounded-lg shadow-lg opacity-0 invisible group-hover/tooltip:opacity-100 group-hover/tooltip:visible transition-all duration-200 z-50">
                  <p className="font-semibold mb-1">Inteligência Competitiva</p>
                  <p className="text-gray-300 leading-relaxed">
                    Assuntos mais frequentes nas matérias dos seus concorrentes (fontes RSS). Use para identificar pautas em alta!
                  </p>
                  <div className="absolute -top-1.5 right-3 w-3 h-3 bg-dark-gray rotate-45"></div>
                </div>
              </div>
            </div>
            <p className="text-xs text-medium-gray mb-3 ml-9">
              Feed dos concorrentes
              {activeTheme && (
                <span className="ml-1 text-tmc-orange font-medium">• Filtro ativo</span>
              )}
            </p>

            {/* Botão para limpar filtro quando ativo */}
            {activeTheme && (
              <button
                type="button"
                onClick={handleClearThemeFilter}
                className="flex items-center gap-1.5 w-full mb-2 px-3 py-1.5 text-xs font-medium text-tmc-orange bg-white border border-orange-200 rounded-lg hover:bg-orange-50 transition-colors"
                aria-label="Limpar filtro de tema"
              >
                <Filter size={12} aria-hidden="true" />
                Limpar filtro: &quot;{activeTheme.theme}&quot;
              </button>
            )}

            {isLoading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center justify-between p-2">
                    <Skeleton className="h-3 w-28" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                ))}
              </div>
            ) : feedThemes.length === 0 ? (
              <EmptyState
                icon={Flame}
                title="Nenhum tema"
                description="Não há temas em destaque no momento."
                className="py-6"
              />
            ) : (
              <ul className="space-y-1">
                {feedThemes.map((item, index) => {
                  const isActive = filters.searchQuery === item.theme;
                  return (
                    <li
                      key={item.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => handleThemeClick(item.theme)}
                      onKeyDown={(e) => e.key === 'Enter' && handleThemeClick(item.theme)}
                      aria-pressed={isActive}
                      aria-label={`Filtrar por ${item.theme}. ${item.count} matérias`}
                      className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-all group ${
                        isActive
                          ? 'bg-tmc-orange text-white shadow-md ring-2 ring-tmc-orange/30'
                          : index === 0
                            ? 'bg-white shadow-sm border border-orange-200 hover:border-orange-300'
                            : 'hover:bg-white/60'
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        {(index < 3 || isActive) && (
                          <Flame
                            size={14}
                            className={`flex-shrink-0 ${
                              isActive
                                ? 'text-white'
                                : index === 0 ? 'text-red-500' : 'text-orange-400'
                            }`}
                            aria-hidden="true"
                          />
                        )}
                        <span className={`text-sm font-medium truncate transition-colors ${
                          isActive
                            ? 'text-white'
                            : index === 0
                              ? 'text-dark-gray group-hover:text-red-600'
                              : 'text-dark-gray group-hover:text-tmc-orange'
                        }`}>
                          {item.theme}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {index === 0 && !isActive && (
                          <span className="text-[10px] font-bold text-white bg-gradient-to-r from-orange-500 to-red-500 px-1.5 py-0.5 rounded uppercase">
                            #1
                          </span>
                        )}
                        {isActive && (
                          <Filter size={12} className="text-white" aria-hidden="true" />
                        )}
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          isActive
                            ? 'text-white bg-white/20 font-medium'
                            : index === 0
                              ? 'text-orange-700 bg-orange-100 font-medium'
                              : 'text-medium-gray bg-white/80'
                        }`} aria-label={`${item.count} matérias`}>
                          {item.count} mat.
                        </span>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {/* Google Trends */}
          <section aria-labelledby="google-trends-heading" className="px-4">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp size={18} className="text-tmc-orange" aria-hidden="true" />
              <h3 id="google-trends-heading" className="font-semibold text-dark-gray text-sm">Google Trends</h3>
            </div>
            {isLoading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center gap-3 p-2">
                    <Skeleton variant="circle" className="w-6 h-6 flex-shrink-0" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-3 w-3/4" />
                      <Skeleton className="h-2 w-1/2" />
                    </div>
                    <Skeleton className="h-4 w-12" />
                  </div>
                ))}
              </div>
            ) : googleTrends.length === 0 ? (
              <EmptyState
                icon={TrendingUp}
                title="Nenhuma tendência"
                description="Não há tendências do Google no momento."
                className="py-6"
              />
            ) : (
              <ul className="space-y-2">
                {googleTrends.map((trend, index) => (
                  <li
                    key={trend.id}
                    className="flex items-center gap-3 p-2 hover:bg-off-white rounded-lg cursor-pointer transition-colors group"
                  >
                    <span className="w-6 h-6 bg-tmc-orange/10 text-tmc-orange rounded-full flex items-center justify-center text-xs font-bold" aria-label={`Posição ${index + 1}`}>
                      {index + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-dark-gray truncate group-hover:text-tmc-orange transition-colors">
                        {trend.topic}
                      </p>
                      <p className="text-xs text-medium-gray">{trend.searches} buscas</p>
                    </div>
                    <span className="text-xs font-semibold text-success bg-success/10 px-2 py-0.5 rounded" aria-label={`Crescimento de ${trend.growth}`}>
                      {trend.growth}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Divider */}
          <div className="border-t border-light-gray mx-4" role="separator"></div>

          {/* Twitter Trending */}
          <section aria-labelledby="twitter-trends-heading" className="px-4">
            <div className="flex items-center gap-2 mb-3">
              <Twitter size={18} className="text-[#1DA1F2]" aria-hidden="true" />
              <h3 id="twitter-trends-heading" className="font-semibold text-dark-gray text-sm">Twitter Trending</h3>
            </div>
            {isLoading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center justify-between p-2">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="h-4 w-12" />
                  </div>
                ))}
              </div>
            ) : twitterTrends.length === 0 ? (
              <EmptyState
                icon={Twitter}
                title="Nenhuma tendência"
                description="Não há trending topics do Twitter no momento."
                className="py-6"
              />
            ) : (
              <ul className="space-y-2">
                {twitterTrends.map((trend) => (
                  <li
                    key={trend.id}
                    className="flex items-center justify-between p-2 hover:bg-off-white rounded-lg cursor-pointer transition-colors group"
                  >
                    <span className="text-sm font-medium text-[#1DA1F2] group-hover:underline">
                      {trend.hashtag}
                    </span>
                    <span className="text-xs text-medium-gray bg-off-white px-2 py-0.5 rounded" aria-label={`${trend.mentions} menções`}>
                      {trend.mentions}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

        </div>

        {/* Footer */}
        <div className="px-4 py-3 bg-off-white border-t border-light-gray absolute bottom-0 left-0 right-0">
          <p className="text-xs text-medium-gray text-center" role="status" aria-live="polite">
            {isPaused ? 'Atualização pausada' : 'Atualizado há 5 minutos'}
          </p>
        </div>
      </aside>
    </>
  );
};

TrendsSidebar.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};

export default TrendsSidebar;
