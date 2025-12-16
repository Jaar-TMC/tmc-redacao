import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Youtube, CheckSquare, Square, Search } from 'lucide-react';

import { useDocumentTitle } from '../../hooks';
import Breadcrumb from '../../components/ui/Breadcrumb';

import {
  YouTubeInput,
  VideoPreview,
  TranscriptionCard,
  ConfigPanel,
  ProgressOverlay,
  StepIndicator,
  SelectionSidebar,
  MiniPlayer
} from './components';

import { useMultiSelect, useSteps } from './hooks';

// Etapas do fluxo
const STEPS = [
  { id: 'input', label: 'Adicionar Vídeo' },
  { id: 'transcribing', label: 'Transcrevendo' },
  { id: 'select', label: 'Selecionar Trechos' }
];

// Mock de transcrição (em produção, viria da API)
const MOCK_TRANSCRIPTION = [
  {
    id: '1',
    startTime: '00:00',
    endTime: '00:45',
    text: 'Olá, sejam bem-vindos ao nosso canal. Hoje vamos falar sobre um tema muito importante que tem chamado a atenção de todos.',
    topic: 'Introdução'
  },
  {
    id: '2',
    startTime: '00:45',
    endTime: '02:12',
    text: 'Nos últimos meses, observamos uma mudança significativa no comportamento do mercado. As empresas estão cada vez mais focadas em inovação.',
    topic: 'Tendências de Mercado'
  },
  {
    id: '3',
    startTime: '02:12',
    endTime: '04:30',
    text: 'Especialistas apontam que essa tendência deve continuar pelos próximos anos. A tecnologia está transformando todos os setores da economia.',
    topic: 'Transformação Digital'
  },
  {
    id: '4',
    startTime: '04:30',
    endTime: '06:15',
    text: 'Os dados mostram um crescimento de 45% em investimentos nessa área. Isso representa uma oportunidade única para quem está atento.',
    topic: 'Dados e Investimentos'
  },
  {
    id: '5',
    startTime: '06:15',
    endTime: '08:00',
    text: 'Para finalizar, gostaria de destacar três pontos principais que discutimos hoje e como eles podem impactar o seu dia a dia.',
    topic: 'Conclusão'
  }
];

/**
 * TranscricaoPage - Página de transcrição de vídeos do YouTube
 */
function TranscricaoPage() {
  useDocumentTitle('Transcrever Vídeo - TMC Redação');
  const navigate = useNavigate();

  // Estado do fluxo
  const { currentStep, nextStep, goToStep, reset: resetSteps } = useSteps(3);

  // Estado dos dados
  const [url, setUrl] = useState('');
  const [videoData, setVideoData] = useState(null);
  const [transcription, setTranscription] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  // Estado de loading
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcriptionProgress, setTranscriptionProgress] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);

  // Seleção de cards inteiros
  const selection = useMultiSelect();

  // Seleção de texto dentro dos cards (por cardId)
  const [cardHighlights, setCardHighlights] = useState({}); // { [segmentId]: [texto1, texto2, ...] }

  // Seleções unificadas para o SelectionSidebar
  const [unifiedSelections, setUnifiedSelections] = useState([]);

  // Refs e estados para MiniPlayer
  const mainPlayerRef = useRef(null);
  const [isMainPlayerVisible, setIsMainPlayerVisible] = useState(true);
  const [currentVideoTime, setCurrentVideoTime] = useState(0);

  // Configurações da matéria
  const [config, setConfig] = useState({
    tone: 'journalistic',
    persona: 'impartial_journalist',
    creativity: 30,
    includeQuotes: true,
    citeSource: true,
    addIntroConclusion: false,
    keywords: []
  });

  // Filtrar transcrição por busca
  const filteredTranscription = transcription.filter(segment =>
    segment.text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Sincronizar seleções unificadas quando mudam cards ou highlights
  useEffect(() => {
    const selections = [];

    // Cards inteiros selecionados
    selection.selectedIds.forEach(id => {
      const segment = transcription.find(s => s.id === id);
      if (segment) {
        selections.push({
          id: `card-${id}`,
          text: segment.text,
          source: 'cards',
          topic: segment.topic,
          timestamp: segment.startTime
        });
      }
    });

    // Highlights de texto dentro dos cards
    Object.entries(cardHighlights).forEach(([segmentId, highlights]) => {
      const segment = transcription.find(s => s.id === segmentId);
      if (segment && highlights.length > 0) {
        highlights.forEach((text, index) => {
          selections.push({
            id: `text-${segmentId}-${index}`,
            text: text,
            source: 'full',
            topic: segment.topic,
            timestamp: segment.startTime
          });
        });
      }
    });

    setUnifiedSelections(selections);
  }, [selection.selectedIds, cardHighlights, transcription]);

  // Observer para detectar visibilidade do player principal
  useEffect(() => {
    if (!mainPlayerRef.current || currentStep !== 3) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsMainPlayerVisible(entry.isIntersecting);
      },
      { threshold: 0.3 }
    );

    observer.observe(mainPlayerRef.current);

    return () => observer.disconnect();
  }, [currentStep]);

  // Handler para URL válida
  const handleValidURL = useCallback((data) => {
    setVideoData(data);
  }, []);

  // Iniciar transcrição
  const handleStartTranscription = useCallback(async () => {
    if (!videoData) return;

    setIsTranscribing(true);
    setTranscriptionProgress(0);
    nextStep(); // Vai para step 2 (loading)

    // Simular progresso da transcrição
    const progressInterval = setInterval(() => {
      setTranscriptionProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return prev + Math.random() * 15;
      });
    }, 500);

    // Simular tempo de transcrição
    try {
      await new Promise(resolve => setTimeout(resolve, 4000));

      clearInterval(progressInterval);
      setTranscriptionProgress(100);

      // Definir transcrição mock
      setTranscription(MOCK_TRANSCRIPTION);

      // Ir para step 3 (seleção)
      setTimeout(() => {
        setIsTranscribing(false);
        nextStep();
      }, 500);
    } catch (error) {
      clearInterval(progressInterval);
      setIsTranscribing(false);
      goToStep(1);
      // TODO: Mostrar erro
    }
  }, [videoData, nextStep, goToStep]);

  // Cancelar transcrição
  const handleCancelTranscription = useCallback(() => {
    setIsTranscribing(false);
    setTranscriptionProgress(0);
    goToStep(1);
  }, [goToStep]);

  // Gerar matéria
  const handleGenerate = useCallback(async () => {
    if (unifiedSelections.length === 0) return;

    setIsGenerating(true);

    // Simular geração
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Em produção, enviar para API e receber ID da matéria
    const articleId = 'new-' + Date.now();

    setIsGenerating(false);

    // Redirecionar para editor
    navigate(`/criar?from=transcription&id=${articleId}`);
  }, [unifiedSelections.length, navigate]);

  // Selecionar/desselecionar todos
  const handleSelectAll = useCallback(() => {
    const allIds = transcription.map(s => s.id);
    selection.selectAll(allIds);
  }, [transcription, selection]);

  const handleDeselectAll = useCallback(() => {
    selection.deselectAll();
  }, [selection]);

  // Play segment (mock)
  const handlePlaySegment = useCallback((segmentId, isPlaying) => {
    console.log('Play segment:', segmentId, isPlaying);
    // Em produção, controlar o player do YouTube
  }, []);

  // Go to moment - pula para timestamp no vídeo
  const handleGoToMoment = useCallback((seconds) => {
    // Se receber string (formato MM:SS), converter para segundos
    let timeInSeconds = seconds;
    if (typeof seconds === 'string') {
      const parts = seconds.split(':').map(p => parseInt(p, 10));
      if (parts.length === 2) {
        timeInSeconds = parts[0] * 60 + parts[1];
      } else if (parts.length === 3) {
        timeInSeconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
      }
    }

    setCurrentVideoTime(timeInSeconds);

    // Scroll para o player principal se não estiver visível
    if (mainPlayerRef.current && !isMainPlayerVisible) {
      mainPlayerRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // Em produção, usar YouTube IFrame API para seek
    console.log('Seek to:', timeInSeconds, 'seconds');
  }, [isMainPlayerVisible]);

  // Handler para seleção de texto dentro dos cards
  const handleTextSelect = useCallback((segmentId, selectedText, isRemove = false) => {
    setCardHighlights(prev => {
      const current = prev[segmentId] || [];

      if (isRemove) {
        // Remover highlight
        const filtered = current.filter(h => h !== selectedText);
        if (filtered.length === 0) {
          const { [segmentId]: _, ...rest } = prev;
          return rest;
        }
        return { ...prev, [segmentId]: filtered };
      } else {
        // Adicionar highlight
        if (current.includes(selectedText)) return prev;
        return { ...prev, [segmentId]: [...current, selectedText] };
      }
    });
  }, []);

  // Handlers para SelectionSidebar
  const handleRemoveSelection = useCallback((selectionId) => {
    if (selectionId.startsWith('card-')) {
      // Remover seleção de card inteiro
      const cardId = selectionId.replace('card-', '');
      selection.toggle(cardId);
    } else if (selectionId.startsWith('text-')) {
      // Remover highlight de texto (formato: text-segmentId-index)
      const parts = selectionId.split('-');
      const segmentId = parts[1];
      // Encontrar o texto pelo índice na lista atual
      const segment = unifiedSelections.find(s => s.id === selectionId);
      if (segment) {
        handleTextSelect(segmentId, segment.text, true);
      }
    }
  }, [selection, unifiedSelections, handleTextSelect]);

  const handleReorderSelections = useCallback((fromIndex, toIndex) => {
    setUnifiedSelections(prev => {
      const newSelections = [...prev];
      const [moved] = newSelections.splice(fromIndex, 1);
      newSelections.splice(toIndex, 0, moved);
      return newSelections;
    });
  }, []);

  const handleClearAllSelections = useCallback(() => {
    selection.deselectAll();
    setCardHighlights({});
  }, [selection]);

  // Atalhos de teclado globais
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ignorar se estiver em input/textarea/select ou em elementos clicáveis
      if (e.target.matches('input, textarea, select, a, button, [role="button"]')) return;

      // Ctrl+V - Focus no input (Etapa 1)
      if (e.ctrlKey && e.key === 'v' && currentStep === 1) {
        e.preventDefault();
        document.getElementById('youtube-url')?.focus();
        return;
      }

      // Enter - Ação principal (só previne se não for em link/botão)
      if (e.key === 'Enter') {
        if (currentStep === 1 && videoData) {
          e.preventDefault();
          handleStartTranscription();
        } else if (currentStep === 3 && unifiedSelections.length > 0 && !isGenerating) {
          e.preventDefault();
          handleGenerate();
        }
        return;
      }

      // A / Shift+A - Seleção (Etapa 3)
      // Só previne se não for Ctrl+A (selecionar texto)
      if (e.key.toLowerCase() === 'a' && currentStep === 3 && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        if (e.shiftKey) {
          handleDeselectAll();
        } else {
          handleSelectAll();
        }
        return;
      }

      // Esc - Cancelar/Voltar
      if (e.key === 'Escape') {
        if (currentStep === 2 && isTranscribing) {
          handleCancelTranscription();
        } else if (currentStep === 3) {
          resetSteps();
          setTranscription([]);
          setVideoData(null);
          setUrl('');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentStep, videoData, unifiedSelections.length, isGenerating, isTranscribing, handleStartTranscription, handleGenerate, handleSelectAll, handleDeselectAll, handleCancelTranscription, resetSteps]);

  return (
    <div className="min-h-screen bg-off-white pt-16">
      {/* Header da página */}
      <div className="bg-white border-b border-light-gray sticky top-16 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {/* Voltar + Título */}
            <div className="flex items-center gap-4">
              <Link
                to="/"
                className="p-2 hover:bg-off-white rounded-lg transition-colors"
                aria-label="Voltar para Redação"
              >
                <ArrowLeft className="w-5 h-5 text-dark-gray" />
              </Link>
              <div>
                <h1 className="text-xl font-bold text-dark-gray">
                  Transcrever Vídeo
                </h1>
                <Breadcrumb
                  items={[
                    { label: 'Redação', href: '/' },
                    { label: 'Transcrever Vídeo' }
                  ]}
                />
              </div>
            </div>

            {/* Step Indicator */}
            <div className="hidden md:block">
              <StepIndicator steps={STEPS} currentStep={currentStep} />
            </div>
          </div>

          {/* Step Indicator Mobile */}
          <div className="md:hidden mt-4">
            <StepIndicator steps={STEPS} currentStep={currentStep} />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main id="main-content" role="main" className="max-w-7xl mx-auto px-4 py-6">
        {/* Step 1: Input */}
        {currentStep === 1 && (
          <div className="max-w-2xl mx-auto py-8">
            {/* Hero */}
            <div className="text-center mb-8">
              <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Youtube className="w-10 h-10 text-red-600" />
              </div>
              <h2 className="text-2xl font-bold text-dark-gray mb-2">
                Transcreva vídeos do YouTube
              </h2>
              <p className="text-medium-gray">
                Cole o link de um vídeo e transforme em matéria jornalística
              </p>
            </div>

            {/* Input */}
            <div className="bg-white rounded-xl p-6 shadow-sm border border-light-gray">
              <YouTubeInput
                value={url}
                onChange={setUrl}
                onValidURL={handleValidURL}
                disabled={isTranscribing}
              />

              {/* Preview do vídeo */}
              {videoData && (
                <div className="mt-6">
                  <VideoPreview video={videoData} />
                </div>
              )}

              {/* Botão de transcrever */}
              <div className="mt-6">
                <button
                  type="button"
                  onClick={handleStartTranscription}
                  disabled={!videoData || isTranscribing}
                  className={`
                    w-full py-3 px-6 rounded-lg font-semibold text-white
                    flex items-center justify-center gap-2
                    transition-all duration-200
                    ${videoData && !isTranscribing
                      ? 'bg-tmc-orange hover:bg-tmc-orange-dark'
                      : 'bg-light-gray text-medium-gray cursor-not-allowed'
                    }
                  `}
                >
                  <Youtube className="w-5 h-5" />
                  Transcrever Vídeo
                </button>

                {videoData && (
                  <p className="text-xs text-medium-gray text-center mt-2">
                    Tempo estimado: ~2 minutos para este vídeo
                  </p>
                )}
              </div>
            </div>

            {/* Dica */}
            <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-sm text-blue-800">
                <strong>Dica:</strong> Funciona melhor com vídeos que possuem legendas
                ou áudio claro em português/inglês
              </p>
            </div>
          </div>
        )}

        {/* Step 2: Transcrevendo (Loading) */}
        <ProgressOverlay
          isVisible={currentStep === 2 && isTranscribing}
          title="Transcrevendo vídeo"
          video={videoData}
          progress={transcriptionProgress}
          onCancel={handleCancelTranscription}
        />

        {/* Step 3: Seleção de trechos */}
        {currentStep === 3 && (
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Coluna esquerda: Vídeo + Transcrição */}
            <div className="w-full lg:w-3/5">
              {/* Player embed (simplificado) */}
              {videoData && (
                <div
                  ref={mainPlayerRef}
                  className="bg-black rounded-xl overflow-hidden mb-4 aspect-video"
                >
                  <iframe
                    src={`https://www.youtube.com/embed/${videoData.videoId}${currentVideoTime > 0 ? `?start=${Math.floor(currentVideoTime)}` : ''}`}
                    title={videoData.title}
                    className="w-full h-full"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                </div>
              )}

              {/* Toolbar de seleção */}
              <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSelectAll}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-medium-gray hover:text-dark-gray hover:bg-off-white rounded-lg transition-colors"
                  >
                    <CheckSquare className="w-4 h-4" />
                    <span className="hidden sm:inline">Selecionar Tudo</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleDeselectAll}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-medium-gray hover:text-dark-gray hover:bg-off-white rounded-lg transition-colors"
                  >
                    <Square className="w-4 h-4" />
                    <span className="hidden sm:inline">Limpar</span>
                  </button>
                </div>

                {/* Busca na transcrição */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-medium-gray" />
                  <input
                    type="text"
                    placeholder="Buscar na transcrição..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 pr-4 py-1.5 text-sm border border-light-gray rounded-lg focus:ring-2 focus:ring-tmc-orange focus:border-tmc-orange"
                  />
                </div>
              </div>

              {/* Cards de transcrição */}
              <div className="space-y-3">
                {filteredTranscription.map(segment => (
                  <TranscriptionCard
                    key={segment.id}
                    segment={segment}
                    isSelected={selection.isSelected(segment.id)}
                    onToggle={selection.toggle}
                    onPlaySegment={handlePlaySegment}
                    onGoToMoment={handleGoToMoment}
                    onTextSelect={handleTextSelect}
                    textHighlights={cardHighlights[segment.id] || []}
                  />
                ))}

                {filteredTranscription.length === 0 && searchQuery && (
                  <div className="text-center py-8 text-medium-gray">
                    <p>Nenhum trecho encontrado para &ldquo;{searchQuery}&rdquo;</p>
                  </div>
                )}
              </div>
            </div>

            {/* Coluna direita: Seleções + Configurações */}
            <div className="w-full lg:w-2/5 space-y-4">
              {/* Painel de seleções */}
              <SelectionSidebar
                selections={unifiedSelections}
                onRemove={handleRemoveSelection}
                onReorder={handleReorderSelections}
                onClear={handleClearAllSelections}
              />

              {/* Configurações da matéria */}
              <ConfigPanel
                config={config}
                onChange={setConfig}
                selection={{
                  selectedCount: unifiedSelections.length,
                  hasSelection: unifiedSelections.length > 0
                }}
                video={videoData}
                onGenerate={handleGenerate}
                isGenerating={isGenerating}
              />
            </div>
          </div>
        )}
      </main>

      {/* MiniPlayer - aparece quando o player principal sai de vista */}
      {currentStep === 3 && videoData && (
        <MiniPlayer
          videoId={videoData.videoId}
          isMainPlayerVisible={isMainPlayerVisible}
          currentTime={currentVideoTime}
          onTimeUpdate={setCurrentVideoTime}
          position="bottom-right"
        />
      )}

      {/* Footer fixo mobile (step 3) */}
      {currentStep === 3 && (
        <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-light-gray p-4 z-30">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={unifiedSelections.length === 0 || isGenerating}
            className={`
              w-full py-3 px-4 rounded-lg font-semibold text-white
              transition-all duration-200
              ${unifiedSelections.length > 0 && !isGenerating
                ? 'bg-tmc-orange hover:bg-tmc-orange-dark'
                : 'bg-light-gray text-medium-gray cursor-not-allowed'
              }
            `}
          >
            {isGenerating ? 'Gerando...' : `Gerar Matéria (${unifiedSelections.length} trechos)`}
          </button>
        </div>
      )}
    </div>
  );
}

export default TranscricaoPage;
