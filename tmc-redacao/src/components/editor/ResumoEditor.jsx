import { useState, useCallback, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  FileText,
  ChevronDown,
  ChevronUp,
  Sparkles,
  X,
  Plus,
  Loader2
} from 'lucide-react';

/**
 * ResumoEditor - Editable bullet-point summary for an article
 *
 * Displays 2-6 key points (resumo) that appear before the article body.
 * Each bullet is inline-editable, and the list supports add/remove/reorder.
 * Optionally supports AI regeneration via onRegenerate callback.
 */
const ResumoEditor = ({
  bullets = [],
  onChange,
  onRegenerate = null,
  isRegenerating = false,
  disabled = false,
  maxBullets = 6,
  minBullets = 2,
}) => {
  const [isExpanded, setIsExpanded] = useState(bullets.length > 0);
  const inputRefs = useRef([]);
  const [focusIndex, setFocusIndex] = useState(null);

  // Auto-focus newly added bullet
  useEffect(() => {
    if (focusIndex !== null && inputRefs.current[focusIndex]) {
      inputRefs.current[focusIndex].focus();
      requestAnimationFrame(() => setFocusIndex(null));
    }
  }, [focusIndex, bullets.length]);

  const handleBulletChange = useCallback((index, value) => {
    const updated = [...bullets];
    updated[index] = value;
    onChange(updated);
  }, [bullets, onChange]);

  const handleAddBullet = useCallback(() => {
    if (bullets.length >= maxBullets) return;
    const updated = [...bullets, ''];
    onChange(updated);
    setFocusIndex(updated.length - 1);
  }, [bullets, maxBullets, onChange]);

  const handleRemoveBullet = useCallback((index) => {
    if (bullets.length <= minBullets) return;
    const updated = bullets.filter((_, i) => i !== index);
    onChange(updated);
  }, [bullets, minBullets, onChange]);

  const handleBlur = useCallback((index) => {
    const value = bullets[index];
    if (value !== undefined && value.trim() === '' && bullets.length > minBullets) {
      const updated = bullets.filter((_, i) => i !== index);
      onChange(updated);
    }
  }, [bullets, minBullets, onChange]);

  const handleKeyDown = useCallback((e, index) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (bullets.length < maxBullets) {
        const updated = [...bullets];
        updated.splice(index + 1, 0, '');
        onChange(updated);
        setFocusIndex(index + 1);
      }
    }
    if (e.key === 'Backspace' && bullets[index] === '' && bullets.length > minBullets) {
      e.preventDefault();
      const updated = bullets.filter((_, i) => i !== index);
      onChange(updated);
      const newFocus = Math.max(0, index - 1);
      setFocusIndex(newFocus);
    }
  }, [bullets, maxBullets, minBullets, onChange]);

  const hasBullets = bullets.length > 0;
  const canAdd = bullets.length < maxBullets;
  const canRemove = bullets.length > minBullets;

  return (
    <div className="bg-slate-50 border border-slate-200 border-l-4 border-l-blue-400 rounded-lg transition-all duration-200">
      {/* Header */}
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="w-full flex items-center gap-2 px-4 py-3 text-left group"
        aria-expanded={isExpanded}
      >
        <FileText size={16} className="text-blue-500 shrink-0" />
        <span className="text-sm font-medium text-dark-gray">Resumo da Mat&eacute;ria</span>

        {hasBullets && (
          <span className="inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
            {bullets.length}
          </span>
        )}

        <div className="ml-auto flex items-center gap-2">
          {/* Regenerate button */}
          {onRegenerate && (
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => {
                e.stopPropagation();
                if (!isRegenerating && !disabled) onRegenerate();
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.stopPropagation();
                  if (!isRegenerating && !disabled) onRegenerate();
                }
              }}
              className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded transition-colors ${
                isRegenerating || disabled
                  ? 'text-light-gray cursor-not-allowed'
                  : 'text-blue-600 hover:bg-blue-100 cursor-pointer'
              }`}
              aria-label="Regenerar resumo"
            >
              {isRegenerating ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Sparkles size={14} />
              )}
              Regenerar
            </span>
          )}

          {/* Collapse toggle */}
          {isExpanded ? (
            <ChevronUp size={16} className="text-medium-gray group-hover:text-dark-gray transition-colors" />
          ) : (
            <ChevronDown size={16} className="text-medium-gray group-hover:text-dark-gray transition-colors" />
          )}
        </div>
      </button>

      {/* Body */}
      {isExpanded && (
        <div className="px-4 pb-4 transition-all duration-200">
          {hasBullets ? (
            <div className="space-y-2">
              {/* Bullet rows */}
              {bullets.map((bullet, index) => (
                <div
                  key={index}
                  className="group/row flex items-center gap-2"
                >
                  {/* Bullet dot */}
                  <span className="text-blue-400 text-sm shrink-0 select-none" aria-hidden="true">
                    &#9679;
                  </span>

                  {/* Editable input */}
                  <input
                    ref={(el) => { inputRefs.current[index] = el; }}
                    type="text"
                    value={bullet}
                    onChange={(e) => handleBulletChange(index, e.target.value)}
                    onBlur={() => handleBlur(index)}
                    onKeyDown={(e) => handleKeyDown(e, index)}
                    disabled={disabled}
                    placeholder="Escreva um ponto-chave..."
                    className={`flex-1 bg-transparent text-sm text-dark-gray placeholder:text-light-gray
                      border-b border-transparent focus:border-blue-300 focus:outline-none
                      py-1 transition-colors duration-200 ${
                        disabled ? 'cursor-not-allowed opacity-60' : ''
                      }`}
                    aria-label={`Ponto ${index + 1} do resumo`}
                  />

                  {/* Delete button - visible on hover/focus */}
                  {!disabled && (
                    <button
                      type="button"
                      onClick={() => handleRemoveBullet(index)}
                      disabled={!canRemove}
                      className={`opacity-0 group-hover/row:opacity-100 focus:opacity-100
                        p-1 rounded transition-all duration-200 shrink-0 ${
                          canRemove
                            ? 'text-medium-gray hover:text-red-500 hover:bg-red-50 cursor-pointer'
                            : 'text-light-gray cursor-not-allowed'
                        }`}
                      aria-label={`Remover ponto ${index + 1}`}
                      tabIndex={-1}
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>
              ))}

              {/* Add button */}
              {!disabled && (
                <button
                  type="button"
                  onClick={handleAddBullet}
                  disabled={!canAdd}
                  className={`flex items-center gap-1.5 mt-1 px-2 py-1 text-xs font-medium rounded transition-colors duration-200 ${
                    canAdd
                      ? 'text-blue-600 hover:bg-blue-50 cursor-pointer'
                      : 'text-light-gray cursor-not-allowed'
                  }`}
                >
                  <Plus size={14} />
                  Adicionar ponto
                </button>
              )}
            </div>
          ) : (
            /* Empty state */
            <p className="text-xs text-medium-gray italic py-2">
              Nenhum resumo gerado. Gere a mat&eacute;ria para obter bullet points autom&aacute;ticos.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

ResumoEditor.propTypes = {
  bullets: PropTypes.arrayOf(PropTypes.string),
  onChange: PropTypes.func.isRequired,
  onRegenerate: PropTypes.func,
  isRegenerating: PropTypes.bool,
  disabled: PropTypes.bool,
  maxBullets: PropTypes.number,
  minBullets: PropTypes.number,
};

export default ResumoEditor;
