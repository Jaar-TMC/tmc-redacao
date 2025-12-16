import { useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import { Play, Pause, ExternalLink, Copy, Check } from 'lucide-react';

/**
 * TranscriptionCard - Card de trecho da transcrição selecionável
 * @param {Object} props
 * @param {Object} props.segment - Dados do segmento
 * @param {boolean} props.isSelected - Se está selecionado
 * @param {Function} props.onToggle - Callback ao selecionar/desselecionar
 * @param {Function} props.onPlaySegment - Callback ao reproduzir
 * @param {Function} props.onGoToMoment - Callback ao ir para momento
 */
function TranscriptionCard({
  segment,
  isSelected,
  onToggle,
  onPlaySegment,
  onGoToMoment
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleClick = useCallback(() => {
    onToggle(segment.id);
  }, [segment.id, onToggle]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onToggle(segment.id);
    }
  }, [segment.id, onToggle]);

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

  const handleGoTo = useCallback((e) => {
    e.stopPropagation();
    onGoToMoment(segment.startTime);
  }, [segment.startTime, onGoToMoment]);

  return (
    <div
      role="checkbox"
      aria-checked={isSelected}
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={`
        relative bg-white rounded-lg border p-4 mb-3 cursor-pointer
        transition-all duration-200
        ${isSelected
          ? 'border-[#2563EB] bg-[#EFF6FF]'
          : 'border-light-gray hover:border-blue-300 hover:shadow-md'
        }
      `}
    >
      {/* Header com checkbox e timestamp */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          {/* Checkbox visual */}
          <div
            className={`
              w-5 h-5 rounded border-2 flex items-center justify-center
              transition-colors flex-shrink-0
              ${isSelected
                ? 'bg-[#2563EB] border-[#2563EB]'
                : 'border-medium-gray bg-white'
              }
            `}
            aria-hidden="true"
          >
            {isSelected && (
              <Check className="w-3 h-3 text-white" />
            )}
          </div>

          {/* Timestamp */}
          <span className="text-xs font-mono text-medium-gray bg-light-gray px-2 py-1 rounded">
            {segment.startTime} - {segment.endTime}
          </span>
        </div>

        {/* Speaker tag */}
        {segment.speaker && (
          <span className="text-[11px] bg-[#DBEAFE] text-[#1D4ED8] px-1.5 py-0.5 rounded font-medium">
            {segment.speaker}
          </span>
        )}
      </div>

      {/* Texto da transcrição */}
      <p className="text-dark-gray text-sm leading-relaxed mb-4">
        &ldquo;{segment.text}&rdquo;
      </p>

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
          onClick={handleGoTo}
          className="flex items-center gap-1.5 text-sm text-medium-gray hover:text-tmc-orange transition-colors"
          aria-label="Ir para momento no vídeo"
        >
          <ExternalLink className="w-4 h-4" aria-hidden="true" />
          <span className="hidden sm:inline">Ir para momento</span>
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
    speaker: PropTypes.string
  }).isRequired,
  isSelected: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  onPlaySegment: PropTypes.func.isRequired,
  onGoToMoment: PropTypes.func.isRequired
};

export default TranscriptionCard;
