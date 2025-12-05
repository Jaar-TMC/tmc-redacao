import { useCallback, useMemo } from 'react';
import { Sparkles, X, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';

const ActionPanel = ({ selectedArticles = [], onRemove, onClearAll, isOpen, onClose }) => {
  const navigate = useNavigate();

  const hasSelection = useMemo(() => selectedArticles.length > 0, [selectedArticles.length]);

  const handleCreateWithInspiration = useCallback(() => {
    navigate('/criar-inspiracao', { state: { articles: selectedArticles } });
  }, [navigate, selectedArticles]);

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

      {/* Desktop Sidebar / Mobile Bottom Sheet */}
      <aside
        className={`
          w-80 bg-white shadow-sm border border-light-gray overflow-hidden flex flex-col
          lg:relative lg:inset-auto lg:z-auto lg:h-full lg:max-h-none lg:rounded-xl lg:border
          ${isOpen
            ? 'fixed bottom-0 left-0 right-0 z-50 max-h-[80vh] rounded-t-xl border-b-0'
            : 'hidden lg:flex'
          }
        `}
        role="complementary"
        aria-label="Painel de ação para matérias selecionadas"
      >
        {/* Header */}
        <div className="bg-tmc-dark-green text-white px-4 py-3 flex items-center justify-between">
          <h2 className="font-bold text-sm uppercase tracking-wide">Painel de Ação</h2>
          <button
            type="button"
            onClick={onClose}
            className="lg:hidden p-1 hover:bg-white/20 rounded transition-colors"
            aria-label="Fechar painel de ação"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 p-4 flex flex-col overflow-hidden">
          {!hasSelection ? (
            /* Empty State */
            <div className="flex-1 flex flex-col items-center justify-center text-center py-8">
              <div className="w-16 h-16 bg-off-white rounded-full flex items-center justify-center mb-4" aria-hidden="true">
                <FileText size={32} className="text-light-gray" />
              </div>
              <h3 className="font-semibold text-dark-gray mb-2">Nenhuma matéria selecionada</h3>
              <p className="text-sm text-medium-gray">
                Selecione uma ou mais matérias para gerar conteúdo original baseado nelas
              </p>
            </div>
          ) : (
            /* Selected Articles */
            <>
              <div className="flex items-center justify-between mb-4" role="status" aria-live="polite">
                <span className="text-sm font-semibold text-dark-gray">
                  {selectedArticles.length} {selectedArticles.length === 1 ? 'matéria selecionada' : 'matérias selecionadas'}
                </span>
                <button
                  type="button"
                  onClick={onClearAll}
                  className="text-xs text-medium-gray hover:text-error transition-colors"
                  aria-label="Remover todas as matérias selecionadas"
                >
                  Remover tudo
                </button>
              </div>

              <div
                className="flex-1 overflow-y-auto space-y-2 mb-4"
                role="list"
                aria-label="Matérias selecionadas"
                tabIndex={0}
              >
                {selectedArticles.map((article) => (
                  <div
                    key={article.id}
                    className="flex items-start gap-3 p-3 bg-off-white rounded-lg group"
                    role="listitem"
                  >
                    <img
                      src={article.favicon}
                      alt=""
                      className="w-5 h-5 rounded mt-0.5"
                      aria-hidden="true"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-dark-gray line-clamp-2">
                        {article.title}
                      </p>
                      <p className="text-xs text-medium-gray mt-1">{article.source}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => onRemove(article.id)}
                      className="p-1 opacity-0 group-hover:opacity-100 hover:bg-white rounded transition-all"
                      aria-label={`Remover ${article.title} da seleção`}
                    >
                      <X size={14} className="text-medium-gray" aria-hidden="true" />
                    </button>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={handleCreateWithInspiration}
                className="w-full bg-tmc-orange hover:bg-tmc-orange/90 text-white py-3 px-4 rounded-lg font-semibold transition-colors"
                aria-label="Criar post com base nas matérias selecionadas"
              >
                <div className="flex items-center justify-center gap-2">
                  <Sparkles size={20} aria-hidden="true" className="flex-shrink-0" />
                  <span className="text-center leading-tight text-sm">Criar Post com Base nas Matérias Selecionadas</span>
                </div>
              </button>
            </>
          )}
        </div>

        {/* Stats Footer */}
        <div className="px-4 py-3 bg-off-white border-t border-light-gray">
          <p className="text-xs text-medium-gray text-center" role="status">
            <span className="font-semibold text-dark-gray">156</span> matérias coletadas hoje
          </p>
        </div>
      </aside>

      {/* Mobile Floating Action Button */}
      {hasSelection && (
        <button
          type="button"
          onClick={() => !isOpen && onClose?.()}
          className="lg:hidden fixed bottom-4 right-4 z-30 bg-tmc-orange text-white p-4 rounded-full shadow-lg flex items-center gap-2"
          aria-label={`${selectedArticles.length} matérias selecionadas - Abrir painel de ação`}
        >
          <Sparkles size={20} aria-hidden="true" />
          <span className="font-semibold">{selectedArticles.length}</span>
        </button>
      )}
    </>
  );
};

ActionPanel.propTypes = {
  selectedArticles: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      title: PropTypes.string.isRequired,
      source: PropTypes.string.isRequired,
      favicon: PropTypes.string.isRequired,
    })
  ),
  onRemove: PropTypes.func.isRequired,
  onClearAll: PropTypes.func.isRequired,
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};

export default ActionPanel;
