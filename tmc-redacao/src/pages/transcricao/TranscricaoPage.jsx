import { useState, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Youtube, AlertTriangle } from 'lucide-react';

import { useDocumentTitle } from '../../hooks';
import { useCriar } from '../../context';
import TipBox from '../../components/ui/TipBox';
import { transcribeVideo } from '../../services/api';

import {
  YouTubeInput,
  VideoPreview,
  ProgressOverlay
} from './components';

import { useSteps } from './hooks';

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

  // Estado de loading e erros
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcriptionProgress, setTranscriptionProgress] = useState(0);
  const [transcriptionError, setTranscriptionError] = useState(null);

  // AbortController ref for cancelling in-flight API requests
  const abortControllerRef = useRef(null);

  // Handler para URL válida
  const handleValidURL = useCallback((data) => {
    setVideoData(data);
  }, []);

  // Iniciar transcrição
  const handleStartTranscription = useCallback(async () => {
    if (!videoData) return;

    // Create AbortController for this request
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsTranscribing(true);
    setTranscriptionProgress(0);
    setTranscriptionError(null);
    nextStep(); // Vai para step 2 (loading)

    // Simular progresso suave enquanto aguarda API
    const progressInterval = setInterval(() => {
      setTranscriptionProgress(prev => {
        if (prev >= 90) return prev; // Cap at 90% until API responds
        return Math.min(90, Math.round(prev + Math.random() * 12));
      });
    }, 400);

    try {
      const result = await transcribeVideo(
        { url: videoData.url },
        { signal: controller.signal }
      );

      clearInterval(progressInterval);
      setTranscriptionProgress(100);

      // Converter transcrição para formato de seleções
      const allSelections = result.transcription.map(segment => ({
        id: `card-${segment.id}`,
        text: segment.text,
        source: 'cards',
        topic: segment.topic,
        timestamp: segment.startTime,
      }));

      setTimeout(() => {
        setIsTranscribing(false);

        setFonte('transcription', {
          video: result.video,
          transcription: result.transcription,
          selections: allSelections,
        });

        navigate('/criar/texto-base');
      }, 500);
    } catch (err) {
      clearInterval(progressInterval);
      setIsTranscribing(false);

      // If user cancelled, don't show error
      if (err.name === 'AbortError') {
        goToStep(1);
        return;
      }

      // Map API error codes to user-friendly messages
      let errorMessage = 'Ocorreu um erro ao transcrever o vídeo. Tente novamente.';
      if (err?.status === 422) {
        errorMessage = err.data?.error || 'Este vídeo não possui legendas disponíveis.';
      } else if (err?.status === 404) {
        errorMessage = 'Vídeo não encontrado ou é privado.';
      } else if (err?.status === 429) {
        errorMessage = 'Muitas requisições. Aguarde um momento e tente novamente.';
      }

      setTranscriptionError(errorMessage);
      goToStep(1);
    } finally {
      abortControllerRef.current = null;
    }
  }, [videoData, nextStep, goToStep, setFonte, navigate]);

  // Cancelar transcrição
  const handleCancelTranscription = useCallback(() => {
    // Abort the in-flight API request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
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
              <h1 className="text-xl font-bold text-dark-gray">
                Transcrever Vídeo
              </h1>
            </div>
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

            {/* Error banner */}
            {transcriptionError && (
              <div
                className="flex items-center gap-3 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-6"
                role="alert"
              >
                <AlertTriangle className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                <p className="text-sm">{transcriptionError}</p>
                <button
                  type="button"
                  onClick={() => setTranscriptionError(null)}
                  className="ml-auto text-red-400 hover:text-red-600 text-lg leading-none"
                  aria-label="Fechar mensagem de erro"
                >
                  &times;
                </button>
              </div>
            )}

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
              Funciona com vídeos que possuem legendas (automáticas ou manuais) em português, inglês ou espanhol
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
