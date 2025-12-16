import { useState, useEffect, useRef, useCallback } from 'react';
import PropTypes from 'prop-types';
import { X, Maximize2, Minimize2, Play, Pause } from 'lucide-react';

/**
 * MiniPlayer - Player de vídeo fixo que aparece quando o player principal sai de vista
 * @param {Object} props
 * @param {string} props.videoId - ID do vídeo do YouTube
 * @param {boolean} props.isMainPlayerVisible - Se o player principal está visível
 * @param {number} [props.currentTime] - Tempo atual do vídeo (segundos)
 * @param {function} [props.onTimeUpdate] - Callback quando o tempo é atualizado
 * @param {string} [props.position='bottom-right'] - Posição do mini player
 */
function MiniPlayer({
  videoId,
  isMainPlayerVisible,
  currentTime = 0,
  onTimeUpdate,
  position = 'bottom-right'
}) {
  // Estados
  const [isVisible, setIsVisible] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isClosed, setIsClosed] = useState(false);

  // Refs
  const playerRef = useRef(null);
  const containerRef = useRef(null);
  const youtubePlayerRef = useRef(null);

  // Controlar visibilidade baseado no player principal
  useEffect(() => {
    // Só mostra se o player principal não estiver visível E não tiver sido fechado manualmente
    if (!isMainPlayerVisible && !isClosed) {
      // Pequeno delay para animação suave
      const timer = setTimeout(() => setIsVisible(true), 100);
      return () => clearTimeout(timer);
    } else {
      setIsVisible(false);
    }
  }, [isMainPlayerVisible, isClosed]);

  // Reset do estado "closed" quando o player principal volta a ficar visível
  useEffect(() => {
    if (isMainPlayerVisible) {
      setIsClosed(false);
    }
  }, [isMainPlayerVisible]);

  // Inicializar YouTube Player API
  useEffect(() => {
    if (!isVisible || !videoId) return;

    // Verificar se a API do YouTube já está carregada
    if (!window.YT) {
      // Carregar script da API do YouTube
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      const firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

      // Callback quando a API estiver pronta
      window.onYouTubeIframeAPIReady = () => {
        initializePlayer();
      };
    } else {
      initializePlayer();
    }

    function initializePlayer() {
      if (!playerRef.current) return;

      youtubePlayerRef.current = new window.YT.Player(playerRef.current, {
        videoId: videoId,
        playerVars: {
          autoplay: 0,
          controls: 1,
          modestbranding: 1,
          rel: 0,
          start: Math.floor(currentTime)
        },
        events: {
          onReady: onPlayerReady,
          onStateChange: onPlayerStateChange
        }
      });
    }

    function onPlayerReady() {
      // Player pronto
      if (currentTime > 0 && youtubePlayerRef.current) {
        youtubePlayerRef.current.seekTo(currentTime, true);
      }
    }

    function onPlayerStateChange(event) {
      // Atualizar estado de playing
      setIsPlaying(event.data === window.YT.PlayerState.PLAYING);

      // Callback de time update
      if (event.data === window.YT.PlayerState.PLAYING && onTimeUpdate) {
        const interval = setInterval(() => {
          if (youtubePlayerRef.current && youtubePlayerRef.current.getCurrentTime) {
            const time = youtubePlayerRef.current.getCurrentTime();
            onTimeUpdate(time);
          }
        }, 1000);

        return () => clearInterval(interval);
      }
    }

    return () => {
      if (youtubePlayerRef.current && youtubePlayerRef.current.destroy) {
        youtubePlayerRef.current.destroy();
        youtubePlayerRef.current = null;
      }
    };
  }, [isVisible, videoId, currentTime, onTimeUpdate]);

  // Toggle play/pause
  const togglePlayPause = useCallback(() => {
    if (!youtubePlayerRef.current) return;

    if (isPlaying) {
      youtubePlayerRef.current.pauseVideo();
    } else {
      youtubePlayerRef.current.playVideo();
    }
  }, [isPlaying]);

  // Toggle expand/minimize
  const toggleExpand = useCallback(() => {
    setIsExpanded(prev => !prev);
  }, []);

  // Fechar mini player
  const handleClose = useCallback(() => {
    setIsClosed(true);
    setIsVisible(false);
    if (youtubePlayerRef.current && youtubePlayerRef.current.pauseVideo) {
      youtubePlayerRef.current.pauseVideo();
    }
  }, []);

  // Atalhos de teclado
  useEffect(() => {
    if (!isVisible) return;

    const handleKeyDown = (e) => {
      // Ignorar se estiver em input/textarea
      if (e.target.matches('input, textarea, select')) return;

      // Espaço - Play/Pause
      if (e.code === 'Space' && e.target === document.body) {
        e.preventDefault();
        togglePlayPause();
      }

      // Esc - Minimizar se expandido
      if (e.key === 'Escape' && isExpanded) {
        setIsExpanded(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isVisible, isExpanded, togglePlayPause]);

  // Não renderizar se não estiver visível
  if (!isVisible) return null;

  // Classes de posição
  const positionClasses = {
    'bottom-right': 'bottom-6 right-6',
    'bottom-left': 'bottom-6 left-6',
    'top-right': 'top-24 right-6',
    'top-left': 'top-24 left-6'
  };

  // Tamanhos
  const sizeClasses = isExpanded
    ? 'w-[90vw] max-w-2xl h-auto'
    : 'w-80 h-auto';

  return (
    <div
      ref={containerRef}
      className={`
        fixed ${positionClasses[position]} z-50
        ${sizeClasses}
        bg-white rounded-xl shadow-2xl border-2 border-light-gray
        transform transition-all duration-300 ease-out
        ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'}
      `}
      role="complementary"
      aria-label="Mini player de vídeo"
    >
      {/* Header com controles */}
      <div className="flex items-center justify-between px-3 py-2 bg-dark-green text-white rounded-t-xl">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Play className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
          <span className="text-sm font-medium truncate">
            Vídeo em reprodução
          </span>
        </div>

        <div className="flex items-center gap-1">
          {/* Botão Play/Pause */}
          <button
            type="button"
            onClick={togglePlayPause}
            className="p-1.5 hover:bg-white/20 rounded transition-colors"
            aria-label={isPlaying ? 'Pausar vídeo' : 'Reproduzir vídeo'}
            title={isPlaying ? 'Pausar (Espaço)' : 'Reproduzir (Espaço)'}
          >
            {isPlaying ? (
              <Pause className="w-4 h-4" aria-hidden="true" />
            ) : (
              <Play className="w-4 h-4" aria-hidden="true" />
            )}
          </button>

          {/* Botão Expandir/Minimizar */}
          <button
            type="button"
            onClick={toggleExpand}
            className="p-1.5 hover:bg-white/20 rounded transition-colors"
            aria-label={isExpanded ? 'Minimizar player' : 'Expandir player'}
            title={isExpanded ? 'Minimizar' : 'Expandir'}
          >
            {isExpanded ? (
              <Minimize2 className="w-4 h-4" aria-hidden="true" />
            ) : (
              <Maximize2 className="w-4 h-4" aria-hidden="true" />
            )}
          </button>

          {/* Botão Fechar */}
          <button
            type="button"
            onClick={handleClose}
            className="p-1.5 hover:bg-white/20 rounded transition-colors"
            aria-label="Fechar mini player"
            title="Fechar (Esc)"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Player embed */}
      <div className={`
        relative bg-black overflow-hidden rounded-b-xl
        ${isExpanded ? 'aspect-video' : 'aspect-video'}
      `}>
        <div
          ref={playerRef}
          className="w-full h-full"
          id={`youtube-mini-player-${videoId}`}
        />
      </div>

      {/* Hint de atalhos (só mostra quando expandido) */}
      {isExpanded && (
        <div className="absolute bottom-2 left-2 right-2 px-3 py-2 bg-black/70 text-white text-xs rounded-lg opacity-0 hover:opacity-100 transition-opacity pointer-events-none">
          <p className="font-medium mb-1">Atalhos:</p>
          <ul className="space-y-0.5">
            <li><kbd className="bg-white/20 px-1 rounded">Espaço</kbd> - Play/Pause</li>
            <li><kbd className="bg-white/20 px-1 rounded">Esc</kbd> - Minimizar</li>
          </ul>
        </div>
      )}
    </div>
  );
}

MiniPlayer.propTypes = {
  videoId: PropTypes.string.isRequired,
  isMainPlayerVisible: PropTypes.bool.isRequired,
  currentTime: PropTypes.number,
  onTimeUpdate: PropTypes.func,
  position: PropTypes.oneOf(['bottom-right', 'bottom-left', 'top-right', 'top-left'])
};

export default MiniPlayer;
