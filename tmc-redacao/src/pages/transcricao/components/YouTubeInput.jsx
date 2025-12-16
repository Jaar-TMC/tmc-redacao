import { useState, useCallback, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Link2, Check, X, Loader2 } from 'lucide-react';

/**
 * YouTubeInput - Input para URL do YouTube com validação
 * @param {Object} props
 * @param {string} props.value - Valor atual do input
 * @param {Function} props.onChange - Callback ao mudar valor
 * @param {Function} props.onValidURL - Callback quando URL é válida
 * @param {boolean} [props.disabled] - Se o input está desabilitado
 */
function YouTubeInput({ value, onChange, onValidURL, disabled = false }) {
  const [status, setStatus] = useState('idle'); // idle, validating, valid, invalid
  const [error, setError] = useState('');

  // Regex para URLs do YouTube
  const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([\w-]{11})/;

  const extractVideoId = useCallback((url) => {
    const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]{11})/);
    return match ? match[1] : null;
  }, []);

  const validateURL = useCallback(async (url) => {
    if (!url || url.trim() === '') {
      setStatus('idle');
      setError('');
      onValidURL(null);
      return;
    }

    if (!youtubeRegex.test(url)) {
      setStatus('invalid');
      setError('URL inválida. Cole um link válido do YouTube.');
      onValidURL(null);
      return;
    }

    setStatus('validating');
    setError('');

    const videoId = extractVideoId(url);

    // Simular validação (em produção, chamar API do YouTube)
    try {
      await new Promise(resolve => setTimeout(resolve, 800));

      // Mock de dados do vídeo
      const mockVideoData = {
        videoId,
        url,
        title: 'Exemplo de Vídeo do YouTube',
        channel: 'Canal de Exemplo',
        thumbnail: `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
        duration: '15:32',
        views: '1.2M',
        publishedAt: 'há 3 dias'
      };

      setStatus('valid');
      onValidURL(mockVideoData);
    } catch (err) {
      setStatus('invalid');
      setError('Não foi possível encontrar este vídeo.');
      onValidURL(null);
    }
  }, [extractVideoId, onValidURL, youtubeRegex]);

  // Debounce da validação
  useEffect(() => {
    const timer = setTimeout(() => {
      validateURL(value);
    }, 600);

    return () => clearTimeout(timer);
  }, [value, validateURL]);

  const getStatusIcon = () => {
    switch (status) {
      case 'validating':
        return <Loader2 className="w-5 h-5 text-medium-gray animate-spin" aria-hidden="true" />;
      case 'valid':
        return <Check className="w-5 h-5 text-success" aria-hidden="true" />;
      case 'invalid':
        return <X className="w-5 h-5 text-error" aria-hidden="true" />;
      default:
        return null;
    }
  };

  const getInputClasses = () => {
    const baseClasses = 'w-full pl-12 pr-12 py-4 text-lg border-2 rounded-xl transition-all focus:outline-none focus:ring-2 focus:ring-offset-2';

    if (disabled) {
      return `${baseClasses} bg-light-gray cursor-not-allowed border-light-gray`;
    }

    switch (status) {
      case 'invalid':
        return `${baseClasses} border-error focus:ring-error focus:border-error`;
      case 'valid':
        return `${baseClasses} border-success focus:ring-success focus:border-success`;
      default:
        return `${baseClasses} border-light-gray focus:ring-tmc-orange focus:border-tmc-orange`;
    }
  };

  return (
    <div className="w-full">
      <label
        htmlFor="youtube-url"
        className="block text-sm font-medium text-dark-gray mb-2"
      >
        Link do YouTube
      </label>

      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Link2 className="w-5 h-5 text-medium-gray" aria-hidden="true" />
        </div>

        <input
          id="youtube-url"
          type="url"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Cole o link do YouTube aqui..."
          disabled={disabled}
          aria-invalid={status === 'invalid'}
          aria-describedby={error ? 'youtube-url-error' : 'youtube-url-help'}
          className={getInputClasses()}
        />

        <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
          {getStatusIcon()}
        </div>
      </div>

      {error && (
        <p
          id="youtube-url-error"
          className="mt-2 text-sm text-error flex items-center gap-1"
          role="alert"
        >
          <X className="w-4 h-4" aria-hidden="true" />
          {error}
        </p>
      )}

      <p id="youtube-url-help" className="mt-2 text-sm text-medium-gray">
        Formatos aceitos: youtube.com/watch?v=xxx ou youtu.be/xxx
      </p>
    </div>
  );
}

YouTubeInput.propTypes = {
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  onValidURL: PropTypes.func.isRequired,
  disabled: PropTypes.bool
};

export default YouTubeInput;
