import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, HelpCircle, Video, Flame, Newspaper, Globe } from 'lucide-react';
import { Stepper } from '../../components/criar';
import SourceCard from '../../components/criar/SourceCard';
import UrlInputModal from '../../components/criar/UrlInputModal';
import TemaSelector from '../../components/criar/TemaSelector';
import FeedSelector from '../../components/criar/FeedSelector';
import TipBox from '../../components/ui/TipBox';
import { useCriar } from '../../context';

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
  const { setFonte } = useCriar();
  const [selectedSource, setSelectedSource] = useState(null);
  const [showUrlModal, setShowUrlModal] = useState(false);
  const [urlModalType, setUrlModalType] = useState('youtube');
  const [expandedSelector, setExpandedSelector] = useState(null); // 'tema' | 'feed' | null

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
    }
  };

  const handleUrlSubmit = (data) => {
    console.log('URL submitted:', data);
    // Salvar fonte no contexto e navegar
    const tipo = urlModalType === 'youtube' ? 'video' : 'link';
    setFonte(tipo, {
      url: data.url,
      preview: data.preview
    });
    navigate('/criar/texto-base');
  };

  const handleTemaSelect = (theme) => {
    console.log('Tema selected:', theme);
    // Salvar fonte no contexto e navegar
    setFonte('tema', theme);
    navigate('/criar/texto-base');
  };

  const handleFeedSelect = (articles) => {
    console.log('Articles selected:', articles);
    // Salvar fonte no contexto e navegar
    setFonte('feed', articles);
    navigate('/criar/texto-base');
  };

  const handleBack = () => {
    navigate('/');
  };

  const handleStepClick = useCallback((stepIndex) => {
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
              className="flex items-center gap-2 text-medium-gray hover:text-dark-gray transition-colors"
              aria-label="Ajuda"
            >
              <HelpCircle size={20} />
              <span className="text-sm font-medium hidden sm:inline">Help</span>
            </button>
          </div>
        </div>
      </header>

      {/* Stepper */}
      <div className="bg-white border-b border-light-gray">
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
              <SourceCard
                icon={<Video size={28} strokeWidth={1.5} />}
                title="TRANSCRIÇÃO DE VÍDEO"
                description="Extraia de um vídeo do YouTube"
                selected={selectedSource === 'video'}
                onClick={() => handleSourceClick('video')}
              />

              <SourceCard
                icon={<Flame size={28} strokeWidth={1.5} />}
                title="TEMA EM ALTA"
                description="Escolha entre os assuntos do momento"
                selected={selectedSource === 'tema'}
                onClick={() => handleSourceClick('tema')}
              />

              <SourceCard
                icon={<Newspaper size={28} strokeWidth={1.5} />}
                title="MATÉRIAS DO FEED"
                description="Use matérias dos seus concorrentes"
                selected={selectedSource === 'feed'}
                onClick={() => handleSourceClick('feed')}
              />

              <SourceCard
                icon={<Globe size={28} strokeWidth={1.5} />}
                title="LINK DA WEB"
                description="Cole qualquer link para extrair"
                selected={selectedSource === 'web'}
                onClick={() => handleSourceClick('web')}
              />
            </div>

            {/* Dica */}
            <div className="max-w-3xl mx-auto">
              <TipBox>
                Não importa qual fonte escolher, você poderá adicionar
                materiais complementares (links, PDFs, vídeos) na etapa 3
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
