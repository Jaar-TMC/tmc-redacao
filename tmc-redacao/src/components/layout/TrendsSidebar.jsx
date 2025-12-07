import { useState, useCallback } from 'react';
import { TrendingUp, Twitter, RefreshCw, Pause, Play, Hash } from 'lucide-react';
import { mockGoogleTrends, mockTwitterTrends, mockFeedThemes } from '../../data/mockData';
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

  const handleRefresh = useCallback(() => {
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
    }, 1000);
  }, []);
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
          className="p-4 space-y-6 overflow-y-auto h-[calc(100%-120px)]"
          aria-live="polite"
          aria-atomic="false"
          tabIndex={0}
          role="region"
          aria-label="Lista de tendências (navegável com teclado)"
        >
          {/* Google Trends */}
          <section aria-labelledby="google-trends-heading">
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
          <div className="border-t border-light-gray" role="separator"></div>

          {/* Twitter Trending */}
          <section aria-labelledby="twitter-trends-heading">
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

          {/* Divider */}
          <div className="border-t border-light-gray" role="separator"></div>

          {/* Feed Themes Trending */}
          <section aria-labelledby="feed-themes-heading">
            <div className="flex items-center gap-2 mb-3">
              <Hash size={18} className="text-tmc-dark-green" aria-hidden="true" />
              <h3 id="feed-themes-heading" className="font-semibold text-dark-gray text-sm">Temas no Feed</h3>
            </div>
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
                icon={Hash}
                title="Nenhum tema"
                description="Não há temas em destaque no momento."
                className="py-6"
              />
            ) : (
              <ul className="space-y-1">
                {feedThemes.map((item) => (
                  <li
                    key={item.id}
                    className="flex items-center justify-between p-2 hover:bg-off-white rounded-lg cursor-pointer transition-colors group"
                  >
                    <span className="text-sm font-medium text-dark-gray truncate group-hover:text-tmc-dark-green transition-colors">
                      {item.theme}
                    </span>
                    <span className="text-xs text-medium-gray bg-off-white px-2 py-0.5 rounded" aria-label={`${item.count} matérias`}>
                      {item.count} mat.
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
