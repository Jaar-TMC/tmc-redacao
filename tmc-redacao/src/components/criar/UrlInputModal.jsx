import { useState } from 'react';
import PropTypes from 'prop-types';
import { X, Copy, Loader } from 'lucide-react';

/**
 * UrlInputModal - Modal para input de URL (YouTube ou Link da Web)
 *
 * Funcionalidades:
 * - Input de URL com botão de colar
 * - Validação de URL
 * - Preview após validação (YouTube ou página web)
 * - Loading state durante processamento
 */
const UrlInputModal = ({
  isOpen,
  onClose,
  type = 'youtube', // 'youtube' | 'web'
  onSubmit
}) => {
  const [url, setUrl] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);

  const modalTitle = type === 'youtube'
    ? 'Transcrever Vídeo do YouTube'
    : 'Extrair Conteúdo da Web';

  const placeholder = type === 'youtube'
    ? 'https://youtube.com/watch?v=...'
    : 'https://exemplo.com/noticia/...';

  const helperText = type === 'youtube'
    ? 'Suporta vídeos de até 2 horas de duração'
    : 'Funciona com a maioria dos sites de notícias';

  const submitButtonText = type === 'youtube'
    ? 'Transcrever'
    : 'Extrair Conteúdo';

  // Simular validação de URL (deve ser substituído por API real)
  const handleValidateUrl = async () => {
    setError(null);
    setIsValidating(true);

    try {
      // Validação básica de URL
      const urlPattern = /^https?:\/\/.+/i;
      if (!urlPattern.test(url)) {
        throw new Error('URL inválida. Certifique-se de incluir http:// ou https://');
      }

      // Validação específica para YouTube
      if (type === 'youtube') {
        const youtubePattern = /(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]+)/;
        const match = url.match(youtubePattern);

        if (!match) {
          throw new Error('URL do YouTube inválida. Use o formato: https://youtube.com/watch?v=...');
        }

        // Simular preview (em produção, buscar via API)
        setTimeout(() => {
          setPreview({
            type: 'youtube',
            videoId: match[1],
            title: 'Título do Vídeo',
            channel: 'Canal do Autor',
            duration: '15:32',
            thumbnail: `https://img.youtube.com/vi/${match[1]}/mqdefault.jpg`
          });
          setIsValidating(false);
        }, 1000);
      } else {
        // Simular preview de página web
        setTimeout(() => {
          setPreview({
            type: 'web',
            title: 'Título da Página',
            domain: new URL(url).hostname,
            detected: 'Artigo de notícias'
          });
          setIsValidating(false);
        }, 1000);
      }
    } catch (err) {
      setError(err.message);
      setIsValidating(false);
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setUrl(text);
    } catch (err) {
      console.error('Erro ao colar:', err);
    }
  };

  const handleSubmit = () => {
    if (preview && onSubmit) {
      onSubmit({ url, preview });
      handleClose();
    }
  };

  const handleClose = () => {
    setUrl('');
    setPreview(null);
    setError(null);
    setIsValidating(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={handleClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-light-gray">
          <h2 id="modal-title" className="text-xl font-bold text-dark-gray">
            {modalTitle}
          </h2>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-off-white rounded-lg transition-colors"
            aria-label="Fechar modal"
          >
            <X size={20} className="text-medium-gray" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* URL Input */}
          <div className="mb-4">
            <label htmlFor="url-input" className="block text-sm font-medium text-dark-gray mb-2">
              Cole a URL {type === 'youtube' ? 'do vídeo' : 'da página'}
            </label>
            <div className="flex gap-2">
              <input
                id="url-input"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isValidating && handleValidateUrl()}
                placeholder={placeholder}
                className="flex-1 px-4 py-3 border border-light-gray rounded-lg text-dark-gray placeholder:text-medium-gray focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                aria-describedby="helper-text"
              />
              <button
                onClick={handlePaste}
                className="p-3 border border-light-gray rounded-lg hover:bg-off-white transition-colors"
                aria-label="Colar URL"
                title="Colar"
              >
                <Copy size={20} className="text-medium-gray" />
              </button>
            </div>
            <p id="helper-text" className="text-sm text-medium-gray mt-2">
              {helperText}
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Validação Button */}
          {!preview && (
            <button
              onClick={handleValidateUrl}
              disabled={!url || isValidating}
              className="w-full mb-4 px-4 py-3 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center justify-center gap-2"
            >
              {isValidating ? (
                <>
                  <Loader size={18} className="animate-spin" />
                  Validando...
                </>
              ) : (
                'Validar URL'
              )}
            </button>
          )}

          {/* Preview */}
          {preview && (
            <div className="mb-4 p-4 bg-off-white rounded-lg border border-light-gray">
              {type === 'youtube' ? (
                <div className="flex gap-4">
                  <img
                    src={preview.thumbnail}
                    alt=""
                    className="w-40 h-24 object-cover rounded"
                  />
                  <div className="flex-1">
                    <h3 className="font-semibold text-dark-gray mb-1">
                      {preview.title}
                    </h3>
                    <p className="text-sm text-medium-gray mb-1">
                      {preview.channel}
                    </p>
                    <p className="text-sm text-medium-gray">
                      Duração: {preview.duration}
                    </p>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex items-start gap-2 mb-2">
                    <span className="text-2xl">🌐</span>
                    <div>
                      <h3 className="font-semibold text-dark-gray">
                        {preview.title}
                      </h3>
                      <p className="text-sm text-medium-gray">
                        {preview.domain}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-green-600 flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor">
                      <path d="M5 13l4 4L19 7" />
                    </svg>
                    Detectado: {preview.detected}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-light-gray">
          <button
            onClick={handleClose}
            className="px-6 py-3 border border-light-gray text-medium-gray rounded-lg hover:bg-off-white transition-colors font-medium"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={!preview}
            className="px-6 py-3 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center gap-2"
          >
            {submitButtonText}
            <svg className="w-5 h-5" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor">
              <path d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

UrlInputModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  type: PropTypes.oneOf(['youtube', 'web']),
  onSubmit: PropTypes.func.isRequired,
};

export default UrlInputModal;
