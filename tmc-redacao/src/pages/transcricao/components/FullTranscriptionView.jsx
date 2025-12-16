import { useState, useCallback, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Clock, Tag, Trash2, Info } from 'lucide-react';

/**
 * FullTranscriptionView - Visão de transcrição completa com seleção de texto por arrasto
 */
function FullTranscriptionView({
  segments,
  onSelectionChange
}) {
  const [highlights, setHighlights] = useState([]);

  // Agrupar segmentos por tópico
  const groupedSegments = segments.reduce((groups, segment) => {
    const lastGroup = groups[groups.length - 1];
    if (lastGroup && lastGroup.topic === segment.topic) {
      lastGroup.segments.push(segment);
      lastGroup.text += ' ' + segment.text;
    } else {
      groups.push({
        topic: segment.topic,
        timestamp: segment.startTime,
        segments: [segment],
        text: segment.text
      });
    }
    return groups;
  }, []);

  // Capturar seleção de texto
  const handleMouseUp = useCallback(() => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;

    const selectedText = selection.toString().trim();
    if (!selectedText || selectedText.length < 3) {
      selection.removeAllRanges();
      return;
    }

    // Verificar se a seleção está dentro de um parágrafo de transcrição
    const range = selection.getRangeAt(0);
    const container = range.commonAncestorContainer;
    const paragraph = container.nodeType === Node.TEXT_NODE
      ? container.parentElement?.closest('[data-transcription-text]')
      : container.closest?.('[data-transcription-text]');

    if (!paragraph) {
      selection.removeAllRanges();
      return;
    }

    // Verificar se já existe esse highlight (evitar duplicatas)
    const alreadyExists = highlights.some(h => h.text === selectedText);
    if (alreadyExists) {
      selection.removeAllRanges();
      return;
    }

    // Adicionar novo highlight
    const newHighlight = {
      id: Date.now().toString(),
      text: selectedText
    };

    setHighlights(prev => [...prev, newHighlight]);
    selection.removeAllRanges();
  }, [highlights]);

  // Remover highlight
  const removeHighlight = useCallback((highlightId, e) => {
    e.stopPropagation();
    setHighlights(prev => prev.filter(h => h.id !== highlightId));
  }, []);

  // Limpar todos os highlights
  const clearAllHighlights = useCallback(() => {
    setHighlights([]);
  }, []);

  // Notificar mudanças na seleção
  useEffect(() => {
    if (onSelectionChange) {
      onSelectionChange(highlights);
    }
  }, [highlights, onSelectionChange]);

  // Renderizar texto com highlights aplicados
  const renderTextWithHighlights = useCallback((text) => {
    if (highlights.length === 0) {
      return text;
    }

    // Criar regex para encontrar todos os highlights
    const escapedHighlights = highlights.map(h => ({
      ...h,
      regex: h.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    }));

    // Construir regex combinada
    const combinedRegex = new RegExp(
      `(${escapedHighlights.map(h => h.regex).join('|')})`,
      'gi'
    );

    const parts = text.split(combinedRegex);

    return parts.map((part, index) => {
      const matchingHighlight = highlights.find(
        h => h.text.toLowerCase() === part.toLowerCase()
      );

      if (matchingHighlight) {
        return (
          <mark
            key={`${matchingHighlight.id}-${index}`}
            className="bg-yellow-200 hover:bg-red-200 cursor-pointer rounded px-0.5 transition-colors"
            onClick={(e) => removeHighlight(matchingHighlight.id, e)}
            title="Clique para remover"
          >
            {part}
          </mark>
        );
      }

      return <span key={index}>{part}</span>;
    });
  }, [highlights, removeHighlight]);

  // Calcular estatísticas
  const totalWords = highlights.reduce((acc, h) => acc + h.text.split(/\s+/).filter(w => w).length, 0);

  return (
    <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
      {/* Header */}
      <div className="bg-off-white px-4 py-3 border-b border-light-gray">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-dark-gray flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Transcrição Completa
            </h3>
            <p className="text-xs text-medium-gray mt-1 flex items-center gap-1">
              <Info className="w-3 h-3" />
              Selecione texto arrastando o mouse • Clique no highlight para remover
            </p>
          </div>

          {highlights.length > 0 && (
            <button
              type="button"
              onClick={clearAllHighlights}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Limpar ({highlights.length})
            </button>
          )}
        </div>
      </div>

      {/* Conteúdo da transcrição */}
      <div
        className="p-6 max-h-[500px] overflow-y-auto"
        onMouseUp={handleMouseUp}
      >
        <div className="space-y-6">
          {groupedSegments.map((group, groupIndex) => (
            <div key={groupIndex}>
              {/* Indicador de tópico */}
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center gap-1.5 bg-tmc-orange/10 text-tmc-orange px-3 py-1.5 rounded-full text-xs font-semibold">
                  <Tag className="w-3.5 h-3.5" />
                  {group.topic}
                  <span className="text-tmc-orange/60 font-normal ml-1">{group.timestamp}</span>
                </span>
                <div className="flex-1 h-px bg-gradient-to-r from-tmc-orange/20 to-transparent" />
              </div>

              {/* Texto do grupo */}
              <p
                data-transcription-text="true"
                className="text-dark-gray text-[15px] leading-relaxed pl-4 border-l-2 border-tmc-orange/20 selection:bg-blue-200"
                style={{ userSelect: 'text' }}
              >
                {renderTextWithHighlights(group.text)}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Footer com resumo */}
      <div className="bg-off-white px-4 py-3 border-t border-light-gray">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-xs text-medium-gray">
            <span>{segments.length} trechos</span>
            <span>•</span>
            <span>{groupedSegments.length} tópicos</span>
          </div>

          {highlights.length > 0 ? (
            <div className="flex items-center gap-3 text-xs">
              <span className="text-medium-gray">
                <strong className="text-dark-gray font-semibold">{highlights.length}</strong> seleções
              </span>
              <span className="text-medium-gray">•</span>
              <span className="text-medium-gray">
                <strong className="text-dark-gray font-semibold">~{totalWords}</strong> palavras
              </span>
            </div>
          ) : (
            <span className="text-xs text-medium-gray italic">
              Nenhum trecho selecionado
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

FullTranscriptionView.propTypes = {
  segments: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    startTime: PropTypes.string.isRequired,
    endTime: PropTypes.string.isRequired,
    text: PropTypes.string.isRequired,
    topic: PropTypes.string
  })).isRequired,
  onSelectionChange: PropTypes.func
};

export default FullTranscriptionView;
