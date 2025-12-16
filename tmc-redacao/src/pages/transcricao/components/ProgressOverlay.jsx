import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Loader2 } from 'lucide-react';

/**
 * ProgressOverlay - Overlay de loading com progresso
 * @param {Object} props
 * @param {boolean} props.isVisible - Se está visível
 * @param {string} props.title - Título do loading
 * @param {Object} props.video - Dados do vídeo (para thumbnail)
 * @param {number} [props.progress] - Progresso (0-100)
 * @param {Function} [props.onCancel] - Callback ao cancelar
 */
function ProgressOverlay({
  isVisible,
  title,
  video,
  progress = 0,
  onCancel
}) {
  const [currentMessage, setCurrentMessage] = useState(0);

  const messages = [
    'Extraindo áudio do vídeo...',
    'Processando faixas de áudio...',
    'Convertendo áudio para texto...',
    'Identificando speakers...',
    'Formatando transcrição...'
  ];

  // Rotacionar mensagens baseado no progresso com intervalos especificados
  useEffect(() => {
    if (!isVisible) return;

    let messageIndex = 0;
    if (progress >= 90) messageIndex = 4;      // 90-100%: Formatando
    else if (progress >= 70) messageIndex = 3; // 70-90%: Identificando speakers
    else if (progress >= 40) messageIndex = 2; // 40-70%: Convertendo
    else if (progress >= 20) messageIndex = 1; // 20-40%: Processando
    else messageIndex = 0;                     // 0-20%: Extraindo

    setCurrentMessage(messageIndex);
  }, [progress, isVisible]);

  // Estimar tempo restante
  const estimatedSeconds = Math.max(0, Math.ceil((100 - progress) / 2));

  if (!isVisible) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="progress-title"
      aria-describedby="progress-description"
    >
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 text-center">
        {/* Thumbnail do vídeo com overlay */}
        {video && (
          <div className="relative w-48 h-28 mx-auto mb-6 rounded-lg overflow-hidden">
            <img
              src={video.thumbnail}
              alt=""
              className="w-full h-full object-cover"
              aria-hidden="true"
            />
            <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
              {/* Animação de ondas de áudio */}
              <div className="flex items-end gap-1 h-8">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="w-1 bg-white rounded-full animate-pulse"
                    style={{
                      height: `${Math.random() * 100}%`,
                      animationDelay: `${i * 0.1}s`,
                      animationDuration: '0.5s'
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Ícone de loading se não tiver vídeo */}
        {!video && (
          <div className="mb-6">
            <Loader2 className="w-16 h-16 text-tmc-orange animate-spin mx-auto" />
          </div>
        )}

        {/* Título */}
        <h2
          id="progress-title"
          className="text-xl font-bold text-dark-gray mb-2"
        >
          {title}
        </h2>

        {/* Título do vídeo */}
        {video && (
          <p className="text-sm text-medium-gray mb-4 line-clamp-1">
            {video.title}
          </p>
        )}

        {/* Barra de progresso */}
        <div className="mb-4">
          <div
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Progresso: ${progress}%`}
            className="w-full h-2 bg-light-gray rounded overflow-hidden"
          >
            <div
              className="h-full bg-[#2563EB] rounded transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between mt-1 text-xs text-medium-gray">
            <span>{progress}%</span>
            <span>~{estimatedSeconds}s restantes</span>
          </div>
        </div>

        {/* Mensagem rotativa */}
        <p
          id="progress-description"
          className="text-sm text-medium-gray mb-6"
          aria-live="polite"
        >
          {messages[currentMessage]}
        </p>

        {/* Botão cancelar */}
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="text-medium-gray hover:text-dark-gray text-sm font-medium transition-colors"
          >
            Cancelar
          </button>
        )}
      </div>
    </div>
  );
}

ProgressOverlay.propTypes = {
  isVisible: PropTypes.bool.isRequired,
  title: PropTypes.string.isRequired,
  video: PropTypes.shape({
    thumbnail: PropTypes.string,
    title: PropTypes.string
  }),
  progress: PropTypes.number,
  onCancel: PropTypes.func
};

export default ProgressOverlay;
