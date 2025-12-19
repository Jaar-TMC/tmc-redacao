import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Search, CheckSquare, Trash2, List, FileText } from 'lucide-react';
import {
  SourceBadge,
  ContentStats,
  VideoTimeline,
  IntervalFilter,
  TooltipEducativo,
  ModeTabs
} from '../../../components/criar';
import TranscriptionCard from '../../transcricao/components/TranscriptionCard';
import MiniPlayer from '../../transcricao/components/MiniPlayer';

/**
 * TextoBaseVideo - Variante da pagina Texto-Base para transcricao de video
 *
 * Inclui:
 * - Player de video com MiniPlayer
 * - Timeline visual interativa
 * - Filtros de intervalo de tempo
 * - Cards de transcricao selecionaveis
 */

// Dados mockados da transcricao
const mockTranscription = {
  videoId: 'dQw4w9WgXcQ', // Placeholder
  title: 'Entrevista Ministro Economia',
  duration: 765, // 12:45 em segundos
  segments: [
    {
      id: 'seg-1',
      startTime: '00:00',
      endTime: '00:45',
      topic: 'Introdução',
      text: 'O ministro da economia anunciou hoje em entrevista coletiva que o governo vai implementar novas medidas para conter a inflação nos próximos meses. As medidas foram recebidas com cautela pelo mercado financeiro, que aguarda mais detalhes sobre a implementação.'
    },
    {
      id: 'seg-2',
      startTime: '00:45',
      endTime: '02:15',
      topic: 'Medidas Anunciadas',
      text: 'Entre as principais medidas estão a redução de impostos sobre combustíveis, revisão das metas fiscais e aumento do salário mínimo. O ministro destacou que as medidas terão impacto positivo na economia em até 6 meses. "Estamos trabalhando para garantir que o brasileiro sinta a diferença no bolso", afirmou.'
    },
    {
      id: 'seg-3',
      startTime: '02:15',
      endTime: '03:30',
      topic: 'Críticas da Oposição',
      text: 'A oposição criticou as medidas, afirmando que são insuficientes para resolver os problemas estruturais da economia. O líder da oposição disse que o governo está "fazendo mais do mesmo" e que as medidas são "eleitoreiras". Segundo ele, seria necessário uma reforma tributária completa.'
    },
    {
      id: 'seg-4',
      startTime: '03:30',
      endTime: '05:00',
      topic: 'Reação do Mercado',
      text: 'O mercado financeiro reagiu com volatilidade às notícias. O dólar subiu 0,5% nas primeiras horas após o anúncio, mas depois estabilizou. A bolsa de valores fechou em leve alta de 0,2%. Analistas apontam que o mercado aguarda mais detalhes sobre o financiamento das medidas.'
    },
    {
      id: 'seg-5',
      startTime: '05:00',
      endTime: '06:15',
      topic: 'Próximos Passos',
      text: 'O ministro informou que enviará o projeto de lei ao Congresso na próxima semana. A expectativa é que a votação ocorra ainda este mês, antes do recesso parlamentar. O governo conta com apoio da base aliada para aprovar as medidas.'
    }
  ]
};

// Converter timestamp para segundos
const parseTimeToSeconds = (time) => {
  if (!time) return 0;
  const parts = time.split(':').map(p => parseInt(p, 10));
  if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  } else if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  return 0;
};

const TextoBaseVideo = ({
  fonte,
  onChangeSource,
  onDataChange
}) => {
  // States
  const [selectedSegments, setSelectedSegments] = useState(
    () => new Set(mockTranscription.segments.map(s => s.id))
  );
  const [textHighlights, setTextHighlights] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [activeIntervals, setActiveIntervals] = useState([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [isMainPlayerVisible, setIsMainPlayerVisible] = useState(true);
  const [viewMode, setViewMode] = useState('segments'); // 'segments' | 'fulltext'
  const [fullTextContent, setFullTextContent] = useState('');

  // Refs
  const playerContainerRef = useRef(null);
  const youtubePlayerRef = useRef(null);
  const mainPlayerRef = useRef(null);

  // Video ID da fonte
  const videoId = fonte?.dados?.videoId || fonte?.dados?.url?.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/)?.[1] || mockTranscription.videoId;

  // Inicializar texto completo a partir dos segmentos
  useEffect(() => {
    const fullText = mockTranscription.segments
      .map(seg => `[${seg.startTime}] ${seg.topic}\n${seg.text}`)
      .join('\n\n');
    setFullTextContent(fullText);
  }, []);

  // Inicializar YouTube player principal
  useEffect(() => {
    if (!mainPlayerRef.current || !videoId) return;

    let isMounted = true;

    function initializeMainPlayer() {
      if (!mainPlayerRef.current || !isMounted) return;

      // Destruir player anterior se existir
      if (youtubePlayerRef.current?.destroy) {
        youtubePlayerRef.current.destroy();
        youtubePlayerRef.current = null;
      }

      youtubePlayerRef.current = new window.YT.Player(mainPlayerRef.current, {
        videoId: videoId,
        playerVars: {
          autoplay: 0,
          controls: 1,
          modestbranding: 1,
          rel: 0
        },
        events: {
          onReady: () => {
            // Player pronto
          },
          onStateChange: (event) => {
            if (!isMounted) return;
            // Atualizar tempo atual quando reproduzindo
            if (event.data === window.YT.PlayerState.PLAYING) {
              const updateTime = () => {
                if (youtubePlayerRef.current?.getCurrentTime) {
                  setCurrentTime(youtubePlayerRef.current.getCurrentTime());
                }
              };
              const interval = setInterval(updateTime, 1000);
              youtubePlayerRef.current._timeInterval = interval;
            } else {
              if (youtubePlayerRef.current?._timeInterval) {
                clearInterval(youtubePlayerRef.current._timeInterval);
              }
            }
          }
        }
      });
    }

    // Verificar se a API do YouTube já está carregada
    if (window.YT?.Player) {
      initializeMainPlayer();
    } else {
      // Carregar script da API do YouTube se não existir
      if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
        const tag = document.createElement('script');
        tag.src = 'https://www.youtube.com/iframe_api';
        const firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
      }

      // Usar callback chain para não sobrescrever outros handlers
      const existingCallback = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        existingCallback?.();
        initializeMainPlayer();
      };
    }

    return () => {
      isMounted = false;
      if (youtubePlayerRef.current?._timeInterval) {
        clearInterval(youtubePlayerRef.current._timeInterval);
      }
      if (youtubePlayerRef.current?.destroy) {
        youtubePlayerRef.current.destroy();
        youtubePlayerRef.current = null;
      }
    };
  }, [videoId]);

  // Observer para detectar quando player sai de vista
  useEffect(() => {
    if (!playerContainerRef.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsMainPlayerVisible(entry.isIntersecting);
      },
      { threshold: 0.3 }
    );

    observer.observe(playerContainerRef.current);

    return () => observer.disconnect();
  }, []);

  // Filtrar segmentos por busca e intervalo
  const filteredSegments = useMemo(() => {
    return mockTranscription.segments.filter(segment => {
      // Filtro de busca
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesText = segment.text.toLowerCase().includes(query);
        const matchesTopic = segment.topic?.toLowerCase().includes(query);
        if (!matchesText && !matchesTopic) return false;
      }

      // Filtro de intervalo
      if (activeIntervals.length > 0) {
        const segmentStart = parseTimeToSeconds(segment.startTime);
        const isInInterval = activeIntervals.some(intervalId => {
          const [start, end] = intervalId.split('-').map(Number);
          return segmentStart >= start && segmentStart < end;
        });
        if (!isInInterval) return false;
      }

      return true;
    });
  }, [searchQuery, activeIntervals]);

  // Estatisticas
  const stats = useMemo(() => {
    let wordCount = 0;
    selectedSegments.forEach(id => {
      const segment = mockTranscription.segments.find(s => s.id === id);
      if (segment) {
        wordCount += segment.text.split(/\s+/).filter(Boolean).length;
      }
    });

    return {
      selected: selectedSegments.size,
      total: mockTranscription.segments.length,
      words: wordCount
    };
  }, [selectedSegments]);

  // Marcadores para timeline
  const timelineMarkers = useMemo(() => {
    return mockTranscription.segments.map(segment => ({
      id: segment.id,
      time: segment.startTime,
      label: segment.topic,
      selected: selectedSegments.has(segment.id)
    }));
  }, [selectedSegments]);

  // Handlers
  const handleToggleSegment = useCallback((segmentId) => {
    setSelectedSegments(prev => {
      const newSet = new Set(prev);
      if (newSet.has(segmentId)) {
        newSet.delete(segmentId);
      } else {
        newSet.add(segmentId);
      }
      return newSet;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedSegments(new Set(mockTranscription.segments.map(s => s.id)));
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedSegments(new Set());
  }, []);

  const handleTextSelect = useCallback((segmentId, selectedText, isRemove = false) => {
    setTextHighlights(prev => {
      const current = prev[segmentId] || [];
      if (isRemove) {
        return {
          ...prev,
          [segmentId]: current.filter(t => t !== selectedText)
        };
      }
      return {
        ...prev,
        [segmentId]: [...current, selectedText]
      };
    });
  }, []);

  const handleToggleInterval = useCallback((intervalId) => {
    setActiveIntervals(prev => {
      if (prev.includes(intervalId)) {
        return prev.filter(id => id !== intervalId);
      }
      return [...prev, intervalId];
    });
  }, []);

  const handleShowAllIntervals = useCallback(() => {
    setActiveIntervals([]);
  }, []);

  const handleMarkerClick = useCallback((seconds, segmentId) => {
    setCurrentTime(seconds);
    // Seek no player do YouTube
    if (youtubePlayerRef.current?.seekTo) {
      youtubePlayerRef.current.seekTo(seconds, true);
    }
  }, []);

  const handleGoToMoment = useCallback((seconds) => {
    setCurrentTime(seconds);
    if (youtubePlayerRef.current?.seekTo) {
      youtubePlayerRef.current.seekTo(seconds, true);
    }
  }, []);

  const handlePlaySegment = useCallback((segmentId, isPlaying) => {
    const segment = mockTranscription.segments.find(s => s.id === segmentId);
    if (segment && youtubePlayerRef.current) {
      if (isPlaying) {
        const seconds = parseTimeToSeconds(segment.startTime);
        youtubePlayerRef.current.seekTo(seconds, true);
        youtubePlayerRef.current.playVideo();
      } else {
        youtubePlayerRef.current.pauseVideo();
      }
    }
  }, []);

  const handleTimeUpdate = useCallback((time) => {
    setCurrentTime(time);
  }, []);

  // Notificar mudancas ao componente pai
  useEffect(() => {
    if (onDataChange) {
      onDataChange({
        selectedSegments: Array.from(selectedSegments),
        textHighlights,
        wordCount: stats.words
      });
    }
  }, [selectedSegments, textHighlights, stats.words, onDataChange]);

  // Formatar duracao para exibicao
  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-6">
      {/* Badge da fonte */}
      <SourceBadge
        type="video"
        title={fonte?.dados?.preview?.title || mockTranscription.title}
        subtitle={formatDuration(mockTranscription.duration)}
        onChangeSource={onChangeSource}
      />

      {/* Layout principal - duas colunas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Coluna esquerda - Player e Timeline */}
        <div className="space-y-4">
          {/* Player principal */}
          <div
            ref={playerContainerRef}
            className="bg-black rounded-xl overflow-hidden aspect-video"
          >
            <div
              ref={mainPlayerRef}
              id="youtube-main-player"
              className="w-full h-full"
            />
          </div>

          {/* Timeline */}
          <VideoTimeline
            duration={mockTranscription.duration}
            markers={timelineMarkers}
            currentTime={currentTime}
            onMarkerClick={handleMarkerClick}
          />

          {/* Filtros de intervalo */}
          <IntervalFilter
            duration={mockTranscription.duration}
            activeIntervals={activeIntervals}
            onToggleInterval={handleToggleInterval}
            onShowAll={handleShowAllIntervals}
          />
        </div>

        {/* Coluna direita - Transcricao */}
        <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
          {/* Header com Tabs */}
          <div className="p-4 border-b border-light-gray">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold text-dark-gray">
                  Transcrição
                </h3>
                <TooltipEducativo
                  title="Transcrição"
                  icon="📝"
                  position="right"
                >
                  <ul className="space-y-2">
                    <li className="flex items-start gap-2">
                      <span className="text-tmc-orange">•</span>
                      <span>Selecione os trechos que deseja usar na matéria</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-tmc-orange">•</span>
                      <span>Expanda um card para selecionar texto específico</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-tmc-orange">•</span>
                      <span>Use os filtros de tempo para navegar rapidamente</span>
                    </li>
                  </ul>
                </TooltipEducativo>
              </div>
            </div>

            {/* Tabs de visualização */}
            <ModeTabs
              activeTab={viewMode}
              onTabChange={setViewMode}
              tabs={[
                { id: 'segments', label: 'Trechos', icon: <List size={16} /> },
                { id: 'fulltext', label: 'Texto Completo', icon: <FileText size={16} /> }
              ]}
            />
          </div>

          {/* Conteúdo baseado no modo */}
          {viewMode === 'segments' ? (
            <>
              {/* Header de controles para modo trechos */}
              <div className="p-4 border-b border-light-gray">
                {/* Busca */}
                <div className="relative mb-4">
                  <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-medium-gray" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Buscar na transcrição..."
                    className="w-full pl-10 pr-4 py-2 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                  />
                </div>

                {/* Controles de selecao */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleSelectAll}
                      className="flex items-center gap-1 text-sm text-tmc-orange hover:text-tmc-orange/80"
                    >
                      <CheckSquare size={16} />
                      Todos
                    </button>
                    <span className="text-light-gray">|</span>
                    <button
                      onClick={handleClearSelection}
                      className="flex items-center gap-1 text-sm text-medium-gray hover:text-red-500"
                    >
                      <Trash2 size={16} />
                      Limpar
                    </button>
                  </div>
                  <span className="text-sm text-medium-gray">
                    {stats.selected} de {stats.total}
                  </span>
                </div>
              </div>

              {/* Lista de cards */}
              <div className="p-4 max-h-[500px] overflow-y-auto">
                {filteredSegments.length === 0 ? (
                  <div className="text-center py-8 text-medium-gray">
                    <p>Nenhum trecho encontrado</p>
                    {(searchQuery || activeIntervals.length > 0) && (
                      <button
                        onClick={() => {
                          setSearchQuery('');
                          setActiveIntervals([]);
                        }}
                        className="mt-2 text-sm text-tmc-orange hover:underline"
                      >
                        Limpar filtros
                      </button>
                    )}
                  </div>
                ) : (
                  filteredSegments.map(segment => (
                    <TranscriptionCard
                      key={segment.id}
                      segment={segment}
                      isSelected={selectedSegments.has(segment.id)}
                      onToggle={handleToggleSegment}
                      onPlaySegment={handlePlaySegment}
                      onGoToMoment={handleGoToMoment}
                      onTextSelect={handleTextSelect}
                      textHighlights={textHighlights[segment.id] || []}
                    />
                  ))
                )}
              </div>
            </>
          ) : (
            /* Modo texto completo */
            <div className="p-4">
              <textarea
                value={fullTextContent}
                onChange={(e) => setFullTextContent(e.target.value)}
                className="w-full h-[450px] p-4 border border-light-gray rounded-lg resize-none text-sm text-dark-gray leading-relaxed focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange font-mono"
                placeholder="Transcrição completa do vídeo..."
              />
              <p className="text-xs text-medium-gray mt-2">
                💡 Edite o texto livremente. Alterações serão usadas na geração da matéria.
              </p>
            </div>
          )}

          {/* Footer com stats */}
          <ContentStats
            selectedCount={stats.selected}
            totalCount={stats.total}
            wordCount={stats.words}
            variant="video"
          />
        </div>
      </div>

      {/* Mini Player */}
      <MiniPlayer
        videoId={videoId}
        isMainPlayerVisible={isMainPlayerVisible}
        currentTime={currentTime}
        onTimeUpdate={handleTimeUpdate}
      />
    </div>
  );
};

TextoBaseVideo.propTypes = {
  fonte: PropTypes.shape({
    tipo: PropTypes.string,
    dados: PropTypes.shape({
      url: PropTypes.string,
      videoId: PropTypes.string,
      preview: PropTypes.object
    })
  }),
  onChangeSource: PropTypes.func,
  onDataChange: PropTypes.func
};

export default TextoBaseVideo;
