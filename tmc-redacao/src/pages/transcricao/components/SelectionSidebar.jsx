import { useState, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  X,
  Trash2,
  ChevronUp,
  ChevronDown,
  GripVertical,
  Hash,
  FileText,
  AlertCircle,
  Tag,
  Clock
} from 'lucide-react';

/**
 * SelectionSidebar - Painel lateral mostrando preview dos trechos selecionados
 * @param {Object} props
 * @param {Array} props.selections - Array de seleções {id, text, source, topic, timestamp}
 * @param {Function} props.onRemove - Callback ao remover item (id) => void
 * @param {Function} props.onReorder - Callback ao reordenar (fromIndex, toIndex) => void
 * @param {Function} props.onClear - Callback ao limpar todas seleções
 */
function SelectionSidebar({
  selections = [],
  onRemove,
  onReorder,
  onClear
}) {
  const [expandedId, setExpandedId] = useState(null);

  // Calcular total de palavras
  const totalWords = useMemo(() => {
    return selections.reduce((acc, sel) => {
      return acc + sel.text.split(/\s+/).filter(word => word.length > 0).length;
    }, 0);
  }, [selections]);

  // Calcular tempo estimado de leitura (200 palavras/minuto)
  const estimatedMinutes = useMemo(() => {
    return Math.ceil(totalWords / 200);
  }, [totalWords]);

  // Handler para remover item
  const handleRemove = useCallback((id) => {
    onRemove(id);
    if (expandedId === id) {
      setExpandedId(null);
    }
  }, [onRemove, expandedId]);

  // Handler para mover item para cima
  const handleMoveUp = useCallback((index) => {
    if (index > 0) {
      onReorder(index, index - 1);
    }
  }, [onReorder]);

  // Handler para mover item para baixo
  const handleMoveDown = useCallback((index) => {
    if (index < selections.length - 1) {
      onReorder(index, index + 1);
    }
  }, [onReorder, selections.length]);

  // Toggle expandir/recolher preview
  const handleToggleExpand = useCallback((id) => {
    setExpandedId(prev => prev === id ? null : id);
  }, []);

  // Handler para limpar tudo
  const handleClearAll = useCallback(() => {
    if (window.confirm('Deseja realmente limpar todas as seleções?')) {
      onClear();
      setExpandedId(null);
    }
  }, [onClear]);

  // Truncar texto para preview
  const getPreviewText = useCallback((text, maxLength = 120) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }, []);

  // Se não há seleções
  if (selections.length === 0) {
    return (
      <div
        className="bg-white rounded-xl border border-light-gray p-6"
        role="complementary"
        aria-label="Painel de seleções"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-dark-gray">
            Seleções
          </h2>
        </div>

        <div className="text-center py-8">
          <div className="w-16 h-16 bg-off-white rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText className="w-8 h-8 text-medium-gray" aria-hidden="true" />
          </div>
          <p className="text-sm text-medium-gray mb-2">
            Nenhum trecho selecionado
          </p>
          <p className="text-xs text-medium-gray">
            Selecione trechos da transcrição para visualizá-los aqui
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="bg-white rounded-xl border border-light-gray"
      role="complementary"
      aria-label="Painel de seleções"
    >
      {/* Header */}
      <div className="p-4 border-b border-light-gray sticky top-0 bg-white rounded-t-xl z-10">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-dark-gray">
            Seleções
          </h2>
          <button
            type="button"
            onClick={handleClearAll}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-error hover:bg-red-50 rounded-lg transition-colors"
            aria-label="Limpar todas as seleções"
          >
            <Trash2 className="w-4 h-4" aria-hidden="true" />
            <span>Limpar Tudo</span>
          </button>
        </div>

        {/* Estatísticas */}
        <div className="flex items-center flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-1.5 text-medium-gray">
            <FileText className="w-4 h-4" aria-hidden="true" />
            <span>
              <strong className="text-dark-gray font-semibold">{selections.length}</strong> {selections.length === 1 ? 'item' : 'itens'}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-medium-gray">
            <Hash className="w-4 h-4" aria-hidden="true" />
            <span>
              <strong className="text-dark-gray font-semibold">{totalWords}</strong> palavras
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-medium-gray">
            <Clock className="w-4 h-4" aria-hidden="true" />
            <span>
              <strong className="text-dark-gray font-semibold">{estimatedMinutes}</strong> min
            </span>
          </div>
        </div>
      </div>

      {/* Lista de seleções */}
      <div className="p-4 space-y-3 max-h-[calc(100vh-20rem)] overflow-y-auto">
        {selections.map((selection, index) => {
          const isExpanded = expandedId === selection.id;
          const wordCount = selection.text.split(/\s+/).filter(word => word.length > 0).length;

          return (
            <div
              key={selection.id}
              className="bg-off-white rounded-lg border border-light-gray hover:border-tmc-orange/50 transition-all"
            >
              {/* Item Header */}
              <div className="p-3">
                <div className="flex items-start gap-2">
                  {/* Grip para drag (visual) */}
                  <div className="flex flex-col gap-0.5 pt-1">
                    <GripVertical className="w-4 h-4 text-medium-gray" aria-hidden="true" />
                  </div>

                  {/* Conteúdo */}
                  <div className="flex-1 min-w-0">
                    {/* Contexto: Tópico e Timestamp */}
                    {(selection.topic || selection.timestamp) && (
                      <div className="flex items-center gap-2 mb-2 pb-2 border-b border-light-gray">
                        {selection.topic && (
                          <div className="flex items-center gap-1 px-2 py-1 bg-tmc-orange/10 rounded-md">
                            <Tag className="w-3 h-3 text-tmc-orange flex-shrink-0" aria-hidden="true" />
                            <span className="text-xs text-tmc-orange font-medium truncate">
                              {selection.topic}
                            </span>
                          </div>
                        )}
                        {selection.timestamp && (
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3 text-medium-gray flex-shrink-0" aria-hidden="true" />
                            <span className="text-xs text-medium-gray font-medium">
                              {selection.timestamp}
                            </span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Preview do texto */}
                    <button
                      type="button"
                      onClick={() => handleToggleExpand(selection.id)}
                      className="w-full text-left group"
                      aria-expanded={isExpanded}
                      aria-label={isExpanded ? 'Recolher preview' : 'Expandir preview'}
                    >
                      <p className="text-sm text-dark-gray leading-relaxed">
                        {isExpanded
                          ? `"${selection.text}"`
                          : `"${getPreviewText(selection.text)}"`
                        }
                      </p>
                    </button>

                    {/* Metadados */}
                    <div className="flex items-center gap-3 mt-2 text-xs text-medium-gray">
                      <span className="flex items-center gap-1">
                        <Hash className="w-3 h-3" aria-hidden="true" />
                        {wordCount} {wordCount === 1 ? 'palavra' : 'palavras'}
                      </span>
                      <span className="px-2 py-0.5 bg-tmc-orange/10 text-tmc-orange rounded-full font-medium">
                        {selection.source === 'cards' ? 'Tópico' : 'Texto'}
                      </span>
                    </div>
                  </div>

                  {/* Botões de ação */}
                  <div className="flex flex-col gap-1">
                    <button
                      type="button"
                      onClick={() => handleMoveUp(index)}
                      disabled={index === 0}
                      className={`p-1 rounded transition-colors ${
                        index === 0
                          ? 'text-light-gray cursor-not-allowed'
                          : 'text-medium-gray hover:bg-white hover:text-tmc-orange'
                      }`}
                      aria-label="Mover para cima"
                      title="Mover para cima"
                    >
                      <ChevronUp className="w-4 h-4" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleMoveDown(index)}
                      disabled={index === selections.length - 1}
                      className={`p-1 rounded transition-colors ${
                        index === selections.length - 1
                          ? 'text-light-gray cursor-not-allowed'
                          : 'text-medium-gray hover:bg-white hover:text-tmc-orange'
                      }`}
                      aria-label="Mover para baixo"
                      title="Mover para baixo"
                    >
                      <ChevronDown className="w-4 h-4" aria-hidden="true" />
                    </button>
                  </div>

                  {/* Botão remover */}
                  <button
                    type="button"
                    onClick={() => handleRemove(selection.id)}
                    className="p-1 text-medium-gray hover:bg-red-50 hover:text-error rounded transition-colors"
                    aria-label="Remover seleção"
                    title="Remover"
                  >
                    <X className="w-4 h-4" aria-hidden="true" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer com dica */}
      <div className="p-4 border-t border-light-gray bg-off-white rounded-b-xl">
        <div className="flex items-start gap-2 text-xs text-medium-gray">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <p>
            Use os botões <ChevronUp className="w-3 h-3 inline" aria-hidden="true" /> e <ChevronDown className="w-3 h-3 inline" aria-hidden="true" /> para reordenar os trechos
          </p>
        </div>
      </div>
    </div>
  );
}

SelectionSidebar.propTypes = {
  selections: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    text: PropTypes.string.isRequired,
    source: PropTypes.oneOf(['cards', 'full']).isRequired,
    topic: PropTypes.string,
    timestamp: PropTypes.string
  })),
  onRemove: PropTypes.func.isRequired,
  onReorder: PropTypes.func.isRequired,
  onClear: PropTypes.func.isRequired
};

export default SelectionSidebar;
