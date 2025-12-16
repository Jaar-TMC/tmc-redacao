# Component Patterns - TMC Redação

Exemplos práticos de componentes seguindo os padrões do projeto.

---

## Cards

### Card Básico

```jsx
import PropTypes from 'prop-types';

function Card({ children, className = '' }) {
  return (
    <div
      className={`
        bg-white rounded-lg shadow-sm border border-gray-200
        ${className}
      `}
    >
      {children}
    </div>
  );
}

Card.propTypes = {
  children: PropTypes.node.isRequired,
  className: PropTypes.string
};

export default Card;
```

### Card Selecionável

```jsx
import { useCallback } from 'react';
import PropTypes from 'prop-types';
import { Check } from 'lucide-react';

function SelectableCard({
  id,
  children,
  isSelected,
  onSelect,
  disabled = false
}) {
  const handleClick = useCallback(() => {
    if (!disabled) {
      onSelect(id);
    }
  }, [id, onSelect, disabled]);

  const handleKeyDown = useCallback((e) => {
    if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
      e.preventDefault();
      onSelect(id);
    }
  }, [id, onSelect, disabled]);

  return (
    <div
      role="checkbox"
      aria-checked={isSelected}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={`
        relative bg-white rounded-lg border-2 p-4 cursor-pointer
        transition-all duration-200
        ${isSelected
          ? 'border-primary-500 bg-orange-50'
          : 'border-gray-200 hover:border-gray-300 hover:shadow-md'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      {/* Checkbox visual */}
      <div
        className={`
          absolute top-3 left-3 w-5 h-5 rounded border-2
          flex items-center justify-center transition-colors
          ${isSelected
            ? 'bg-primary-500 border-primary-500'
            : 'border-gray-300 bg-white'
          }
        `}
      >
        {isSelected && (
          <Check className="w-3 h-3 text-white" aria-hidden="true" />
        )}
      </div>

      {/* Conteúdo com padding para o checkbox */}
      <div className="pl-8">
        {children}
      </div>
    </div>
  );
}

SelectableCard.propTypes = {
  id: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
  isSelected: PropTypes.bool.isRequired,
  onSelect: PropTypes.func.isRequired,
  disabled: PropTypes.bool
};

export default SelectableCard;
```

### Card de Trecho de Transcrição

```jsx
import { useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import { Play, Pause, ExternalLink, Copy, Check } from 'lucide-react';

function TranscriptionCard({
  segment,
  isSelected,
  onSelect,
  onPlaySegment,
  onGoToMoment
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [copied, setCopied] = useState(false);

  const handlePlay = useCallback((e) => {
    e.stopPropagation();
    setIsPlaying(prev => !prev);
    onPlaySegment(segment.id, !isPlaying);
  }, [segment.id, isPlaying, onPlaySegment]);

  const handleCopy = useCallback(async (e) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(segment.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
      onClick={() => onSelect(segment.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(segment.id);
        }
      }}
      className={`
        relative bg-white rounded-lg border-2 p-4 cursor-pointer
        transition-all duration-200
        ${isSelected
          ? 'border-primary-500 bg-orange-50'
          : 'border-gray-200 hover:border-gray-300 hover:shadow-md'
        }
      `}
    >
      {/* Header com checkbox e timestamp */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          {/* Checkbox */}
          <div
            className={`
              w-5 h-5 rounded border-2 flex items-center justify-center
              transition-colors
              ${isSelected
                ? 'bg-primary-500 border-primary-500'
                : 'border-gray-300 bg-white'
              }
            `}
          >
            {isSelected && (
              <Check className="w-3 h-3 text-white" aria-hidden="true" />
            )}
          </div>

          {/* Timestamp */}
          <span className="text-sm font-mono text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {segment.startTime} - {segment.endTime}
          </span>
        </div>

        {/* Speaker tag (se houver) */}
        {segment.speaker && (
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
            {segment.speaker}
          </span>
        )}
      </div>

      {/* Texto da transcrição */}
      <p className="text-gray-700 text-sm leading-relaxed mb-4">
        "{segment.text}"
      </p>

      {/* Ações */}
      <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
        <button
          type="button"
          onClick={handlePlay}
          className="flex items-center gap-1 text-sm text-gray-600 hover:text-primary-500 transition-colors"
          aria-label={isPlaying ? 'Pausar trecho' : 'Ouvir trecho'}
        >
          {isPlaying ? (
            <Pause className="w-4 h-4" aria-hidden="true" />
          ) : (
            <Play className="w-4 h-4" aria-hidden="true" />
          )}
          <span>{isPlaying ? 'Pausar' : 'Ouvir'}</span>
        </button>

        <button
          type="button"
          onClick={handleGoTo}
          className="flex items-center gap-1 text-sm text-gray-600 hover:text-primary-500 transition-colors"
          aria-label="Ir para momento no vídeo"
        >
          <ExternalLink className="w-4 h-4" aria-hidden="true" />
          <span>Ir para momento</span>
        </button>

        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 text-sm text-gray-600 hover:text-primary-500 transition-colors"
          aria-label={copied ? 'Copiado!' : 'Copiar texto'}
        >
          {copied ? (
            <Check className="w-4 h-4 text-green-500" aria-hidden="true" />
          ) : (
            <Copy className="w-4 h-4" aria-hidden="true" />
          )}
          <span>{copied ? 'Copiado!' : 'Copiar'}</span>
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
  onSelect: PropTypes.func.isRequired,
  onPlaySegment: PropTypes.func.isRequired,
  onGoToMoment: PropTypes.func.isRequired
};

export default TranscriptionCard;
```

---

## Inputs

### Input com Validação

```jsx
import { forwardRef } from 'react';
import PropTypes from 'prop-types';
import { AlertCircle } from 'lucide-react';

const Input = forwardRef(function Input({
  id,
  label,
  type = 'text',
  value,
  onChange,
  placeholder,
  error,
  helpText,
  required = false,
  disabled = false,
  icon: Icon,
  className = ''
}, ref) {
  const inputId = id || `input-${label?.toLowerCase().replace(/\s/g, '-')}`;
  const errorId = `${inputId}-error`;
  const helpId = `${inputId}-help`;

  return (
    <div className={className}>
      {label && (
        <label
          htmlFor={inputId}
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}

      <div className="relative">
        {Icon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Icon
              className={`w-5 h-5 ${error ? 'text-red-400' : 'text-gray-400'}`}
              aria-hidden="true"
            />
          </div>
        )}

        <input
          ref={ref}
          id={inputId}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          aria-invalid={!!error}
          aria-describedby={
            [error && errorId, helpText && helpId].filter(Boolean).join(' ') || undefined
          }
          className={`
            w-full px-4 py-2 border rounded-lg transition-colors
            focus:outline-none focus:ring-2
            disabled:bg-gray-100 disabled:cursor-not-allowed
            ${Icon ? 'pl-10' : ''}
            ${error
              ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
              : 'border-gray-300 focus:ring-primary-500 focus:border-primary-500'
            }
          `}
        />

        {error && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <AlertCircle className="w-5 h-5 text-red-500" aria-hidden="true" />
          </div>
        )}
      </div>

      {error && (
        <p id={errorId} className="mt-1 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {helpText && !error && (
        <p id={helpId} className="mt-1 text-sm text-gray-500">
          {helpText}
        </p>
      )}
    </div>
  );
});

Input.propTypes = {
  id: PropTypes.string,
  label: PropTypes.string,
  type: PropTypes.string,
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  placeholder: PropTypes.string,
  error: PropTypes.string,
  helpText: PropTypes.string,
  required: PropTypes.bool,
  disabled: PropTypes.bool,
  icon: PropTypes.elementType,
  className: PropTypes.string
};

export default Input;
```

### Input de URL do YouTube

```jsx
import { useState, useCallback, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Link2, Check, X, Loader2 } from 'lucide-react';

function YouTubeURLInput({ value, onChange, onValidURL, disabled = false }) {
  const [status, setStatus] = useState('idle'); // idle, validating, valid, invalid
  const [error, setError] = useState('');

  // Regex para URLs do YouTube
  const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]{11}/;

  const extractVideoId = useCallback((url) => {
    const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]{11})/);
    return match ? match[1] : null;
  }, []);

  const validateURL = useCallback(async (url) => {
    if (!url) {
      setStatus('idle');
      setError('');
      return;
    }

    if (!youtubeRegex.test(url)) {
      setStatus('invalid');
      setError('URL inválida. Cole um link válido do YouTube.');
      return;
    }

    setStatus('validating');
    setError('');

    const videoId = extractVideoId(url);

    // Simular validação (em produção, chamar API)
    try {
      // await validateYouTubeVideo(videoId);
      await new Promise(resolve => setTimeout(resolve, 500));

      setStatus('valid');
      onValidURL({ videoId, url });
    } catch (err) {
      setStatus('invalid');
      setError('Não foi possível encontrar este vídeo.');
    }
  }, [extractVideoId, onValidURL]);

  // Debounce da validação
  useEffect(() => {
    const timer = setTimeout(() => {
      validateURL(value);
    }, 500);

    return () => clearTimeout(timer);
  }, [value, validateURL]);

  const getStatusIcon = () => {
    switch (status) {
      case 'validating':
        return <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />;
      case 'valid':
        return <Check className="w-5 h-5 text-green-500" />;
      case 'invalid':
        return <X className="w-5 h-5 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="w-full">
      <label
        htmlFor="youtube-url"
        className="block text-sm font-medium text-gray-700 mb-2"
      >
        Link do YouTube
      </label>

      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Link2 className="w-5 h-5 text-gray-400" aria-hidden="true" />
        </div>

        <input
          id="youtube-url"
          type="url"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Cole o link do YouTube aqui..."
          disabled={disabled}
          aria-invalid={status === 'invalid'}
          aria-describedby={error ? 'youtube-url-error' : undefined}
          className={`
            w-full pl-12 pr-12 py-3 text-lg border-2 rounded-xl
            transition-colors focus:outline-none focus:ring-2
            ${status === 'invalid'
              ? 'border-red-500 focus:ring-red-500'
              : status === 'valid'
                ? 'border-green-500 focus:ring-green-500'
                : 'border-gray-300 focus:ring-primary-500 focus:border-primary-500'
            }
            ${disabled ? 'bg-gray-100 cursor-not-allowed' : ''}
          `}
        />

        <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
          {getStatusIcon()}
        </div>
      </div>

      {error && (
        <p id="youtube-url-error" className="mt-2 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <p className="mt-2 text-sm text-gray-500">
        Formatos aceitos: youtube.com/watch?v=xxx ou youtu.be/xxx
      </p>
    </div>
  );
}

YouTubeURLInput.propTypes = {
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  onValidURL: PropTypes.func.isRequired,
  disabled: PropTypes.bool
};

export default YouTubeURLInput;
```

---

## Dropdowns

### Select/Dropdown

```jsx
import { useState, useCallback, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import { ChevronDown, Check } from 'lucide-react';

function Select({
  id,
  label,
  value,
  onChange,
  options,
  placeholder = 'Selecione...',
  disabled = false,
  error
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const buttonRef = useRef(null);

  const selectedOption = options.find(opt => opt.value === value);

  // Fechar ao clicar fora
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Navegação por teclado
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      buttonRef.current?.focus();
    } else if (e.key === 'ArrowDown' && !isOpen) {
      e.preventDefault();
      setIsOpen(true);
    }
  }, [isOpen]);

  const handleSelect = useCallback((optionValue) => {
    onChange(optionValue);
    setIsOpen(false);
    buttonRef.current?.focus();
  }, [onChange]);

  return (
    <div ref={containerRef} className="relative" onKeyDown={handleKeyDown}>
      {label && (
        <label
          id={`${id}-label`}
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          {label}
        </label>
      )}

      <button
        ref={buttonRef}
        type="button"
        id={id}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-labelledby={label ? `${id}-label` : undefined}
        className={`
          w-full flex items-center justify-between px-4 py-2
          bg-white border rounded-lg text-left
          transition-colors focus:outline-none focus:ring-2
          ${error
            ? 'border-red-500 focus:ring-red-500'
            : 'border-gray-300 focus:ring-primary-500 focus:border-primary-500'
          }
          ${disabled ? 'bg-gray-100 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        <span className={selectedOption ? 'text-gray-900' : 'text-gray-500'}>
          {selectedOption?.label || placeholder}
        </span>
        <ChevronDown
          className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <ul
          role="listbox"
          aria-labelledby={label ? `${id}-label` : undefined}
          className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto"
        >
          {options.map((option) => (
            <li
              key={option.value}
              role="option"
              aria-selected={option.value === value}
              onClick={() => handleSelect(option.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleSelect(option.value);
                }
              }}
              tabIndex={0}
              className={`
                flex items-center justify-between px-4 py-2 cursor-pointer
                ${option.value === value
                  ? 'bg-primary-50 text-primary-700'
                  : 'hover:bg-gray-50'
                }
              `}
            >
              <div>
                <span className="block font-medium">{option.label}</span>
                {option.description && (
                  <span className="block text-sm text-gray-500">{option.description}</span>
                )}
              </div>
              {option.value === value && (
                <Check className="w-5 h-5 text-primary-500" aria-hidden="true" />
              )}
            </li>
          ))}
        </ul>
      )}

      {error && (
        <p className="mt-1 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

Select.propTypes = {
  id: PropTypes.string.isRequired,
  label: PropTypes.string,
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      value: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      description: PropTypes.string
    })
  ).isRequired,
  placeholder: PropTypes.string,
  disabled: PropTypes.bool,
  error: PropTypes.string
};

export default Select;
```

---

## Botões

### Button Component

```jsx
import { forwardRef } from 'react';
import PropTypes from 'prop-types';
import { Loader2 } from 'lucide-react';

const Button = forwardRef(function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconPosition = 'left',
  isLoading = false,
  disabled = false,
  fullWidth = false,
  type = 'button',
  onClick,
  className = '',
  ...props
}, ref) {
  const baseStyles = `
    inline-flex items-center justify-center font-medium rounded-lg
    transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2
    disabled:opacity-50 disabled:cursor-not-allowed
  `;

  const variants = {
    primary: 'bg-primary-500 hover:bg-primary-600 text-white focus:ring-primary-500',
    secondary: 'bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 focus:ring-gray-500',
    ghost: 'hover:bg-gray-100 text-gray-700 focus:ring-gray-500',
    danger: 'bg-red-500 hover:bg-red-600 text-white focus:ring-red-500',
    success: 'bg-green-500 hover:bg-green-600 text-white focus:ring-green-500'
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm gap-1.5',
    md: 'px-4 py-2 text-sm gap-2',
    lg: 'px-6 py-3 text-base gap-2'
  };

  const iconSizes = {
    sm: 'w-4 h-4',
    md: 'w-4 h-4',
    lg: 'w-5 h-5'
  };

  return (
    <button
      ref={ref}
      type={type}
      onClick={onClick}
      disabled={disabled || isLoading}
      className={`
        ${baseStyles}
        ${variants[variant]}
        ${sizes[size]}
        ${fullWidth ? 'w-full' : ''}
        ${className}
      `}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className={`${iconSizes[size]} animate-spin`} aria-hidden="true" />
          <span>Carregando...</span>
        </>
      ) : (
        <>
          {Icon && iconPosition === 'left' && (
            <Icon className={iconSizes[size]} aria-hidden="true" />
          )}
          {children}
          {Icon && iconPosition === 'right' && (
            <Icon className={iconSizes[size]} aria-hidden="true" />
          )}
        </>
      )}
    </button>
  );
});

Button.propTypes = {
  children: PropTypes.node.isRequired,
  variant: PropTypes.oneOf(['primary', 'secondary', 'ghost', 'danger', 'success']),
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  icon: PropTypes.elementType,
  iconPosition: PropTypes.oneOf(['left', 'right']),
  isLoading: PropTypes.bool,
  disabled: PropTypes.bool,
  fullWidth: PropTypes.bool,
  type: PropTypes.oneOf(['button', 'submit', 'reset']),
  onClick: PropTypes.func,
  className: PropTypes.string
};

export default Button;
```

---

## Progress/Loading

### Progress Bar

```jsx
import PropTypes from 'prop-types';

function ProgressBar({ value, max = 100, label, showPercentage = true }) {
  const percentage = Math.round((value / max) * 100);

  return (
    <div className="w-full">
      {(label || showPercentage) && (
        <div className="flex items-center justify-between mb-2">
          {label && (
            <span className="text-sm font-medium text-gray-700">{label}</span>
          )}
          {showPercentage && (
            <span className="text-sm text-gray-500">{percentage}%</span>
          )}
        </div>
      )}

      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label || `Progresso: ${percentage}%`}
        className="w-full h-2 bg-gray-200 rounded-full overflow-hidden"
      >
        <div
          className="h-full bg-primary-500 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

ProgressBar.propTypes = {
  value: PropTypes.number.isRequired,
  max: PropTypes.number,
  label: PropTypes.string,
  showPercentage: PropTypes.bool
};

export default ProgressBar;
```

### Loading Overlay

```jsx
import PropTypes from 'prop-types';
import { Loader2 } from 'lucide-react';
import ProgressBar from './ProgressBar';

function LoadingOverlay({
  isVisible,
  title,
  message,
  progress,
  onCancel
}) {
  if (!isVisible) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="loading-title"
    >
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 text-center">
        {/* Animação */}
        <div className="mb-6">
          <Loader2 className="w-16 h-16 text-primary-500 animate-spin mx-auto" />
        </div>

        {/* Título */}
        {title && (
          <h2 id="loading-title" className="text-xl font-semibold text-gray-900 mb-2">
            {title}
          </h2>
        )}

        {/* Mensagem (pode mudar) */}
        {message && (
          <p className="text-gray-600 mb-6" aria-live="polite">
            {message}
          </p>
        )}

        {/* Barra de progresso */}
        {progress !== undefined && (
          <div className="mb-6">
            <ProgressBar value={progress} />
          </div>
        )}

        {/* Botão cancelar */}
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="text-gray-500 hover:text-gray-700 text-sm font-medium"
          >
            Cancelar
          </button>
        )}
      </div>
    </div>
  );
}

LoadingOverlay.propTypes = {
  isVisible: PropTypes.bool.isRequired,
  title: PropTypes.string,
  message: PropTypes.string,
  progress: PropTypes.number,
  onCancel: PropTypes.func
};

export default LoadingOverlay;
```

---

## Layouts

### Two Column Layout

```jsx
import PropTypes from 'prop-types';

function TwoColumnLayout({
  leftContent,
  rightContent,
  leftWidth = '60%',
  rightWidth = '40%',
  gap = 6
}) {
  return (
    <div className={`flex flex-col lg:flex-row gap-${gap}`}>
      <div
        className="w-full lg:flex-none"
        style={{ '--lg-width': leftWidth }}
        // Em Tailwind, usar classe customizada ou style
      >
        <div className="lg:w-[var(--lg-width)]">
          {leftContent}
        </div>
      </div>

      <div className="w-full lg:flex-1">
        {rightContent}
      </div>
    </div>
  );
}

// Versão mais simples com classes fixas
function TwoColumnLayout60_40({ leftContent, rightContent }) {
  return (
    <div className="flex flex-col lg:flex-row gap-6">
      <div className="w-full lg:w-3/5">
        {leftContent}
      </div>
      <div className="w-full lg:w-2/5">
        {rightContent}
      </div>
    </div>
  );
}

TwoColumnLayout.propTypes = {
  leftContent: PropTypes.node.isRequired,
  rightContent: PropTypes.node.isRequired,
  leftWidth: PropTypes.string,
  rightWidth: PropTypes.string,
  gap: PropTypes.number
};

export default TwoColumnLayout;
```

### Step Indicator

```jsx
import PropTypes from 'prop-types';
import { Check } from 'lucide-react';

function StepIndicator({ steps, currentStep }) {
  return (
    <nav aria-label="Progresso">
      <ol className="flex items-center">
        {steps.map((step, index) => {
          const stepNumber = index + 1;
          const isCompleted = stepNumber < currentStep;
          const isCurrent = stepNumber === currentStep;

          return (
            <li
              key={step.id}
              className={`flex items-center ${index < steps.length - 1 ? 'flex-1' : ''}`}
            >
              {/* Círculo do step */}
              <div
                className={`
                  flex items-center justify-center w-10 h-10 rounded-full
                  font-semibold text-sm transition-colors
                  ${isCompleted
                    ? 'bg-green-500 text-white'
                    : isCurrent
                      ? 'bg-primary-500 text-white'
                      : 'bg-gray-200 text-gray-500'
                  }
                `}
                aria-current={isCurrent ? 'step' : undefined}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5" aria-hidden="true" />
                ) : (
                  stepNumber
                )}
              </div>

              {/* Label do step */}
              <span
                className={`
                  ml-3 text-sm font-medium
                  ${isCurrent ? 'text-primary-600' : 'text-gray-500'}
                  hidden sm:inline
                `}
              >
                {step.label}
              </span>

              {/* Linha conectora */}
              {index < steps.length - 1 && (
                <div
                  className={`
                    flex-1 h-0.5 mx-4
                    ${isCompleted ? 'bg-green-500' : 'bg-gray-200'}
                  `}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

StepIndicator.propTypes = {
  steps: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired
    })
  ).isRequired,
  currentStep: PropTypes.number.isRequired
};

export default StepIndicator;
```

---

## Hooks Customizados

### useMultiSelect

```jsx
import { useState, useCallback, useMemo } from 'react';

/**
 * Hook para gerenciar seleção múltipla de itens
 * @param {Array} initialSelection - IDs inicialmente selecionados
 * @returns {Object} Estado e funções de seleção
 */
function useMultiSelect(initialSelection = []) {
  const [selectedIds, setSelectedIds] = useState(new Set(initialSelection));

  const toggle = useCallback((id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const select = useCallback((id) => {
    setSelectedIds(prev => new Set([...prev, id]));
  }, []);

  const deselect = useCallback((id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const selectAll = useCallback((ids) => {
    setSelectedIds(new Set(ids));
  }, []);

  const deselectAll = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const isSelected = useCallback((id) => {
    return selectedIds.has(id);
  }, [selectedIds]);

  const selectedArray = useMemo(() => {
    return Array.from(selectedIds);
  }, [selectedIds]);

  return {
    selectedIds: selectedArray,
    selectedCount: selectedIds.size,
    toggle,
    select,
    deselect,
    selectAll,
    deselectAll,
    isSelected,
    hasSelection: selectedIds.size > 0
  };
}

export default useMultiSelect;
```

### useSteps

```jsx
import { useState, useCallback, useMemo } from 'react';

/**
 * Hook para gerenciar fluxo de steps/wizard
 * @param {number} totalSteps - Número total de etapas
 * @param {number} initialStep - Etapa inicial (default: 1)
 * @returns {Object} Estado e funções de navegação
 */
function useSteps(totalSteps, initialStep = 1) {
  const [currentStep, setCurrentStep] = useState(initialStep);

  const goToStep = useCallback((step) => {
    if (step >= 1 && step <= totalSteps) {
      setCurrentStep(step);
    }
  }, [totalSteps]);

  const nextStep = useCallback(() => {
    setCurrentStep(prev => Math.min(prev + 1, totalSteps));
  }, [totalSteps]);

  const prevStep = useCallback(() => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  }, []);

  const reset = useCallback(() => {
    setCurrentStep(initialStep);
  }, [initialStep]);

  const progress = useMemo(() => {
    return Math.round((currentStep / totalSteps) * 100);
  }, [currentStep, totalSteps]);

  return {
    currentStep,
    totalSteps,
    progress,
    isFirstStep: currentStep === 1,
    isLastStep: currentStep === totalSteps,
    goToStep,
    nextStep,
    prevStep,
    reset
  };
}

export default useSteps;
```

### useAsync

```jsx
import { useState, useCallback } from 'react';

/**
 * Hook para gerenciar operações assíncronas
 * @param {Function} asyncFunction - Função assíncrona a ser executada
 * @returns {Object} Estado e função de execução
 */
function useAsync(asyncFunction) {
  const [state, setState] = useState({
    data: null,
    error: null,
    status: 'idle' // idle, pending, success, error
  });

  const execute = useCallback(async (...args) => {
    setState({ data: null, error: null, status: 'pending' });

    try {
      const data = await asyncFunction(...args);
      setState({ data, error: null, status: 'success' });
      return data;
    } catch (error) {
      setState({ data: null, error, status: 'error' });
      throw error;
    }
  }, [asyncFunction]);

  const reset = useCallback(() => {
    setState({ data: null, error: null, status: 'idle' });
  }, []);

  return {
    ...state,
    isIdle: state.status === 'idle',
    isPending: state.status === 'pending',
    isSuccess: state.status === 'success',
    isError: state.status === 'error',
    execute,
    reset
  };
}

export default useAsync;
```

---

## Exemplo Completo: Página de Transcrição

```jsx
// src/pages/transcricao/TranscricaoPage.jsx
import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocumentTitle } from '../../hooks';
import { ArrowLeft } from 'lucide-react';

import Header from '../../components/layout/Header';
import Breadcrumb from '../../components/ui/Breadcrumb';
import StepIndicator from './components/StepIndicator';
import YouTubeURLInput from './components/YouTubeURLInput';
import VideoPreview from './components/VideoPreview';
import LoadingOverlay from './components/LoadingOverlay';
import TranscriptionList from './components/TranscriptionList';
import ConfigPanel from './components/ConfigPanel';
import Button from '../../components/ui/Button';

import useSteps from './hooks/useSteps';
import useMultiSelect from './hooks/useMultiSelect';
import useAsync from './hooks/useAsync';

const STEPS = [
  { id: 'input', label: 'Adicionar Vídeo' },
  { id: 'transcribing', label: 'Transcrevendo' },
  { id: 'select', label: 'Selecionar Trechos' }
];

function TranscricaoPage() {
  useDocumentTitle('Transcrever Vídeo - TMC Redação');
  const navigate = useNavigate();

  // State
  const [url, setUrl] = useState('');
  const [videoData, setVideoData] = useState(null);
  const [transcription, setTranscription] = useState([]);
  const [config, setConfig] = useState({
    tone: 'journalistic',
    persona: 'impartial_journalist',
    type: 'reportagem'
  });

  // Hooks customizados
  const { currentStep, nextStep, prevStep, goToStep } = useSteps(3);
  const selection = useMultiSelect();
  const transcribeAsync = useAsync(transcribeVideo);
  const generateAsync = useAsync(generateArticle);

  // Handlers
  const handleValidURL = useCallback((data) => {
    setVideoData(data);
  }, []);

  const handleStartTranscription = useCallback(async () => {
    nextStep(); // Vai para loading
    try {
      const result = await transcribeAsync.execute(videoData.videoId);
      setTranscription(result.segments);
      nextStep(); // Vai para seleção
    } catch (error) {
      goToStep(1); // Volta para input em caso de erro
    }
  }, [videoData, transcribeAsync, nextStep, goToStep]);

  const handleGenerate = useCallback(async () => {
    const selectedSegments = transcription.filter(
      seg => selection.isSelected(seg.id)
    );

    const article = await generateAsync.execute({
      segments: selectedSegments,
      config,
      source: videoData
    });

    // Redireciona para editor com a matéria
    navigate(`/editor/${article.id}`);
  }, [transcription, selection, config, videoData, generateAsync, navigate]);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main id="main-content" className="max-w-7xl mx-auto px-4 py-6" role="main">
        {/* Breadcrumb */}
        <Breadcrumb
          items={[
            { label: 'Redação', href: '/' },
            { label: 'Transcrever Vídeo' }
          ]}
        />

        {/* Header da página */}
        <div className="flex items-center justify-between mt-6 mb-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-100 rounded-lg"
              aria-label="Voltar para Redação"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-2xl font-bold text-gray-900">
              Transcrever Vídeo
            </h1>
          </div>

          <StepIndicator steps={STEPS} currentStep={currentStep} />
        </div>

        {/* Step 1: Input */}
        {currentStep === 1 && (
          <div className="max-w-2xl mx-auto py-12">
            <div className="text-center mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Cole o link do YouTube
              </h2>
              <p className="text-gray-600">
                Transcreva vídeos do YouTube para criar matérias automaticamente
              </p>
            </div>

            <YouTubeURLInput
              value={url}
              onChange={setUrl}
              onValidURL={handleValidURL}
            />

            {videoData && (
              <div className="mt-6">
                <VideoPreview video={videoData} />
              </div>
            )}

            <div className="mt-8 flex justify-center">
              <Button
                variant="primary"
                size="lg"
                disabled={!videoData}
                onClick={handleStartTranscription}
              >
                Transcrever Vídeo
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: Loading */}
        <LoadingOverlay
          isVisible={currentStep === 2}
          title="Transcrevendo vídeo"
          message={transcribeAsync.status === 'pending' ? 'Convertendo áudio para texto...' : ''}
          progress={50}
          onCancel={() => goToStep(1)}
        />

        {/* Step 3: Seleção */}
        {currentStep === 3 && (
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Coluna esquerda: Lista de trechos */}
            <div className="w-full lg:w-3/5">
              <TranscriptionList
                segments={transcription}
                selection={selection}
                videoId={videoData?.videoId}
              />
            </div>

            {/* Coluna direita: Configurações */}
            <div className="w-full lg:w-2/5">
              <ConfigPanel
                config={config}
                onChange={setConfig}
                selection={selection}
                onGenerate={handleGenerate}
                isGenerating={generateAsync.isPending}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// Funções de API (mock)
async function transcribeVideo(videoId) {
  // Simulação - substituir por chamada real
  await new Promise(resolve => setTimeout(resolve, 2000));
  return {
    segments: [
      { id: '1', startTime: '00:00', endTime: '00:45', text: 'Introdução...' },
      { id: '2', startTime: '00:45', endTime: '02:12', text: 'Desenvolvimento...' }
    ]
  };
}

async function generateArticle({ segments, config, source }) {
  // Simulação - substituir por chamada real
  await new Promise(resolve => setTimeout(resolve, 1500));
  return { id: 'new-article-123' };
}

export default TranscricaoPage;
```
