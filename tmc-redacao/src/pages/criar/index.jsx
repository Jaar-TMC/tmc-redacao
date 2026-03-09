import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, HelpCircle, Video, Flame, Newspaper, PenLine } from 'lucide-react';
import { Stepper } from '../../components/criar';
import SourceCard from '../../components/criar/SourceCard';
import UrlInputModal from '../../components/criar/UrlInputModal';
import TemaSelector from '../../components/criar/TemaSelector';
import FeedSelector from '../../components/criar/FeedSelector';
import TipBox from '../../components/ui/TipBox';
import { useCriar } from '../../context';
import { FEATURES } from '../../config/featureFlags';
import { useOnboarding, TOUR_IDS } from '../../components/onboarding';

/**
 * Página de Seleção de Fonte (Etapa 1)
 *
 * Layout: Grid 2x2 de cards de fonte
 * Permite selecionar entre:
 * - Transcrição de Vídeo (abre modal)
 * - Tema em Alta (expande seletor inline)
 * - Matérias do Feed (expande seletor inline)
 * - Link da Web (abre modal)
 */
const CriarMateria = () => {
  const navigate = useNavigate();
  const { setFonte, setSelectedTags } = useCriar();
  const [selectedSource, setSelectedSource] = useState(null);
  const [showUrlModal, setShowUrlModal] = useState(false);
  const [urlModalType, setUrlModalType] = useState('youtube');
  const [expandedSelector, setExpandedSelector] = useState(null); // 'tema' | 'feed' | null
  const { shouldShowTour, startTour } = useOnboarding();

  // Auto-trigger onboarding tour for first-time users
  useEffect(() => {
    if (shouldShowTour(TOUR_IDS.CRIAR) && !expandedSelector) {
      // Delay to ensure page is fully loaded
      const timeoutId = setTimeout(() => {
        startTour(TOUR_IDS.CRIAR);
      }, 800);
      return () => clearTimeout(timeoutId);
    }
  }, [shouldShowTour, startTour, expandedSelector]);

  const handleSourceClick = (sourceType) => {
    // Resetar estados anteriores
    setExpandedSelector(null);
    setShowUrlModal(false);

    if (sourceType === 'video') {
      setUrlModalType('youtube');
      setShowUrlModal(true);
      setSelectedSource('video');
    } else if (sourceType === 'web') {
      setUrlModalType('web');
      setShowUrlModal(true);
      setSelectedSource('web');
    } else if (sourceType === 'tema') {
      // Ir direto para TextoBaseTema sem dados pré-selecionados
      // A seleção de tema será feita na própria página
      setFonte('tema', {});
      navigate('/criar/texto-base');
    } else if (sourceType === 'feed') {
      setExpandedSelector('feed');
      setSelectedSource('feed');
    } else if (sourceType === 'zero') {
      setFonte('zero', {});
      navigate('/criar/texto-base');
    }
  };

  const handleUrlSubmit = (data) => {
    // Salvar fonte no contexto e navegar
    const tipo = urlModalType === 'youtube' ? 'video' : 'link';
    setFonte(tipo, {
      url: data.url,
      preview: data.preview
    });
    navigate('/criar/texto-base');
  };

  const handleTemaSelect = (theme) => {
    // Salvar fonte no contexto e navegar
    setFonte('tema', theme);
    navigate('/criar/texto-base');
  };

  const handleFeedSelect = (articles, tags = []) => {
    // Salvar fonte no contexto e navegar
    setFonte('feed', articles);
    // Salvar tags selecionadas para SEO
    if (tags.length > 0) {
      setSelectedTags(tags);
    }
    navigate('/criar/texto-base');
  };

  const handleBack = () => {
    navigate('/');
  };

  const handleStepClick = useCallback((_stepIndex) => {
    // Na etapa 1, não há etapas anteriores para navegar
    // Este handler existe para manter consistência com as outras páginas
  }, []);

  const closeSelector = () => {
    setExpandedSelector(null);
    setSelectedSource(null);
  };

  return (
    <div className="min-h-screen bg-off-white">
      {/* Header */}
      <header className="bg-white border-b border-light-gray sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={handleBack}
              className="flex items-center gap-2 text-medium-gray hover:text-dark-gray transition-colors"
              aria-label="Voltar para redação"
            >
              <ArrowLeft size={20} />
              <span className="text-sm font-medium hidden sm:inline">Redação</span>
            </button>

            <h1 className="text-lg md:text-xl font-bold text-dark-gray">
              CRIAR NOVA MATÉRIA
            </h1>

            <button
              onClick={() => startTour(TOUR_IDS.CRIAR)}
              className="flex items-center gap-2 text-medium-gray hover:text-dark-gray transition-colors"
              aria-label="Iniciar tour guiado desta página"
            >
              <HelpCircle size={20} />
              <span className="text-sm font-medium hidden sm:inline">Ajuda</span>
            </button>
          </div>
        </div>
      </header>

      {/* Stepper */}
      <div className="bg-white border-b border-light-gray" data-tour="stepper">
        <div className="max-w-7xl mx-auto px-4 md:px-6">
          <Stepper
            steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
            currentStep={0}
            onStepClick={handleStepClick}
          />
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 md:px-6 py-8">
        {/* Título */}
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-dark-gray mb-2">
            Escolha o ponto de partida
          </h2>
        </div>

        {/* Grid de Cards ou Seletor Expandido */}
        {expandedSelector ? (
          <div className="max-w-3xl mx-auto">
            {expandedSelector === 'tema' && (
              <TemaSelector
                onClose={closeSelector}
                onSelect={handleTemaSelect}
              />
            )}
            {expandedSelector === 'feed' && (
              <FeedSelector
                onClose={closeSelector}
                onSelect={handleFeedSelect}
              />
            )}
          </div>
        ) : (
          <>
            {/* Grid de Source Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto mb-8">
              {/* MVP: RSS Feed - Primary source */}
              <div data-tour="source-feed">
                <SourceCard
                  icon={<Newspaper size={28} strokeWidth={1.5} />}
                  title="MATÉRIAS DO FEED"
                  description="Use matérias dos seus concorrentes"
                  selected={selectedSource === 'feed'}
                  onClick={() => handleSourceClick('feed')}
                />
              </div>


              {/* Post-MVP: Video Transcription */}
              {FEATURES.VIDEO_TRANSCRIPTION && (
                <div data-tour="source-video">
                  <SourceCard
                    icon={<Video size={28} strokeWidth={1.5} />}
                    title="TRANSCRIÇÃO DE VÍDEO"
                    description="Extraia de um vídeo do YouTube"
                    selected={selectedSource === 'video'}
                    onClick={() => handleSourceClick('video')}
                  />
                </div>
              )}

              {/* Post-MVP: Trending Themes (requires Google Trends) */}
              {FEATURES.GOOGLE_TRENDS && (
                <div data-tour="source-tema">
                  <SourceCard
                    icon={<Flame size={28} strokeWidth={1.5} />}
                    title="TEMA EM ALTA"
                    description="Escolha entre os assuntos do momento"
                    selected={selectedSource === 'tema'}
                    onClick={() => handleSourceClick('tema')}
                  />
                </div>
              )}

              {/* Criar do Zero - texto livre */}
              <div data-tour="source-zero">
                <SourceCard
                  icon={<PenLine size={28} strokeWidth={1.5} />}
                  title="CRIAR DO ZERO"
                  description="Cole qualquer texto como ponto de partida"
                  selected={selectedSource === 'zero'}
                  onClick={() => handleSourceClick('zero')}
                />
              </div>
            </div>

            {/* Dica */}
            <div className="max-w-3xl mx-auto" data-tour="tip-box">
              <TipBox>
                Não importa qual fonte escolher, você poderá adicionar
                instruções e configurações complementares na etapa 3
              </TipBox>

              {/* Botão para ir direto ao editor */}
              <div className="mt-6 text-center">
                <button
                  onClick={() => {
                    setFonte('manual', { skipSteps: true });
                    navigate('/criar/editor');
                  }}
                  className="text-medium-gray hover:text-tmc-orange text-sm underline transition-colors"
                >
                  Ou ir direto ao editor sem ponto de partida →
                </button>
              </div>
            </div>
          </>
        )}
      </main>

      {/* Modal de URL */}
      <UrlInputModal
        isOpen={showUrlModal}
        onClose={() => {
          setShowUrlModal(false);
          setSelectedSource(null);
        }}
        type={urlModalType}
        onSubmit={handleUrlSubmit}
      />
    </div>
  );
};

export default CriarMateria;
