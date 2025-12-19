import { useMemo } from 'react';
import PropTypes from 'prop-types';
import { Clock } from 'lucide-react';

/**
 * IntervalFilter - Filtros de intervalo de tempo para video
 *
 * Permite filtrar transcricao por intervalos de minutos.
 */

// Gerar intervalos baseados na duracao
const generateIntervals = (duration, intervalSize = 180) => {
  if (!duration || duration === 0) return [];

  const intervals = [];
  let start = 0;

  while (start < duration) {
    const end = Math.min(start + intervalSize, duration);
    intervals.push({
      id: `${start}-${end}`,
      start,
      end,
      label: `${formatTime(start)}-${formatTime(end)}`
    });
    start = end;
  }

  return intervals;
};

// Formatar segundos para "MM:SS"
const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

const IntervalFilter = ({
  duration,
  activeIntervals = [], // Array de IDs de intervalos ativos
  onToggleInterval,
  onShowAll,
  intervalSize = 180, // 3 minutos por padrao
  className = ''
}) => {
  const intervals = useMemo(() => generateIntervals(duration, intervalSize), [duration, intervalSize]);

  const allActive = activeIntervals.length === 0 || activeIntervals.length === intervals.length;

  return (
    <div className={`${className}`}>
      <div className="flex items-center gap-2 mb-3">
        <Clock size={16} className="text-medium-gray" />
        <span className="text-sm font-medium text-dark-gray">Filtrar por Intervalo</span>
      </div>

      <div className="flex flex-wrap gap-2">
        {/* Botao Todos */}
        <button
          onClick={onShowAll}
          className={`
            px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors
            ${allActive
              ? 'bg-tmc-orange text-white border-tmc-orange'
              : 'bg-white text-medium-gray border-light-gray hover:border-tmc-orange'
            }
          `}
        >
          Todos
        </button>

        {/* Botoes de intervalo */}
        {intervals.map((interval) => {
          const isActive = activeIntervals.includes(interval.id);

          return (
            <button
              key={interval.id}
              onClick={() => onToggleInterval(interval.id)}
              className={`
                px-3 py-1.5 text-xs font-mono rounded-lg border transition-colors
                ${isActive
                  ? 'bg-tmc-orange text-white border-tmc-orange'
                  : 'bg-white text-medium-gray border-light-gray hover:border-tmc-orange hover:text-tmc-orange'
                }
              `}
            >
              {interval.label}
            </button>
          );
        })}
      </div>
    </div>
  );
};

IntervalFilter.propTypes = {
  duration: PropTypes.number.isRequired,
  activeIntervals: PropTypes.arrayOf(PropTypes.string),
  onToggleInterval: PropTypes.func.isRequired,
  onShowAll: PropTypes.func.isRequired,
  intervalSize: PropTypes.number,
  className: PropTypes.string
};

export default IntervalFilter;
