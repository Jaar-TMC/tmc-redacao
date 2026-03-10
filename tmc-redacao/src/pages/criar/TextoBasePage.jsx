import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, HelpCircle, Loader2 } from 'lucide-react';
import { Stepper, TooltipEducativo } from '../../components/criar';
import { useCriar } from '../../context';
import {
  TextoBaseVideo,
  TextoBaseTema,
  TextoBaseFeed,
  TextoBaseLink,
  TextoBaseZero
} from './variantes';

/**
 * TextoBasePage - Etapa 2 do fluxo de criação de matéria
 *
 * Wrapper que roteia para a variante correta baseado no tipo de fonte selecionada:
 * - video: Transcrição de vídeo com player e timeline
 * - transcription: Trechos selecionados de transcrição de YouTube
 * - tema: Seleção de tema e matérias relacionadas
 * - feed: Matérias do feed com extração de tópicos
 * - link: Conteúdo de link com tópicos extraídos
 */

// Tooltip educativo para todas as variantes
const tooltipContent = {
  title: 'Texto-Base',
  icon: '📚',
  items: [
    'Selecione apenas os trechos relevantes para sua matéria',
    'Você pode editar o conteúdo antes de prosseguir',
    'Não se preocupe em deixar perfeito - você poderá adicionar mais contexto na próxima etapa',
    'Quanto mais focado o texto-base, melhor será o resultado da geração da matéria'
  ]
};

const TextoBasePage = () => {
  const navigate = useNavigate();
  const { fonte, confirmarTextoBase, setBlocos, setFonte: _setFonte, textoBase, setVariantSelections } = useCriar();

  // Estado para dados coletados da variante
  const [variantData, setVariantData] = useState(null);
  const [canProceed, setCanProceed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Estado para edição de matérias do tema (fluxo: tema → seleção → edição de tópicos)
  const [temaArticlesForEdit, setTemaArticlesForEdit] = useState(null);

  // Estado para preservar o tema selecionado ao voltar da edição
  const [savedTemaData, setSavedTemaData] = useState(null);

  // Verificar se há fonte selecionada
  useEffect(() => {
    if (!fonte.tipo) {
      // Se não há fonte, redirecionar para etapa 1
      navigate('/criar');
    }
  }, [fonte.tipo, navigate]);

  // Handler para mudanças de dados da variante
  const handleDataChange = useCallback((data) => {
    setVariantData(data);

    // Persist selections to context so they survive navigation
    if (data && (data.selectedTopics || data.editedTexts)) {
      const selections = {
        selectedTopics: data.selectedTopics || [],
        editedTexts: data.editedTexts || {},
        topicTexts: data.topicTexts || {},
      };
      // Cache extracted materias for instant restore on return
      if (data.cachedMaterias) {
        selections.cachedMaterias = data.cachedMaterias;
      }
      setVariantSelections(selections);
    }

    // Verificar se pode prosseguir baseado nos dados
    if (data) {
      const hasSelection = (
        (data.selectedSegments && data.selectedSegments.length > 0) ||
        (data.selectedTopics && data.selectedTopics.length > 0) ||
        (data.selectedTrechos && data.selectedTrechos.length > 0) ||
        (data.selectedArticles && data.selectedArticles.length > 0) ||
        (data.tema && !data.selectedArticles) || // Tema sem matérias (pular)
        (data.wordCount && data.wordCount > 0) ||
        // StoryFusionView data
        (data.groups && data.groups.length > 0) ||
        (data.exclusives && data.exclusives.length > 0) ||
        (data.quotes && data.quotes.length > 0)
      );
      setCanProceed(hasSelection);
    }
  }, [setVariantSelections]);

  // Handler para trocar fonte
  const handleChangeSource = useCallback(() => {
    navigate('/criar');
  }, [navigate]);

  // Handler para pular para configurações (tema sem matérias)
  const handleSkipToConfig = useCallback(() => {
    confirmarTextoBase();
    navigate('/criar/configurar');
  }, [confirmarTextoBase, navigate]);

  // Handler para continuar com matérias do tema (ir para edição de tópicos)
  const handleContinueWithTemaArticles = useCallback((selectedArticles, temaData) => {
    // Salvar dados do tema para restaurar ao voltar
    setSavedTemaData({
      tema: temaData || variantData?.tema,
      selectedArticleIds: selectedArticles.map(a => a.id)
    });

    // Converter matérias do tema para formato compatível com TextoBaseFeed
    const articlesForFeed = selectedArticles.map(article => ({
      id: article.id,
      title: article.title,
      source: article.source,
      sourceUrl: article.sourceUrl,
      category: article.category,
      preview: article.preview,
      content: article.preview,
      wordCount: article.wordCount
    }));

    // Salvar as matérias para edição
    setTemaArticlesForEdit(articlesForFeed);
  }, [variantData]);

  // Handler para voltar da edição de tópicos para seleção de tema
  const handleBackFromTopicEdit = useCallback(() => {
    setTemaArticlesForEdit(null);
  }, []);

  // Handler para continuar
  const handleContinue = useCallback(() => {
    if (!canProceed) return;

    setIsLoading(true);

    // Salvar dados no contexto
    if (variantData) {
      // Converter dados da variante para formato do contexto
      const blocos = [];

      if (variantData.selectedSegments) {
        // Variante de vídeo/transcrição — look up actual text from fonte
        const transcriptionSegments = fonte?.dados?.transcription || [];
        variantData.selectedSegments.forEach((id) => {
          const segment = transcriptionSegments.find(s => s.id === id);
          blocos.push({
            id,
            type: 'transcription',
            content: segment?.text || '',
            highlights: variantData.textHighlights?.[id] || []
          });
        });
      } else if (variantData.selectedTrechos) {
        // Variante de transcrição (YouTube) — edited text or original
        const transcriptionSegments = fonte?.dados?.transcription || [];
        variantData.selectedTrechos.forEach((id) => {
          const segment = transcriptionSegments.find(s => s.id === id);
          blocos.push({
            id,
            type: 'transcription',
            content: variantData.editedTexts?.[id] || segment?.text || ''
          });
        });
      } else if (variantData.groups || variantData.exclusives || variantData.quotes) {
        // StoryFusionView - múltiplas matérias combinadas
        // Extract content from groups (selected versions)
        variantData.groups?.forEach((group, _index) => {
          const version = group.selectedVersion;
          if (version) {
            blocos.push({
              id: `group-${group.id}`,
              type: group.type || 'fato',
              content: version.text || version.content || ''
            });
          }
        });

        // Extract exclusive content
        variantData.exclusives?.forEach((exc, _index) => {
          blocos.push({
            id: `exc-${exc.id}`,
            type: 'exclusivo',
            content: exc.text || exc.content || ''
          });
        });

        // Extract quotes
        variantData.quotes?.forEach((quote, _index) => {
          blocos.push({
            id: `quote-${quote.id}`,
            type: 'citacao',
            content: `"${quote.text}" - ${quote.speaker || quote.source || 'Fonte'}`
          });
        });
      } else if (variantData.selectedTopics) {
        // Variante de link ou feed (single article)
        variantData.selectedTopics.forEach((id, index) => {
          blocos.push({
            id,
            type: 'topic',
            // Use topicTexts (actual content), then editedTexts, then fallback
            content: variantData.topicTexts?.[id] || variantData.editedTexts?.[id] || `Tópico ${index + 1}`
          });
        });
      } else if (variantData.selectedArticles) {
        // Variante de tema
        variantData.selectedArticles.forEach((id, index) => {
          blocos.push({
            id,
            type: 'article',
            content: `Matéria ${index + 1}`
          });
        });
      }

      setBlocos(blocos);
    }

    confirmarTextoBase();

    // Pequeno delay para feedback visual
    setTimeout(() => {
      navigate('/criar/configurar');
    }, 300);
  }, [canProceed, variantData, fonte, setBlocos, confirmarTextoBase, navigate]);

  // Handler para navegação do stepper
  const handleStepClick = useCallback((stepIndex) => {
    const routes = ['/criar', '/criar/texto-base', '/criar/configurar', '/criar/editor'];
    if (stepIndex < 1) {
      navigate(routes[stepIndex]);
    }
  }, [navigate]);

  // Renderizar variante correta baseada no tipo de fonte
  const renderVariant = () => {
    // Se há matérias do tema para editar, mostrar TextoBaseFeed
    if (temaArticlesForEdit && temaArticlesForEdit.length > 0) {
      return (
        <TextoBaseFeed
          fonte={{ tipo: 'tema-articles', dados: temaArticlesForEdit }}
          onChangeSource={handleBackFromTopicEdit}
          onDataChange={handleDataChange}
          savedSelections={textoBase.variantSelections}
        />
      );
    }

    switch (fonte.tipo) {
      case 'video':
      case 'transcription':
        return (
          <TextoBaseVideo
            fonte={fonte}
            onChangeSource={handleChangeSource}
            onDataChange={handleDataChange}
          />
        );
      case 'tema':
        return (
          <TextoBaseTema
            fonte={fonte}
            onChangeSource={handleChangeSource}
            onDataChange={handleDataChange}
            onSkipToConfig={handleSkipToConfig}
            onContinueWithArticles={handleContinueWithTemaArticles}
            initialTemaData={savedTemaData}
          />
        );
      case 'feed':
        return (
          <TextoBaseFeed
            fonte={fonte}
            onChangeSource={handleChangeSource}
            onDataChange={handleDataChange}
            savedSelections={textoBase.variantSelections}
          />
        );
      case 'link':
        return (
          <TextoBaseLink
            fonte={fonte}
            onChangeSource={handleChangeSource}
            onDataChange={handleDataChange}
            savedSelections={textoBase.variantSelections}
          />
        );
      case 'zero':
        return (
          <TextoBaseZero
            fonte={fonte}
            onChangeSource={handleChangeSource}
            onDataChange={handleDataChange}
          />
        );
      default:
        // Fallback - redirecionar para fonte
        return (
          <div className="text-center py-12">
            <p className="text-medium-gray mb-4">Nenhuma fonte selecionada</p>
            <button
              onClick={() => navigate('/criar')}
              className="text-tmc-orange hover:underline"
            >
              Selecionar fonte
            </button>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-off-white">
      {/* Header */}
      <header className="bg-white border-b border-light-gray sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 text-medium-gray hover:text-dark-gray transition-colors"
              aria-label="Voltar para redação"
            >
              <ArrowLeft size={20} />
              <span className="text-sm font-medium hidden sm:inline">Redação</span>
            </button>

            <h1 className="text-lg md:text-xl font-bold text-dark-gray">
              CRIAR NOVA MATÉRIA
            </h1>

            <div className="flex items-center gap-2">
              <TooltipEducativo
                title={tooltipContent.title}
                icon={tooltipContent.icon}
                position="left"
              >
                <p className="font-semibold mb-2">BOAS PRÁTICAS:</p>
                <ul className="space-y-2">
                  {tooltipContent.items.map((item, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-tmc-orange">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </TooltipEducativo>
              <button
                className="flex items-center gap-2 text-medium-gray hover:text-tmc-orange transition-colors"
                aria-label="Ajuda"
              >
                <HelpCircle size={20} />
                <span className="text-sm font-medium hidden sm:inline">Ajuda</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Stepper */}
      <div className="bg-white border-b border-light-gray">
        <div className="max-w-7xl mx-auto px-4 md:px-6">
          <Stepper
            steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
            currentStep={1}
            onStepClick={handleStepClick}
          />
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 md:px-6 py-8">
        {/* Variante */}
        {renderVariant()}

        {/* Navigation Buttons - Ocultar quando tema está na fase de seleção (tem seus próprios botões) */}
        {!(fonte.tipo === 'tema' && !temaArticlesForEdit) && (
          <div className="flex justify-between mt-8">
            <button
              onClick={() => {
                // Se está editando matérias do tema, voltar para seleção de matérias
                if (temaArticlesForEdit) {
                  handleBackFromTopicEdit();
                } else {
                  navigate('/criar');
                }
              }}
              className="flex items-center gap-2 px-6 py-3 border border-light-gray text-medium-gray rounded-lg hover:bg-off-white transition-colors"
            >
              <ArrowLeft size={20} />
              Voltar
            </button>
            <button
              onClick={handleContinue}
              disabled={!canProceed || isLoading}
              className={`
                flex items-center gap-2 px-6 py-3 rounded-lg transition-colors
                ${!canProceed || isLoading
                  ? 'bg-light-gray text-medium-gray cursor-not-allowed'
                  : 'bg-tmc-orange text-white hover:bg-tmc-orange/90'
                }
              `}
            >
              {isLoading ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  Processando...
                </>
              ) : (
                <>
                  Continuar
                  <ArrowRight size={20} />
                </>
              )}
            </button>
          </div>
        )}
      </main>
    </div>
  );
};

export default TextoBasePage;
