import { useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import { Play, Pause, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';
import ClickableTimestamp from './ClickableTimestamp';

/**
 * TranscriptionCard - Card de trecho da transcrição selecionável e expandível
 * @param {Object} props
 * @param {Object} props.segment - Dados do segmento
 * @param {boolean} props.isSelected - Se o card inteiro está selecionado
 * @param {Function} props.onToggle - Callback ao selecionar/desselecionar card inteiro
 * @param {Function} props.onPlaySegment - Callback ao reproduzir
 * @param {Function} props.onGoToMoment - Callback ao ir para momento (recebe segundos)
 * @param {Function} props.onTextSelect - Callback ao selecionar texto (segmentId, selectedText)
 * @param {Array<string>} props.textHighlights - Array de textos já destacados neste card
 */
function TranscriptionCard({
  segment,
  isSelected,
  onToggle,
  onPlaySegment,
  onGoToMoment,
  onTextSelect,
  textHighlights = []
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const handleCheckboxClick = useCallback((e) => {
    e.stopPropagation();
    onToggle(segment.id);
  }, [segment.id, onToggle]);

  const handleExpandToggle = useCallback((e) => {
    e.stopPropagation();
    setIsExpanded(prev => !prev);
  }, []);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setIsExpanded(prev => !prev);
    }
  }, []);

  const handlePlay = useCallback((e) => {
    e.stopPropagation();
    const newIsPlaying = !isPlaying;
    setIsPlaying(newIsPlaying);
    onPlaySegment(segment.id, newIsPlaying);
  }, [segment.id, isPlaying, onPlaySegment]);

  const handleCopy = useCallback(async (e) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(segment.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [segment.text]);

  // Capturar seleção de texto quando o card está expandido
  const handleMouseUp = useCallback((e) => {
    if (!isExpanded || !onTextSelect) return;

    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;

    const selectedText = selection.toString().trim();
    if (!selectedText || selectedText.length < 3) {
      selection.removeAllRanges();
      return;
    }

    // Verificar se a seleção está dentro do texto da transcrição
    const range = selection.getRangeAt(0);
    const container = range.commonAncestorContainer;
    const textElement = container.nodeType === Node.TEXT_NODE
      ? container.parentElement?.closest('[data-transcription-text]')
      : container.closest?.('[data-transcription-text]');

    if (!textElement) {
      selection.removeAllRanges();
      return;
    }

    // Verificar se já existe esse highlight (evitar duplicatas)
    const alreadyExists = textHighlights.some(h => h === selectedText);
    if (alreadyExists) {
      selection.removeAllRanges();
      return;
    }

    // Notificar seleção
    onTextSelect(segment.id, selectedText);
    selection.removeAllRanges();
  }, [isExpanded, onTextSelect, segment.id, textHighlights]);

  // Remover highlight clicando nele
  const handleRemoveHighlight = useCallback((highlightText, e) => {
    e.stopPropagation();
    if (onTextSelect) {
      // Enviar texto vazio ou null para indicar remoção
      // A lógica de remoção será implementada no componente pai
      onTextSelect(segment.id, highlightText, true); // true = remover
    }
  }, [segment.id, onTextSelect]);

  // Renderizar texto com highlights aplicados
  const renderTextWithHighlights = useCallback((text) => {
    if (textHighlights.length === 0) {
      return text;
    }

    // Criar regex para encontrar todos os highlights
    const escapedHighlights = textHighlights.map(h =>
      h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    );

    // Construir regex combinada
    const combinedRegex = new RegExp(
      `(${escapedHighlights.join('|')})`,
      'gi'
    );

    const parts = text.split(combinedRegex);

    return parts.map((part, index) => {
      const matchingHighlight = textHighlights.find(
        h => h.toLowerCase() === part.toLowerCase()
      );

      if (matchingHighlight) {
        return (
          <mark
            key={`highlight-${index}`}
            className="bg-yellow-200 hover:bg-red-200 cursor-pointer rounded px-0.5 transition-colors"
            onClick={(e) => handleRemoveHighlight(matchingHighlight, e)}
            title="Clique para remover destaque"
          >
            {part}
          </mark>
        );
      }

      return <span key={index}>{part}</span>;
    });
  }, [textHighlights, handleRemoveHighlight]);

  // Truncar texto para preview (quando colapsado)
  const getPreviewText = useCallback(() => {
    const maxChars = 150;
    if (segment.text.length <= maxChars) return segment.text;
    return segment.text.substring(0, maxChars) + '...';
  }, [segment.text]);

  return (
    <div
      className={`
        relative bg-white rounded-lg border p-4 mb-3
        transition-all duration-200
        ${isSelected
          ? 'border-[#2563EB] bg-[#EFF6FF]'
          : 'border-light-gray hover:border-blue-300 hover:shadow-md'
        }
      `}
    >
      {/* Header com checkbox, timestamp e botão expandir */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          {/* Checkbox visual - seleciona card inteiro */}
          <div
            role="checkbox"
            aria-checked={isSelected}
            aria-label="Selecionar card inteiro"
            tabIndex={0}
            onClick={handleCheckboxClick}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleCheckboxClick(e);
              }
            }}
            className={`
              w-5 h-5 rounded border-2 flex items-center justify-center
              transition-colors flex-shrink-0 cursor-pointer
              ${isSelected
                ? 'bg-[#2563EB] border-[#2563EB]'
                : 'border-medium-gray bg-white hover:border-[#2563EB]'
              }
            `}
          >
            {isSelected && (
              <Check className="w-3 h-3 text-white" />
            )}
          </div>

          {/* Timestamps clicáveis - intervalo */}
          <div className="flex items-center gap-1">
            <ClickableTimestamp
              time={segment.startTime}
              onClick={onGoToMoment}
              showIcon
            />
            <span className="text-medium-gray text-xs">-</span>
            <ClickableTimestamp
              time={segment.endTime}
              onClick={onGoToMoment}
              showIcon
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Topic tag */}
          {segment.topic && (
            <span className="text-[11px] bg-tmc-orange/10 text-tmc-orange px-2 py-0.5 rounded-full font-medium">
              {segment.topic}
            </span>
          )}

          {/* Botão expandir/colapsar */}
          <button
            type="button"
            onClick={handleExpandToggle}
            onKeyDown={handleKeyDown}
            className="flex items-center gap-1 text-xs text-medium-gray hover:text-tmc-orange transition-colors p-1 rounded hover:bg-tmc-orange/10"
            aria-expanded={isExpanded}
            aria-label={isExpanded ? 'Colapsar' : 'Expandir'}
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                <span className="hidden sm:inline">Colapsar</span>
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                <span className="hidden sm:inline">Expandir</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Texto da transcrição */}
      <div onMouseUp={handleMouseUp}>
        {isExpanded ? (
          // Texto completo com seleção por arrasto
          <div className="mb-4">
            <p
              data-transcription-text="true"
              className="text-dark-gray text-sm leading-relaxed selection:bg-blue-200 pl-3 border-l-2 border-tmc-orange/20"
              style={{ userSelect: 'text' }}
            >
              &ldquo;{renderTextWithHighlights(segment.text)}&rdquo;
            </p>
            {textHighlights.length > 0 && (
              <p className="text-xs text-medium-gray mt-2 italic">
                {textHighlights.length} trecho{textHighlights.length > 1 ? 's' : ''} destacado{textHighlights.length > 1 ? 's' : ''} • Arraste para selecionar mais • Clique no destaque para remover
              </p>
            )}
            {!textHighlights.length && onTextSelect && (
              <p className="text-xs text-medium-gray mt-2 italic">
                Arraste o mouse para selecionar texto específico
              </p>
            )}
          </div>
        ) : (
          // Preview do texto (colapsado)
          <p className="text-dark-gray text-sm leading-relaxed mb-4">
            &ldquo;{getPreviewText()}&rdquo;
          </p>
        )}
      </div>

      {/* Ações */}
      <div className="flex items-center gap-3 pt-3 border-t border-light-gray">
        <button
          type="button"
          onClick={handlePlay}
          className="flex items-center gap-1.5 text-sm text-medium-gray hover:text-tmc-orange transition-colors"
          aria-label={isPlaying ? 'Pausar trecho' : 'Ouvir trecho'}
        >
          {isPlaying ? (
            <Pause className="w-4 h-4" aria-hidden="true" />
          ) : (
            <Play className="w-4 h-4" aria-hidden="true" />
          )}
          <span className="hidden sm:inline">{isPlaying ? 'Pausar' : 'Ouvir'}</span>
          {isPlaying && (
            <span className="ml-1 flex items-center gap-0.5">
              <span className="w-1 h-3 bg-tmc-orange rounded-full animate-pulse" />
              <span className="w-1 h-4 bg-tmc-orange rounded-full animate-pulse" style={{ animationDelay: '75ms' }} />
              <span className="w-1 h-2 bg-tmc-orange rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-sm text-medium-gray hover:text-tmc-orange transition-colors"
          aria-label={copied ? 'Texto copiado!' : 'Copiar texto'}
        >
          {copied ? (
            <>
              <Check className="w-4 h-4 text-success" aria-hidden="true" />
              <span className="hidden sm:inline text-success">Copiado!</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" aria-hidden="true" />
              <span className="hidden sm:inline">Copiar</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

TranscriptionCard.propTypes = {
  segment: PropTypes.shape({
    id: PropTypes.string.isRequired,
    startTime: PropTypes.string.isRequired,
    endTime: PropTypes.string.isRequired,
    text: PropTypes.string.isRequired,
    topic: PropTypes.string
  }).isRequired,
  isSelected: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  onPlaySegment: PropTypes.func.isRequired,
  onGoToMoment: PropTypes.func.isRequired,
  onTextSelect: PropTypes.func, // (segmentId, selectedText, isRemove?) => void
  textHighlights: PropTypes.arrayOf(PropTypes.string) // textos já destacados neste card
};

export default TranscriptionCard;
