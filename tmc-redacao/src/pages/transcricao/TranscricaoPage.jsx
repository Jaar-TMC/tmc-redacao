import { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Youtube } from 'lucide-react';

import { useDocumentTitle } from '../../hooks';
import { useCriar } from '../../context';
import Breadcrumb from '../../components/ui/Breadcrumb';
import TipBox from '../../components/ui/TipBox';

import {
  YouTubeInput,
  VideoPreview,
  ProgressOverlay,
  StepIndicator
} from './components';

import { useSteps } from './hooks';

// Etapas do fluxo (simplificado)
const STEPS = [
  { id: 'input', label: 'Adicionar Vídeo' },
  { id: 'transcribing', label: 'Transcrevendo' }
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
 *
 * Fluxo simplificado:
 * 1. Inserir URL do YouTube
 * 2. Transcrever vídeo
 * 3. Ir direto para Texto-Base onde o usuário revisa/edita trechos
 */
function TranscricaoPage() {
  useDocumentTitle('Transcrever Vídeo - TMC Redação');
  const navigate = useNavigate();
  const { setFonte } = useCriar();

  // Estado do fluxo (apenas 2 steps agora)
  const { currentStep, nextStep, goToStep } = useSteps(2);

  // Estado dos dados
  const [url, setUrl] = useState('');
  const [videoData, setVideoData] = useState(null);

  // Estado de loading
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcriptionProgress, setTranscriptionProgress] = useState(0);

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

      // Converter transcrição para formato de seleções (todos os trechos)
      const allSelections = MOCK_TRANSCRIPTION.map(segment => ({
        id: `card-${segment.id}`,
        text: segment.text,
        source: 'cards',
        topic: segment.topic,
        timestamp: segment.startTime
      }));

      // Salvar no contexto e navegar para Texto-Base
      setTimeout(() => {
        setIsTranscribing(false);

        // Salvar vídeo + todos os trechos transcritos
        setFonte('transcription', {
          video: videoData,
          transcription: MOCK_TRANSCRIPTION,
          selections: allSelections
        });

        // Navegar para Texto-Base onde o usuário vai revisar/editar
        navigate('/criar/texto-base');
      }, 500);
    } catch (error) {
      clearInterval(progressInterval);
      setIsTranscribing(false);
      goToStep(1);
      // TODO: Mostrar erro
    }
  }, [videoData, nextStep, goToStep, setFonte, navigate]);

  // Cancelar transcrição
  const handleCancelTranscription = useCallback(() => {
    setIsTranscribing(false);
    setTranscriptionProgress(0);
    goToStep(1);
  }, [goToStep]);

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
              {/* Logo YouTube oficial */}
              <div className="flex items-center justify-center mb-4">
                <svg
                  className="w-20 h-auto"
                  viewBox="0 0 159 110"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-label="YouTube"
                >
                  <path
                    d="M154 17.5c-1.82-6.73-7.07-12-13.8-13.8C128.1 0 78.83 0 78.83 0s-49.27 0-61.37 3.7C10.8 5.5 5.54 10.77 3.72 17.5 0 29.6 0 55 0 55s0 25.4 3.72 37.5c1.82 6.73 7.08 12 13.8 13.8 12.1 3.7 61.37 3.7 61.37 3.7s49.27 0 61.37-3.7c6.73-1.82 11.98-7.07 13.8-13.8C158 80.4 158 55 158 55s0-25.4-4-37.5z"
                    fill="#FF0000"
                  />
                  <path d="M64 78.75V31.25L103.5 55 64 78.75z" fill="#FFFFFF" />
                </svg>
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
            <TipBox className="mt-6">
              Funciona melhor com vídeos que possuem legendas
              ou áudio claro em português/inglês
            </TipBox>
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
      </main>
    </div>
  );
}

export default TranscricaoPage;
