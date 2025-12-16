import { useState } from 'react';
import PropTypes from 'prop-types';
import { Clock } from 'lucide-react';

/**
 * Converte timestamp string (MM:SS ou HH:MM:SS) para segundos
 * @param {string} time - Timestamp no formato "MM:SS" ou "HH:MM:SS"
 * @returns {number} Tempo em segundos
 */
function parseTimeToSeconds(time) {
  if (!time) return 0;

  const parts = time.split(':').map(p => parseInt(p, 10));

  if (parts.length === 2) {
    // MM:SS
    const [minutes, seconds] = parts;
    return minutes * 60 + seconds;
  } else if (parts.length === 3) {
    // HH:MM:SS
    const [hours, minutes, seconds] = parts;
    return hours * 3600 + minutes * 60 + seconds;
  }

  return 0;
}

/**
 * ClickableTimestamp - Timestamp clicável que dispara callback com tempo em segundos
 * @param {Object} props
 * @param {string} props.time - Timestamp no formato "MM:SS" ou "HH:MM:SS"
 * @param {Function} props.onClick - Callback chamado com tempo em segundos: (seconds: number) => void
 * @param {string} [props.className] - Classes CSS adicionais
 * @param {boolean} [props.showIcon] - Mostrar ícone de relógio
 */
function ClickableTimestamp({ time, onClick, className = '', showIcon = false }) {
  const [isHovered, setIsHovered] = useState(false);

  const handleClick = (e) => {
    e.stopPropagation();
    const seconds = parseTimeToSeconds(time);
    onClick(seconds);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      e.stopPropagation();
      const seconds = parseTimeToSeconds(time);
      onClick(seconds);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`
        inline-flex items-center gap-1
        text-xs font-mono
        bg-light-gray
        px-2 py-1 rounded
        transition-all duration-200
        hover:bg-tmc-orange hover:text-white
        focus:outline-none focus:ring-2 focus:ring-tmc-orange focus:ring-offset-1
        cursor-pointer
        ${className}
      `}
      role="button"
      aria-label={`Ir para ${time} no vídeo`}
      title={isHovered ? `Ir para ${time} no vídeo` : ''}
    >
      {showIcon && <Clock className="w-3 h-3" aria-hidden="true" />}
      <span>{time}</span>
    </button>
  );
}

ClickableTimestamp.propTypes = {
  time: PropTypes.string.isRequired,
  onClick: PropTypes.func.isRequired,
  className: PropTypes.string,
  showIcon: PropTypes.bool
};

export default ClickableTimestamp;
