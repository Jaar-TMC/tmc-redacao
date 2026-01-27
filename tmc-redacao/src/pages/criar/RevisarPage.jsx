import { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, HelpCircle, FileText, ChevronDown, ChevronUp,
  Link, Youtube, File, User, Palette, Building2, Calendar,
  MessageSquare, Edit, Sparkles, Check, AlertCircle, Tag, X
} from 'lucide-react';
import { Stepper } from '../../components/criar';
import { useCriar } from '../../context';
import { generateArticle } from '../../services/api';

/**
 * RevisarPage - Etapa 3.5 do fluxo de criação de matéria
 *
 * Permite ao usuário revisar todos os conteúdos e configurações
 * antes de gerar a matéria usando IA.
 */

// Fallback mock data when context is empty (for testing)
const mockReviewData = {
  textoBase: {
    type: 'Transcrição YouTube',
    title: 'Entrevista Ministro Economia',
    blocks: 5,
    words: 420,
    content: 'O ministro da economia anunciou hoje em entrevista coletiva que o governo vai implementar novas medidas para conter a inflação nos próximos meses. As medidas foram recebidas com cautela pelo mercado financeiro...'
  },
  materiais: [
    { id: 1, type: 'link', title: 'g1.com/noticia/economia...', words: 320, status: 'extracted' },
    { id: 2, type: 'pdf', title: 'relatorio_trimestral.pdf', pages: 12, words: 3400, status: 'extracted' }
  ],
  configuracoes: {
    categoria: 'Economia',
    tom: 'Didático',
    modoOpinativo: false,
    creditos: 'Agência Brasil',
    dataBase: '18/12/2024',
    orientacaoLide: 'Focar no impacto econômico para o cidadão comum',
    citacoes: 1,
    instrucoes: 'Evitar termos técnicos, manter parágrafos curtos',
    tipoMateria: 'destaque'
  }
};

// Map context categoria to display names
const CATEGORIA_NAMES = {
  esportes: 'Esportes',
  entretenimento: 'Entretenimento',
  politica: 'Política',
  economia: 'Economia',
  geral: 'Geral/Variedades'
};

const TOM_NAMES = {
  informal: 'Informal',
  emocional: 'Emocional',
  sobrio: 'Sóbrio',
  leve: 'Leve',
  criativo: 'Criativo',
  didatico: 'Didático',
  analitico: 'Analítico',
  conversacional: 'Conversacional',
  informativo: 'Informativo'
};

const RevisarPage = () => {
  const navigate = useNavigate();
  const { fonte, textoBase, configuracoes, materiaisComplementares, setResultado, selectedTags, toggleTag, getSelectedTagsArray, getTextoBaseParaGeracao } = useCriar();

  // State
  const [expandedSections, setExpandedSections] = useState({
    textoBase: false,
    materiais: {}
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationMessage, setGenerationMessage] = useState('');
  const [generationError, setGenerationError] = useState(null);

  // Generation messages
  const generationMessages = [
    'Conectando à IA Claude Sonnet 4.5...',
    'Analisando texto-base e fontes complementares...',
    'Identificando informações principais...',
    'Aplicando persona e tom selecionados...',
    'Estruturando lide conforme orientação...',
    'Incorporando citações e declarações...',
    'Gerando parágrafos do corpo da matéria...',
    'Otimizando para legibilidade e SEO...',
    'Finalizando e revisando estrutura...'
  ];

  // Build review data from context or use mock
  const reviewData = useMemo(() => {
    // Handle "Criar do Zero" - text from textoBase.blocos
    if (fonte?.tipo === 'zero') {
      const textoBaseContent = getTextoBaseParaGeracao() || '';
      const wordCount = textoBaseContent.split(/\s+/).filter(Boolean).length;

      return {
        textoBase: {
          type: 'Criar do Zero',
          title: 'Texto Livre',
          blocks: textoBase?.blocos?.length || 1,
          words: wordCount,
          content: textoBaseContent.substring(0, 500) + (textoBaseContent.length > 500 ? '...' : '')
        },
        materiais: [
          ...materiaisComplementares.links.map((l, i) => ({
            id: `link-${i}`, type: 'link', title: l.url || l.title, words: l.words || 0, status: 'extracted'
          })),
          ...materiaisComplementares.pdfs.map((p, i) => ({
            id: `pdf-${i}`, type: 'pdf', title: p.name || p.title, pages: p.pages, words: p.words || 0, status: 'extracted'
          })),
          ...materiaisComplementares.videos.map((v, i) => ({
            id: `video-${i}`, type: 'video', title: v.title || v.url, words: v.words || 0, status: 'extracted'
          }))
        ],
        configuracoes: {
          categoria: CATEGORIA_NAMES[configuracoes.categoria] || configuracoes.categoria || 'Geral/Variedades',
          tom: TOM_NAMES[configuracoes.tom] || configuracoes.tom,
          modoOpinativo: configuracoes.modoOpinativo,
          creditos: configuracoes.creditos || 'Não informado',
          dataBase: configuracoes.data || new Date().toLocaleDateString('pt-BR'),
          orientacaoLide: configuracoes.orientacaoLide || '',
          citacoes: configuracoes.citacoes?.length || 0,
          instrucoes: configuracoes.instrucoes || '',
          tipoMateria: configuracoes.tipoMateria || ''
        },
        _raw: {
          textoBaseContent,
          categoria: configuracoes.categoria,
          tom: configuracoes.tom,
          modoOpinativo: configuracoes.modoOpinativo,
          tipoMateria: configuracoes.tipoMateria,
          citacoes: configuracoes.citacoes,
          contexto: configuracoes.contexto,
          creditos: configuracoes.creditos,
          orientacaoLide: configuracoes.orientacaoLide,
          tags: getSelectedTagsArray()
        }
      };
    }

    // If we have real data from context, use it
    if (fonte?.dados && fonte.dados.length > 0) {
      const articles = fonte.dados;
      const textoBaseContent = textoBase?.textoCompleto ||
        articles.map(a => a.content || a.preview || a.title).join('\n\n');

      const wordCount = textoBaseContent.split(/\s+/).filter(Boolean).length;

      return {
        textoBase: {
          type: fonte.tipo === 'feed' ? 'Matérias do Feed' :
                fonte.tipo === 'link' ? 'Link da Web' :
                fonte.tipo === 'video' ? 'Transcrição de Vídeo' : 'Texto',
          title: articles[0]?.title || 'Texto-base',
          blocks: articles.length,
          words: wordCount,
          content: textoBaseContent.substring(0, 500) + (textoBaseContent.length > 500 ? '...' : '')
        },
        materiais: [
          ...materiaisComplementares.links.map((l, i) => ({
            id: `link-${i}`, type: 'link', title: l.url || l.title, words: l.words || 0, status: 'extracted'
          })),
          ...materiaisComplementares.pdfs.map((p, i) => ({
            id: `pdf-${i}`, type: 'pdf', title: p.name || p.title, pages: p.pages, words: p.words || 0, status: 'extracted'
          })),
          ...materiaisComplementares.videos.map((v, i) => ({
            id: `video-${i}`, type: 'video', title: v.title || v.url, words: v.words || 0, status: 'extracted'
          }))
        ],
        configuracoes: {
          categoria: CATEGORIA_NAMES[configuracoes.categoria] || configuracoes.categoria || 'Geral/Variedades',
          tom: TOM_NAMES[configuracoes.tom] || configuracoes.tom,
          modoOpinativo: configuracoes.modoOpinativo,
          creditos: configuracoes.creditos || 'Não informado',
          dataBase: configuracoes.data || new Date().toLocaleDateString('pt-BR'),
          orientacaoLide: configuracoes.orientacaoLide || '',
          citacoes: configuracoes.citacoes?.length || 0,
          instrucoes: configuracoes.instrucoes || '',
          tipoMateria: configuracoes.tipoMateria || ''
        },
        // Keep raw data for API
        _raw: {
          textoBaseContent,
          categoria: configuracoes.categoria,
          tom: configuracoes.tom,
          modoOpinativo: configuracoes.modoOpinativo,
          tipoMateria: configuracoes.tipoMateria,
          citacoes: configuracoes.citacoes,
          contexto: configuracoes.contexto,
          creditos: configuracoes.creditos,
          orientacaoLide: configuracoes.orientacaoLide,
          tags: getSelectedTagsArray()
        }
      };
    }

    // Fall back to mock data
    return {
      ...mockReviewData,
      configuracoes: {
        ...mockReviewData.configuracoes,
        categoria: 'Geral/Variedades',
        modoOpinativo: false
      },
      _raw: {
        textoBaseContent: mockReviewData.textoBase.content,
        categoria: 'geral',
        tom: 'conversacional',
        modoOpinativo: false,
        tipoMateria: 'destaque',
        citacoes: [],
        contexto: '',
        creditos: mockReviewData.configuracoes.creditos,
        orientacaoLide: mockReviewData.configuracoes.orientacaoLide,
        tags: getSelectedTagsArray()
      }
    };
  }, [fonte, textoBase, configuracoes, materiaisComplementares, getSelectedTagsArray, getTextoBaseParaGeracao]);

  const toggleSection = useCallback((section, id = null) => {
    if (id) {
      setExpandedSections(prev => ({
        ...prev,
        materiais: {
          ...prev.materiais,
          [id]: !prev.materiais[id]
        }
      }));
    } else {
      setExpandedSections(prev => ({
        ...prev,
        [section]: !prev[section]
      }));
    }
  }, []);

  const handleGenerate = useCallback(async () => {
    setIsGenerating(true);
    setGenerationProgress(0);
    setGenerationError(null);
    setGenerationMessage(generationMessages[0]);

    // Progress simulation while API call is in progress
    let progressInterval;
    let currentProgress = 0;

    const startProgressSimulation = () => {
      progressInterval = setInterval(() => {
        currentProgress += Math.random() * 8 + 2; // Slower, more realistic progress
        if (currentProgress > 90) currentProgress = 90; // Cap at 90% until API returns

        setGenerationProgress(currentProgress);
        const messageIndex = Math.floor((currentProgress / 100) * generationMessages.length);
        setGenerationMessage(generationMessages[Math.min(messageIndex, generationMessages.length - 1)]);
      }, 1500);
    };

    try {
      startProgressSimulation();

      // Call the real generation API
      const result = await generateArticle({
        texto_base: reviewData._raw.textoBaseContent,
        categoria: reviewData._raw.categoria || 'geral',
        tom: reviewData._raw.tom || 'conversacional',
        modo_opinativo: reviewData._raw.modoOpinativo || false,
        tipo_materia: reviewData._raw.tipoMateria || 'destaque',
        orientacao_lide: reviewData._raw.orientacaoLide || '',
        citacoes: reviewData._raw.citacoes || [],
        contexto: reviewData._raw.contexto || '',
        creditos: reviewData._raw.creditos || '',
        tags: reviewData._raw.tags || []
      });

      // Stop progress simulation
      clearInterval(progressInterval);

      // Complete progress
      setGenerationProgress(100);
      setGenerationMessage('Matéria gerada com sucesso!');

      // Store result in context
      if (setResultado) {
        setResultado({
          titulo: result.titulo,
          linhaFina: result.linha_fina,
          conteudo: result.conteudo,
          tagsSugeridas: result.tags_sugeridas || [],
          geradoEm: new Date().toISOString()
        });
      }

      // Navigate to editor after brief delay
      setTimeout(() => {
        navigate('/criar/editor');
      }, 500);

    } catch (error) {
      clearInterval(progressInterval);
      console.error('Error generating article:', error);
      setIsGenerating(false);
      setGenerationError(error.message || 'Erro ao gerar matéria. Tente novamente.');
    }
  }, [navigate, generationMessages, reviewData, setResultado]);

  const handleStepClick = useCallback((stepIndex) => {
    const routes = ['/criar', '/criar/texto-base', '/criar/configurar', '/criar/editor'];
    if (stepIndex < 2) {
      navigate(routes[stepIndex]);
    }
  }, [navigate]);

  const totalWords = useMemo(() => {
    return reviewData.textoBase.words +
      reviewData.materiais.reduce((acc, m) => acc + (m.words || 0), 0);
  }, [reviewData]);

  // Generation Overlay
  if (isGenerating) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md px-6">
          {/* Animated Icon */}
          <div className="relative w-28 h-28 mx-auto mb-10">
            {/* Outer ring - slow rotation */}
            <div className="absolute inset-0 border-4 border-tmc-orange/20 rounded-full animate-spin" style={{ animationDuration: '3s' }} />
            {/* Middle ring - pulse */}
            <div className="absolute inset-2 bg-tmc-orange/10 rounded-full animate-ping" style={{ animationDuration: '2s' }} />
            {/* Inner circle - breathing */}
            <div className="absolute inset-4 bg-gradient-to-br from-tmc-orange to-orange-600 rounded-full flex items-center justify-center shadow-lg shadow-tmc-orange/30">
              <Sparkles className="w-10 h-10 text-white animate-pulse" />
            </div>
          </div>

          <h2 className="text-2xl font-bold text-white mb-3">
            Gerando sua matéria...
          </h2>

          <p className="text-gray-300 mb-8 min-h-[48px] leading-relaxed">
            {generationMessage}
          </p>

          {/* Progress Bar */}
          <div className="w-full bg-gray-700/50 rounded-full h-3 mb-4 overflow-hidden">
            <div
              className="bg-gradient-to-r from-tmc-orange to-orange-500 h-3 rounded-full transition-all duration-500 relative"
              style={{ width: `${generationProgress}%` }}
            >
              {/* Shimmer effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
            </div>
          </div>

          <div className="flex items-center justify-center gap-3 text-sm">
            <span className="text-white font-semibold">{Math.round(generationProgress)}%</span>
            <span className="text-gray-400">•</span>
            <span className="text-gray-400">Tempo estimado: ~25 segundos</span>
          </div>

          {/* Progress Steps Indicator */}
          <div className="mt-8 flex justify-center gap-2">
            {generationMessages.slice(0, 8).map((_, index) => (
              <div
                key={index}
                className={`w-2 h-2 rounded-full transition-all duration-300 ${
                  index <= Math.floor((generationProgress / 100) * 8)
                    ? 'bg-tmc-orange scale-110'
                    : 'bg-gray-600'
                }`}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error state display
  const ErrorAlert = generationError && (
    <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-start gap-3">
      <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm font-medium text-red-800">Erro ao gerar matéria</p>
        <p className="text-sm text-red-600 mt-1">{generationError}</p>
      </div>
      <button
        onClick={() => setGenerationError(null)}
        className="text-red-400 hover:text-red-600"
      >
        ×
      </button>
    </div>
  );

  return (
    <div className="min-h-screen bg-off-white">
      <div className="max-w-5xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-medium-gray hover:text-dark-gray transition-colors"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">Redação</span>
          </button>

          <h1 className="text-xl font-bold text-dark-gray uppercase tracking-wide">
            Criar Nova Matéria
          </h1>

          <button
            className="flex items-center gap-2 text-medium-gray hover:text-tmc-orange transition-colors"
            aria-label="Ajuda"
          >
            <HelpCircle size={20} />
            <span className="text-sm font-medium hidden sm:inline">Help</span>
          </button>
        </div>

        {/* Stepper */}
        <Stepper
          steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
          currentStep={2}
          onStepClick={handleStepClick}
        />

        {/* Error Alert */}
        {ErrorAlert}

        {/* Review Header */}
        <div className="bg-gradient-to-r from-tmc-orange to-orange-600 text-white rounded-xl p-6 mb-6">
          <div className="flex items-center gap-3 mb-2">
            <FileText size={24} />
            <h2 className="text-xl font-bold">Revisão Final</h2>
          </div>
          <p className="text-white/80">
            Confira tudo que será usado na geração da matéria
          </p>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Left Column - Contents (2/3 width) */}
          <div className="lg:col-span-2 space-y-4">
            <h3 className="text-sm font-semibold text-medium-gray uppercase tracking-wide">
              Conteúdos Selecionados
            </h3>

            {/* Texto-Base Card */}
            <div className="bg-white border border-light-gray rounded-xl overflow-hidden">
              <button
                onClick={() => toggleSection('textoBase')}
                className="w-full flex items-center justify-between p-4 hover:bg-off-white/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-tmc-orange/10 rounded-lg flex items-center justify-center">
                    <FileText size={20} className="text-tmc-orange" />
                  </div>
                  <div className="text-left">
                    <p className="font-semibold text-dark-gray">TEXTO-BASE</p>
                    <p className="text-sm text-medium-gray">{reviewData.textoBase.type}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm text-dark-gray">{reviewData.textoBase.blocks} blocos</p>
                    <p className="text-xs text-medium-gray">~{reviewData.textoBase.words} palavras</p>
                  </div>
                  {expandedSections.textoBase ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </div>
              </button>

              {expandedSections.textoBase && (
                <div className="border-t border-light-gray p-4 bg-off-white/30">
                  <p className="text-sm text-dark-gray leading-relaxed mb-4">
                    {reviewData.textoBase.content}
                  </p>
                  <button
                    onClick={() => navigate('/criar/texto-base')}
                    className="flex items-center gap-2 text-sm text-tmc-orange hover:underline"
                  >
                    <Edit size={14} />
                    Editar texto-base
                  </button>
                </div>
              )}
            </div>

            {/* Materiais Cards */}
            {reviewData.materiais.map(material => (
              <div key={material.id} className="bg-white border border-light-gray rounded-xl overflow-hidden">
                <button
                  onClick={() => toggleSection('materiais', material.id)}
                  className="w-full flex items-center justify-between p-4 hover:bg-off-white/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      material.type === 'link' ? 'bg-blue-50' :
                      material.type === 'video' ? 'bg-red-50' : 'bg-orange-50'
                    }`}>
                      {material.type === 'link' ? <Link size={20} className="text-blue-500" /> :
                       material.type === 'video' ? <Youtube size={20} className="text-red-500" /> :
                       <File size={20} className="text-orange-500" />}
                    </div>
                    <div className="text-left">
                      <p className="font-semibold text-dark-gray uppercase text-sm">
                        {material.type === 'link' ? 'Link Complementar' :
                         material.type === 'video' ? 'Vídeo YouTube' : 'PDF Anexado'}
                      </p>
                      <p className="text-sm text-medium-gray truncate max-w-[200px]">{material.title}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      {material.pages && <p className="text-sm text-dark-gray">{material.pages} págs</p>}
                      <p className="text-xs text-medium-gray">~{material.words} palavras</p>
                    </div>
                    <span className="text-xs text-green-600 flex items-center gap-1">
                      <Check size={12} /> Extraído
                    </span>
                    {expandedSections.materiais[material.id] ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </div>
                </button>

                {expandedSections.materiais[material.id] && (
                  <div className="border-t border-light-gray p-4 bg-off-white/30">
                    <p className="text-sm text-medium-gray mb-4">
                      Conteúdo extraído de {material.title}. Clique em editar para selecionar trechos específicos.
                    </p>
                    <div className="flex gap-4">
                      <button className="flex items-center gap-2 text-sm text-tmc-orange hover:underline">
                        <Edit size={14} />
                        Selecionar trechos
                      </button>
                      <button className="flex items-center gap-2 text-sm text-red-500 hover:underline">
                        Remover
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {/* Summary */}
            <div className="bg-off-white rounded-xl p-4">
              <p className="text-sm text-medium-gray">
                <strong className="text-dark-gray">Total de conteúdo de referência:</strong>{' '}
                ~{totalWords.toLocaleString()} palavras
              </p>
              <p className="text-sm text-medium-gray mt-1">
                <strong className="text-dark-gray">Fontes:</strong>{' '}
                {1 + mockReviewData.materiais.length} (texto-base + {reviewData.materiais.length} complementares)
              </p>
            </div>
          </div>

          {/* Right Column - Configurations (1/3 width) */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-medium-gray uppercase tracking-wide">
              Configurações
            </h3>

            <div className="bg-white border border-light-gray rounded-xl p-4 space-y-4">
              <div className="flex items-center gap-3">
                <User size={18} className="text-tmc-orange" />
                <div>
                  <p className="text-xs text-medium-gray">Categoria Editorial</p>
                  <p className="text-sm font-medium text-dark-gray">{reviewData.configuracoes.categoria}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Palette size={18} className="text-tmc-orange" />
                <div>
                  <p className="text-xs text-medium-gray">Tom</p>
                  <p className="text-sm font-medium text-dark-gray">{reviewData.configuracoes.tom}</p>
                </div>
              </div>

              {reviewData.configuracoes.modoOpinativo && (
                <div className="flex items-center gap-3">
                  <MessageSquare size={18} className="text-orange-500" />
                  <div>
                    <p className="text-xs text-medium-gray">Modo</p>
                    <p className="text-sm font-medium text-orange-600">Opinativo Ativo</p>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3">
                <Building2 size={18} className="text-tmc-orange" />
                <div>
                  <p className="text-xs text-medium-gray">Créditos</p>
                  <p className="text-sm font-medium text-dark-gray">{reviewData.configuracoes.creditos}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Calendar size={18} className="text-tmc-orange" />
                <div>
                  <p className="text-xs text-medium-gray">Data base</p>
                  <p className="text-sm font-medium text-dark-gray">{reviewData.configuracoes.dataBase}</p>
                </div>
              </div>

              <div className="border-t border-light-gray pt-4">
                <div className="flex items-start gap-3">
                  <FileText size={18} className="text-tmc-orange mt-0.5" />
                  <div>
                    <p className="text-xs text-medium-gray">Orientação do lide</p>
                    <p className="text-sm text-dark-gray">&quot;{reviewData.configuracoes.orientacaoLide}&quot;</p>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <MessageSquare size={18} className="text-tmc-orange" />
                <div>
                  <p className="text-xs text-medium-gray">Citações</p>
                  <p className="text-sm font-medium text-dark-gray">{reviewData.configuracoes.citacoes} citação adicionada</p>
                </div>
              </div>

              {reviewData.configuracoes.instrucoes && (
                <div className="border-t border-light-gray pt-4">
                  <div className="flex items-start gap-3">
                    <Edit size={18} className="text-tmc-orange mt-0.5" />
                    <div>
                      <p className="text-xs text-medium-gray">Instruções</p>
                      <p className="text-sm text-dark-gray">&quot;{reviewData.configuracoes.instrucoes}&quot;</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Tags SEO Section */}
              {selectedTags && selectedTags.size > 0 && (
                <div className="border-t border-light-gray pt-4">
                  <div className="flex items-start gap-3">
                    <Tag size={18} className="text-tmc-orange mt-0.5" />
                    <div className="flex-1">
                      <p className="text-xs text-medium-gray mb-2">Tags para SEO ({selectedTags.size})</p>
                      <div className="flex flex-wrap gap-1.5">
                        {Array.from(selectedTags).map(tag => (
                          <button
                            key={tag}
                            onClick={() => toggleTag(tag)}
                            className="text-xs bg-tmc-orange text-white px-2 py-1 rounded-full flex items-center gap-1 hover:bg-tmc-orange/80 transition-colors"
                            title={`Remover tag "${tag}"`}
                          >
                            #{tag}
                            <X size={10} />
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <button
                onClick={() => navigate('/criar/configurar')}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-tmc-orange border border-tmc-orange rounded-lg hover:bg-orange-50 transition-colors"
              >
                <Edit size={14} />
                Editar Configurações
              </button>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="bg-white border border-light-gray rounded-xl p-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <button
              onClick={() => navigate('/criar/texto-base')}
              className="flex items-center gap-2 px-6 py-3 text-medium-gray hover:text-dark-gray transition-colors"
            >
              <ArrowLeft size={20} />
              Editar Conteúdos
            </button>

            <button
              onClick={handleGenerate}
              className="flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-tmc-orange to-orange-600 text-white rounded-xl hover:shadow-lg hover:scale-105 transition-all font-semibold text-lg"
            >
              <Sparkles size={24} />
              GERAR MATÉRIA
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RevisarPage;
