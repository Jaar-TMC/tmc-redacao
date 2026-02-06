import { useCallback } from 'react';
import PropTypes from 'prop-types';
import { Flame, Zap, Sun } from 'lucide-react';

const URGENCY_OPTIONS = [
  {
    value: null,
    label: 'Todas',
    mobileLabel: 'Todas',
    icon: null,
    color: 'gray',
    countKey: 'all',
    ariaLabel: (count) => `Todas as matérias, ${count} matérias`,
  },
  {
    value: 1,
    label: 'Última hora',
    mobileLabel: '1h',
    icon: Flame,
    color: 'red',
    countKey: 'now',
    ariaLabel: (count) => `Última hora, ${count} matérias`,
  },
  {
    value: 3,
    label: 'Últimas 3h',
    mobileLabel: '3h',
    icon: Zap,
    color: 'amber',
    countKey: 'recent',
    ariaLabel: (count) => `Últimas 3 horas, ${count} matérias`,
  },
  {
    value: 8,
    label: 'Últimas 8h',
    mobileLabel: '8h',
    icon: Sun,
    color: 'blue',
    countKey: 'today',
    ariaLabel: (count) => `Últimas 8 horas, ${count} matérias`,
  },
];

const colorClasses = {
  gray: {
    active: 'bg-gray-500 border-gray-500 text-white font-semibold shadow-sm',
    hover: 'hover:bg-gray-50 hover:border-gray-400 hover:text-gray-600',
    badge: 'bg-gray-100 text-gray-600',
    badgeActive: 'bg-white/20 text-white',
  },
  red: {
    active: 'bg-red-500 border-red-500 text-white font-semibold shadow-sm',
    hover: 'hover:bg-red-50 hover:border-red-400 hover:text-red-500',
    badge: 'bg-red-100 text-red-600',
    badgeActive: 'bg-white/20 text-white',
  },
  amber: {
    active: 'bg-amber-500 border-amber-500 text-white font-semibold shadow-sm',
    hover: 'hover:bg-amber-50 hover:border-amber-400 hover:text-amber-500',
    badge: 'bg-amber-100 text-amber-600',
    badgeActive: 'bg-white/20 text-white',
  },
  blue: {
    active: 'bg-blue-500 border-blue-500 text-white font-semibold shadow-sm',
    hover: 'hover:bg-blue-50 hover:border-blue-400 hover:text-blue-500',
    badge: 'bg-blue-100 text-blue-600',
    badgeActive: 'bg-white/20 text-white',
  },
};

function UrgencyChips({ counts, activeUrgency = null, onUrgencyChange }) {
  const hasCounts = counts && (counts.now > 0 || counts.recent > 0 || counts.today > 0 || counts.all > 0);
  const handleKeyDown = useCallback(
    (e) => {
      const currentIndex = URGENCY_OPTIONS.findIndex(
        (opt) => opt.value === activeUrgency
      );
      let newIndex = currentIndex;

      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        newIndex = (currentIndex + 1) % URGENCY_OPTIONS.length;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        newIndex =
          (currentIndex - 1 + URGENCY_OPTIONS.length) % URGENCY_OPTIONS.length;
      } else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        return;
      } else {
        return;
      }

      onUrgencyChange(URGENCY_OPTIONS[newIndex].value);
      // Focus the new chip
      const chipEl = e.currentTarget.parentElement?.querySelector(
        `[data-urgency-index="${newIndex}"]`
      );
      chipEl?.focus();
    },
    [activeUrgency, onUrgencyChange]
  );

  return (
    <div
      className="flex items-center gap-2 flex-wrap"
      role="radiogroup"
      aria-label="Filtrar por frescor"
    >
      {URGENCY_OPTIONS.map((option, index) => {
        const isActive = activeUrgency === option.value;
        const count = counts?.[option.countKey] ?? 0;
        const colors = colorClasses[option.color];
        const Icon = option.icon;

        const isPulse =
          option.value === 1 && !isActive && hasCounts && count > 0;

        return (
          <button
            key={option.value ?? 'all'}
            type="button"
            role="radio"
            aria-checked={isActive}
            aria-label={option.ariaLabel(count)}
            data-urgency-index={index}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onUrgencyChange(isActive && option.value !== null ? null : option.value)}
            onKeyDown={handleKeyDown}
            className={`
              inline-flex items-center gap-1.5 rounded-full border text-sm font-medium
              transition-all duration-200 cursor-pointer
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500
              px-3.5 py-1.5
              md:px-3.5 md:py-1.5
              ${isActive ? colors.active : `bg-white border-light-gray text-medium-gray ${colors.hover}`}
              ${isPulse ? 'urgency-pulse' : ''}
            `}
          >
            {Icon && (
              <Icon
                className="w-4 h-4 shrink-0"
                aria-hidden="true"
              />
            )}
            <span className="hidden md:inline">{option.label}</span>
            <span className="md:hidden">{option.mobileLabel}</span>
            {hasCounts && (
              <span
                className={`
                  text-xs rounded-full px-1.5 py-0.5 min-w-[1.25rem] text-center font-medium
                  ${isActive ? colors.badgeActive : colors.badge}
                `}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

UrgencyChips.propTypes = {
  counts: PropTypes.shape({
    now: PropTypes.number,
    recent: PropTypes.number,
    today: PropTypes.number,
    all: PropTypes.number,
  }),
  activeUrgency: PropTypes.oneOf([null, 1, 3, 8]),
  onUrgencyChange: PropTypes.func.isRequired,
};

export default UrgencyChips;
