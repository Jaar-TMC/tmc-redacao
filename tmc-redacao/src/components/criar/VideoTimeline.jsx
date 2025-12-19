import { useMemo, useCallback } from 'react';
import PropTypes from 'prop-types';
import { Clock } from 'lucide-react';

/**
 * VideoTimeline - Timeline visual interativa do video
 *
 * Mostra marcadores clicaveis nos momentos dos topicos da transcricao.
 */

// Converter timestamp "MM:SS" ou "HH:MM:SS" para segundos
const parseTimeToSeconds = (time) => {
  if (!time) return 0;
  const parts = time.split(':').map(p => parseInt(p, 10));
  if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  } else if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  return 0;
};

// Converter segundos para "MM:SS"
const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

const VideoTimeline = ({
  duration, // Duracao total em segundos
  markers = [], // Array de { id, time, label, selected }
  currentTime = 0, // Tempo atual do video
  onMarkerClick, // Callback quando clica em um marcador
  className = ''
}) => {
  // Calcular posicao percentual de cada marcador (com margem para não cortar bordas)
  const markerPositions = useMemo(() => {
    if (!duration || duration === 0) return [];

    return markers.map(marker => ({
      ...marker,
      // Escala de 4% a 96% para dar margem nas bordas
      position: 4 + (parseTimeToSeconds(marker.time) / duration) * 92
    }));
  }, [markers, duration]);

  // Posicao do indicador de tempo atual (mesma escala)
  const currentPosition = useMemo(() => {
    if (!duration || duration === 0) return 4;
    return 4 + (currentTime / duration) * 92;
  }, [currentTime, duration]);

  // Gerar labels de tempo para o eixo
  const timeLabels = useMemo(() => {
    if (!duration) return [];

    const labelCount = Math.min(5, Math.ceil(duration / 60));
    const interval = duration / labelCount;

    return Array.from({ length: labelCount + 1 }, (_, i) => ({
      time: Math.round(i * interval),
      // Mesma escala de 4% a 96%
      position: 4 + (i * interval / duration) * 92
    }));
  }, [duration]);

  const handleMarkerClick = useCallback((marker) => {
    if (onMarkerClick) {
      onMarkerClick(parseTimeToSeconds(marker.time), marker.id);
    }
  }, [onMarkerClick]);

  return (
    <div className={`bg-white rounded-xl border border-light-gray overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-5 py-3 border-b border-light-gray bg-off-white/50">
        <div className="flex items-center gap-2">
          <Clock size={16} className="text-tmc-orange" />
          <h3 className="text-sm font-semibold text-dark-gray">
            LINHA DO TEMPO
          </h3>
        </div>
      </div>

      {/* Timeline Container */}
      <div className="px-5 py-5">
        {/* Timeline Track */}
        <div className="relative h-10 mb-1">
          {/* Linha base */}
          <div className="absolute top-1/2 left-[4%] right-[4%] h-1.5 bg-light-gray rounded-full transform -translate-y-1/2" />

          {/* Progresso atual */}
          <div
            className="absolute top-1/2 left-[4%] h-1.5 bg-tmc-orange/30 rounded-full transform -translate-y-1/2 transition-all duration-300"
            style={{ width: `${Math.min(currentPosition - 4, 92)}%` }}
          />

          {/* Indicador de tempo atual */}
          <div
            className="absolute top-1/2 w-3.5 h-3.5 bg-tmc-orange rounded-full transform -translate-y-1/2 -translate-x-1/2 transition-all duration-300 shadow-md z-20 ring-2 ring-white"
            style={{ left: `${Math.min(currentPosition, 96)}%` }}
          />

          {/* Marcadores dos topicos */}
          {markerPositions.map((marker) => (
            <button
              key={marker.id}
              onClick={() => handleMarkerClick(marker)}
              className={`
                absolute top-1/2 transform -translate-y-1/2 -translate-x-1/2
                w-5 h-5 rounded-full border-2 transition-all duration-200 z-10
                hover:scale-110 focus:outline-none focus:ring-2 focus:ring-tmc-orange focus:ring-offset-2
                ${marker.selected
                  ? 'bg-tmc-orange border-tmc-orange shadow-md'
                  : 'bg-white border-medium-gray hover:border-tmc-orange hover:shadow-sm'
                }
              `}
              style={{ left: `${marker.position}%` }}
              title={`${marker.label || ''} - ${marker.time}`}
              aria-label={`Ir para ${marker.time}${marker.label ? ` - ${marker.label}` : ''}`}
            >
              {marker.selected && (
                <span className="absolute inset-0 flex items-center justify-center">
                  <span className="w-2 h-2 bg-white rounded-full" />
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Labels de tempo */}
        <div className="relative h-5 mb-4">
          {timeLabels.map((label, index) => (
            <span
              key={index}
              className="absolute text-[11px] font-mono text-medium-gray transform -translate-x-1/2"
              style={{ left: `${label.position}%` }}
            >
              {formatTime(label.time)}
            </span>
          ))}
        </div>

        {/* Legenda e Dica */}
        <div className="flex items-center justify-between pt-3 border-t border-light-gray">
          <div className="flex items-center gap-4 text-xs text-medium-gray">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-tmc-orange shadow-sm" />
              <span>Selecionado</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full border-2 border-medium-gray bg-white" />
              <span>Não selecionado</span>
            </div>
          </div>
          <p className="text-xs text-medium-gray">
            Clique para pular ao momento
          </p>
        </div>
      </div>
    </div>
  );
};

VideoTimeline.propTypes = {
  duration: PropTypes.number.isRequired,
  markers: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    time: PropTypes.string.isRequired,
    label: PropTypes.string,
    selected: PropTypes.bool
  })),
  currentTime: PropTypes.number,
  onMarkerClick: PropTypes.func,
  className: PropTypes.string
};

export default VideoTimeline;
