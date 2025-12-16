/**
 * EXEMPLO DE INTEGRAÇÃO DO MINIPLAYER NA TRANSCRICAOPAGE
 *
 * Este arquivo demonstra como integrar o MiniPlayer na página de transcrição.
 * Copie e adapte as seções conforme necessário.
 */

import { useState, useRef, useEffect } from 'react';
import { MiniPlayer } from './components';

function TranscricaoPageComMiniPlayer() {
  // ... outros estados da página

  // ADICIONAR: Estados para o MiniPlayer
  const [isMainPlayerVisible, setIsMainPlayerVisible] = useState(true);
  const mainPlayerRef = useRef(null);

  // ADICIONAR: IntersectionObserver para detectar quando player sai de vista
  useEffect(() => {
    // Só observar quando estiver no step 3 (seleção de trechos)
    if (!mainPlayerRef.current || currentStep !== 3) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        // Player está visível quando 50% ou mais está na viewport
        setIsMainPlayerVisible(entry.isIntersecting);
      },
      {
        threshold: 0.5, // 50% do elemento deve estar visível
        rootMargin: '0px' // Sem margem adicional
      }
    );

    observer.observe(mainPlayerRef.current);

    return () => {
      observer.disconnect();
    };
  }, [currentStep]); // Re-observar quando mudar de step

  return (
    <div className="min-h-screen bg-off-white pt-16">
      {/* ... header da página ... */}

      <main id="main-content" role="main" className="max-w-7xl mx-auto px-4 py-6">
        {/* Step 1: Input */}
        {currentStep === 1 && (
          // ... código do step 1 ...
        )}

        {/* Step 2: Loading */}
        {/* ... código do step 2 ... */}

        {/* Step 3: Seleção de trechos */}
        {currentStep === 3 && (
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Coluna esquerda: Vídeo + Transcrição */}
            <div className="w-full lg:w-3/5">

              {/* MODIFICAR: Adicionar ref ao player principal */}
              {videoData && (
                <div
                  ref={mainPlayerRef}
                  className="bg-black rounded-xl overflow-hidden mb-4 aspect-video"
                >
                  <iframe
                    src={`https://www.youtube.com/embed/${videoData.videoId}`}
                    title={videoData.title}
                    className="w-full h-full"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                </div>
              )}

              {/* ... resto do conteúdo da coluna esquerda ... */}
            </div>

            {/* Coluna direita: Configurações */}
            <div className="w-full lg:w-2/5">
              {/* ... ConfigPanel ... */}
            </div>
          </div>
        )}
      </main>

      {/* ADICIONAR: MiniPlayer (só aparece no step 3) */}
      {currentStep === 3 && videoData && (
        <MiniPlayer
          videoId={videoData.videoId}
          isMainPlayerVisible={isMainPlayerVisible}
          position="bottom-right"
        />
      )}

      {/* ... footer mobile ... */}
    </div>
  );
}

export default TranscricaoPageComMiniPlayer;

// =============================================================================
// EXEMPLO COM SINCRONIZAÇÃO DE TEMPO (AVANÇADO)
// =============================================================================

function TranscricaoPageComSincronizacao() {
  // Estados básicos
  const [videoData, setVideoData] = useState(null);
  const [currentStep, setCurrentStep] = useState(1);

  // Estados do MiniPlayer
  const [isMainPlayerVisible, setIsMainPlayerVisible] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const mainPlayerRef = useRef(null);
  const mainYouTubePlayerRef = useRef(null);

  // IntersectionObserver
  useEffect(() => {
    if (!mainPlayerRef.current || currentStep !== 3) return;

    const observer = new IntersectionObserver(
      ([entry]) => setIsMainPlayerVisible(entry.isIntersecting),
      { threshold: 0.5 }
    );

    observer.observe(mainPlayerRef.current);
    return () => observer.disconnect();
  }, [currentStep]);

  // Carregar YouTube IFrame API
  useEffect(() => {
    // Verificar se já está carregado
    if (window.YT) return;

    // Carregar script
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    // Callback quando API estiver pronta
    window.onYouTubeIframeAPIReady = () => {
      console.log('YouTube API carregada');
    };
  }, []);

  // Inicializar player principal
  useEffect(() => {
    if (!window.YT || !videoData || currentStep !== 3) return;

    // Aguardar um tick para garantir que o DOM está pronto
    const timer = setTimeout(() => {
      if (!mainPlayerRef.current) return;

      mainYouTubePlayerRef.current = new window.YT.Player('main-youtube-player', {
        videoId: videoData.videoId,
        playerVars: {
          autoplay: 0,
          controls: 1,
          modestbranding: 1
        },
        events: {
          onStateChange: handlePlayerStateChange
        }
      });
    }, 100);

    return () => {
      clearTimeout(timer);
      if (mainYouTubePlayerRef.current) {
        mainYouTubePlayerRef.current.destroy();
        mainYouTubePlayerRef.current = null;
      }
    };
  }, [videoData, currentStep]);

  // Atualizar tempo quando player principal estiver tocando
  const handlePlayerStateChange = (event) => {
    if (event.data === window.YT.PlayerState.PLAYING) {
      const interval = setInterval(() => {
        if (mainYouTubePlayerRef.current) {
          const time = mainYouTubePlayerRef.current.getCurrentTime();
          setCurrentTime(time);
        }
      }, 1000);

      return () => clearInterval(interval);
    }
  };

  // Callback quando mini player atualiza o tempo
  const handleMiniPlayerTimeUpdate = (time) => {
    setCurrentTime(time);

    // Sincronizar com player principal se estiver visível
    if (mainYouTubePlayerRef.current && isMainPlayerVisible) {
      mainYouTubePlayerRef.current.seekTo(time, true);
    }
  };

  // Handler para ir para momento específico (botão "Ir para momento")
  const handleGoToMoment = (timestamp) => {
    // Converter timestamp "00:45" para segundos
    const [minutes, seconds] = timestamp.split(':').map(Number);
    const timeInSeconds = minutes * 60 + seconds;

    // Atualizar estado
    setCurrentTime(timeInSeconds);

    // Seek no player principal
    if (mainYouTubePlayerRef.current) {
      mainYouTubePlayerRef.current.seekTo(timeInSeconds, true);
    }

    // Scroll para o player se não estiver visível
    if (!isMainPlayerVisible && mainPlayerRef.current) {
      mainPlayerRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }
  };

  return (
    <div className="min-h-screen bg-off-white pt-16">
      <main id="main-content" role="main" className="max-w-7xl mx-auto px-4 py-6">
        {currentStep === 3 && (
          <div className="flex flex-col lg:flex-row gap-6">
            <div className="w-full lg:w-3/5">
              {/* Player com API do YouTube */}
              {videoData && (
                <div
                  ref={mainPlayerRef}
                  className="bg-black rounded-xl overflow-hidden mb-4 aspect-video"
                >
                  <div id="main-youtube-player" className="w-full h-full" />
                </div>
              )}

              {/* Lista de transcrição com botão "Ir para momento" */}
              <div className="space-y-3">
                {transcription.map(segment => (
                  <TranscriptionCard
                    key={segment.id}
                    segment={segment}
                    isSelected={selection.isSelected(segment.id)}
                    onToggle={selection.toggle}
                    onGoToMoment={handleGoToMoment} // Conectar handler
                  />
                ))}
              </div>
            </div>

            <div className="w-full lg:w-2/5">
              {/* ConfigPanel */}
            </div>
          </div>
        )}
      </main>

      {/* MiniPlayer com sincronização */}
      {currentStep === 3 && videoData && (
        <MiniPlayer
          videoId={videoData.videoId}
          isMainPlayerVisible={isMainPlayerVisible}
          currentTime={currentTime}
          onTimeUpdate={handleMiniPlayerTimeUpdate}
          position="bottom-right"
        />
      )}
    </div>
  );
}

// =============================================================================
// NOTAS DE IMPLEMENTAÇÃO
// =============================================================================

/**
 * PASSO A PASSO PARA INTEGRAR:
 *
 * 1. ADICIONAR IMPORTS
 *    import { MiniPlayer } from './components';
 *
 * 2. ADICIONAR ESTADOS
 *    const [isMainPlayerVisible, setIsMainPlayerVisible] = useState(true);
 *    const mainPlayerRef = useRef(null);
 *
 * 3. ADICIONAR INTERSECTIONOBSERVER
 *    useEffect(() => {
 *      if (!mainPlayerRef.current || currentStep !== 3) return;
 *      const observer = new IntersectionObserver(...);
 *      observer.observe(mainPlayerRef.current);
 *      return () => observer.disconnect();
 *    }, [currentStep]);
 *
 * 4. ADICIONAR REF AO PLAYER PRINCIPAL
 *    <div ref={mainPlayerRef} className="...">
 *      <iframe ... />
 *    </div>
 *
 * 5. ADICIONAR MINIPLAYER NO JSX
 *    {currentStep === 3 && videoData && (
 *      <MiniPlayer
 *        videoId={videoData.videoId}
 *        isMainPlayerVisible={isMainPlayerVisible}
 *      />
 *    )}
 *
 * AJUSTES DE Z-INDEX:
 * - MiniPlayer usa z-50
 * - Certifique-se de que outros elementos fixos (header, footer mobile) usem z-index menor
 * - Header atual usa z-40 (correto)
 * - Footer mobile usa z-30 (correto)
 *
 * RESPONSIVIDADE:
 * - Em mobile, considerar ajustar posição para não sobrepor footer fixo
 * - Pode usar position="top-right" em mobile e "bottom-right" em desktop
 *
 * PERFORMANCE:
 * - IntersectionObserver é eficiente e não afeta performance
 * - YouTube API carrega lazy (só quando necessário)
 * - MiniPlayer só renderiza quando visível
 */
