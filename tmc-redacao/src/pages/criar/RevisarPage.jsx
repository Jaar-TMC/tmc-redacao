import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, HelpCircle, FileText, ChevronDown, ChevronUp,
  Link, Youtube, File, User, Palette, Building2, Calendar,
  MessageSquare, Edit, Sparkles, Check, AlertCircle, Tag, X,
  Search, ShieldCheck, CheckCircle2
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
  const [currentPhase, setCurrentPhase] = useState(0);
  const [generationError, setGenerationError] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const phaseTimerRef = useRef(null);
  const elapsedTimerRef = useRef(null);
  const isGeneratingRef = useRef(false);

  // Pipeline phases with realistic timing based on production measurements
  const PHASES = useMemo(() => [
    { id: 'enrichment', label: 'Enriquecimento', description: 'Buscando fontes e verificando fatos...', Icon: Search, targetProgress: 15, durationMs: 15000 },
    { id: 'generation', label: 'Geração', description: 'Escrevendo matéria com IA...', Icon: Sparkles, targetProgress: 45, durationMs: 40000 },
    { id: 'verification', label: 'Verificação', description: 'Conferindo claims e informações...', Icon: ShieldCheck, targetProgress: 65, durationMs: 30000 },
    { id: 'refinement', label: 'Refinamento', description: 'Corrigindo e aprimorando automaticamente...', Icon: Sparkles, targetProgress: 85, durationMs: 40000 },
    { id: 'finishing', label: 'Finalização', description: 'Aplicando SEO e revisão final...', Icon: CheckCircle2, targetProgress: 95, durationMs: 10000 },
  ], []);

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
    // Support both array (feed) and object (tema, link, video, prompt) fonte.dados
    const hasFonteDados = fonte?.dados && (
      Array.isArray(fonte.dados) ? fonte.dados.length > 0 : Object.keys(fonte.dados).length > 0
    );
    if (hasFonteDados) {
      const articles = Array.isArray(fonte.dados) ? fonte.dados : [];
      // Build texto_base from multiple sources, preferring the richest content.
      // blocos: curated topic text assembled by TextoBasePage (from AI extraction)
      // rawArticleText: full article content from fonte.dados (original RSS content)
      // textoCompleto: manual text editing mode (rarely used)
      // The generation API requires >= 300 chars (MIN_SOURCE_CHARS).
      // Use blocos when available; fall back to raw article content if blocos are
      // too short (topic extraction summarizes, so extracted text can be < 300 chars
      // even when the source article has 3000+ chars).
      const blocosText = getTextoBaseParaGeracao();
      const rawArticleText = articles.length > 0
        ? articles.map(a => a.content || a.preview || a.title).join('\n\n')
        : '';
      let textoBaseContent = textoBase?.textoCompleto || blocosText || rawArticleText;
      // Safety net: if assembled text is below minimum but raw content is longer, use raw
      if (textoBaseContent.length < 300 && rawArticleText.length > textoBaseContent.length) {
        textoBaseContent = rawArticleText;
      }

      const wordCount = textoBaseContent.split(/\s+/).filter(Boolean).length;

      return {
        textoBase: {
          type: fonte.tipo === 'feed' ? 'Matérias do Feed' :
                fonte.tipo === 'link' ? 'Link da Web' :
                fonte.tipo === 'video' ? 'Transcrição de Vídeo' :
                fonte.tipo === 'tema' ? 'Tema em Alta' :
                fonte.tipo === 'transcription' ? 'Transcrição de Vídeo' : 'Texto',
          title: articles[0]?.title || fonte.dados?.title || fonte.dados?.url || 'Texto-base',
          blocks: articles.length || textoBase?.blocos?.length || 1,
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

    // Fallback for non-array fonte types (transcription, link, tema, etc.)
    // Use blocos assembled by TextoBasePage → getTextoBaseParaGeracao()
    const textoBaseContent = getTextoBaseParaGeracao() || '';
    if (!textoBaseContent) return null;

    const wordCount = textoBaseContent.split(/\s+/).filter(Boolean).length;
    const fonteLabel = fonte?.tipo === 'transcription' ? 'Transcrição de Vídeo'
      : fonte?.tipo === 'link' ? 'Link da Web'
      : fonte?.tipo === 'tema' ? 'Tema'
      : fonte?.tipo === 'prompt' ? 'Pesquisa na Web'
      : 'Texto';
    const fonteTitle = fonte?.tipo === 'transcription'
      ? (fonte.dados?.video?.title || 'Vídeo do YouTube')
      : (fonte.dados?.title || fonte.dados?.url || 'Texto-base');

    return {
      textoBase: {
        type: fonteLabel,
        title: fonteTitle,
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
    if (isGeneratingRef.current) return;
    isGeneratingRef.current = true;
    if (!reviewData) { isGeneratingRef.current = false; return; }

    setIsGenerating(true);
    setGenerationProgress(0);
    setCurrentPhase(0);
    setGenerationError(null);
    setElapsedSeconds(0);

    // Phase-aware progress simulation based on real pipeline timing
    let phase = 0;
    let phaseStart = Date.now();
    const pipelineStart = Date.now();

    const startProgressSimulation = () => {
      // Elapsed timer (updates every second)
      elapsedTimerRef.current = setInterval(() => {
        setElapsedSeconds(Math.floor((Date.now() - pipelineStart) / 1000));
      }, 1000);

      // Phase progress timer (smooth 100ms updates)
      phaseTimerRef.current = setInterval(() => {
        if (phase >= PHASES.length) return;

        const p = PHASES[phase];
        const prevTarget = phase > 0 ? PHASES[phase - 1].targetProgress : 0;
        const elapsed = Date.now() - phaseStart;
        const phaseFraction = Math.min(elapsed / p.durationMs, 1);
        // Ease-out curve for natural feel
        const eased = 1 - Math.pow(1 - phaseFraction, 2);
        const progress = prevTarget + eased * (p.targetProgress - prevTarget);

        setGenerationProgress(Math.min(progress, 95)); // Cap at 95% until API returns

        // Move to next phase when current phase duration elapsed
        if (elapsed >= p.durationMs && phase < PHASES.length - 1) {
          phase++;
          phaseStart = Date.now();
          setCurrentPhase(phase);
        }
      }, 100);
    };

    try {
      startProgressSimulation();

      // Get source title for enrichment search
      const tituloFonte = fonte?.dados?.[0]?.title || reviewData.textoBase.title || '';

      // Prompt metadata from variant selections (if prompt source)
      const promptMeta = textoBase?.variantSelections?.promptMeta;

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
        tags: reviewData._raw.tags || [],
        titulo_fonte: tituloFonte,
        source_type: promptMeta?.source_type || 'manual',
        research_prompt: promptMeta?.research_prompt || null,
        research_source_urls: promptMeta?.research_source_urls || [],
      });

      // Stop progress simulation
      clearInterval(phaseTimerRef.current);
      clearInterval(elapsedTimerRef.current);

      // Complete progress
      setGenerationProgress(100);
      setCurrentPhase(PHASES.length); // All phases done

      // Store result in context (including verification data)
      if (setResultado) {
        setResultado({
          titulo: result.titulo,
          tituloCurto: result.titulo_curto || '',
          linhaFina: result.linha_fina,
          resumo: result.resumo || [],
          conteudo: result.conteudo,
          tagsSugeridas: result.tags_sugeridas || [],
          geradoEm: new Date().toISOString(),
          // Anti-hallucination verification data
          verification: result.verification || null,
          riskLevel: result.verification?.risk_level || null,
          publishBlocked: result.publish_blocked || false,
          blockReason: result.block_reason || null,
          materialSufficiency: result.material_sufficiency || null,
          humanReviewRequired: result.human_review_required || false,
          reviewReasons: result.review_reasons || [],
          // v7: editorial gates
          publicationStatus: result.publication_status || null,
          readability: result.readability || null,
          enrichmentDegraded: result.enrichment_degraded || false,
          slugSugerido: result.slug_sugerido || null,
          sourceUrls: result.source_urls || [],
          // v7.1: additional pipeline fields
          schemaOrg: result.schema_org || null,
          aiDisclosure: result.ai_disclosure || null,
          sensitiveTopicsDetected: result.sensitive_topics_detected || false,
          sensitiveInstructions: result.sensitive_instructions || [],
          notaForced: result.nota_forced || false,
          notaDisclaimer: result.nota_disclaimer || null,
          regenerated: result.regenerated || false,
          regenerationImprovement: result.regeneration_improvement || null,
          correlationId: result.correlation_id || null,
          // Quality Loop result
          qualityLoop: result.quality_loop || null,
        });
      }

      // Navigate to editor after brief delay
      setTimeout(() => {
        navigate('/criar/editor');
      }, 500);

    } catch (error) {
      clearInterval(phaseTimerRef.current);
      clearInterval(elapsedTimerRef.current);
      console.error('Error generating article:', error);
      setIsGenerating(false);
      setGenerationError(error.message || 'Erro ao gerar matéria. Tente novamente.');
    } finally {
      isGeneratingRef.current = false;
    }
  }, [navigate, PHASES, reviewData, setResultado, fonte?.dados, textoBase?.variantSelections?.promptMeta]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      clearInterval(phaseTimerRef.current);
      clearInterval(elapsedTimerRef.current);
    };
  }, []);

  const handleStepClick = useCallback((stepIndex) => {
    const routes = ['/criar', '/criar/texto-base', '/criar/configurar', '/criar/editor'];
    if (stepIndex < 2) {
      navigate(routes[stepIndex]);
    }
  }, [navigate]);

  const totalWords = useMemo(() => {
    if (!reviewData) return 0;
    return reviewData.textoBase.words +
      reviewData.materiais.reduce((acc, m) => acc + (m.words || 0), 0);
  }, [reviewData]);

  // Guard: redirect to /criar if no valid data
  if (!reviewData && fonte?.tipo !== 'zero') {
    navigate('/criar', { replace: true });
    return null;
  }

  // Generation Overlay — phase-based progress
  if (isGenerating) {
    const activePhase = PHASES[Math.min(currentPhase, PHASES.length - 1)];
    const ActiveIcon = activePhase.Icon;

    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="w-full max-w-lg px-6">
          {/* Active phase icon */}
          <div className="relative w-24 h-24 mx-auto mb-8">
            <div className="absolute inset-0 border-4 border-tmc-orange/20 rounded-full animate-spin" style={{ animationDuration: '3s' }} />
            <div className="absolute inset-3 bg-gradient-to-br from-tmc-orange to-orange-600 rounded-full flex items-center justify-center shadow-lg shadow-tmc-orange/30">
              <ActiveIcon className="w-9 h-9 text-white animate-pulse" />
            </div>
          </div>

          <h2 className="text-2xl font-bold text-white text-center mb-2">
            {currentPhase >= PHASES.length ? 'Matéria gerada!' : activePhase.description}
          </h2>

          <p className="text-gray-400 text-sm text-center mb-10">
            {elapsedSeconds}s decorridos
          </p>

          {/* Phase steps */}
          <div className="space-y-3 mb-10">
            {PHASES.map((phase, idx) => {
              const PhaseIcon = phase.Icon;
              const isCompleted = idx < currentPhase;
              const isActive = idx === currentPhase && currentPhase < PHASES.length;
              const _isPending = idx > currentPhase;

              return (
                <div
                  key={phase.id}
                  className={`flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-500 ${
                    isActive
                      ? 'bg-tmc-orange/10 border border-tmc-orange/30'
                      : isCompleted
                        ? 'bg-green-500/5 border border-green-500/10'
                        : 'bg-gray-800/30 border border-gray-700/30'
                  }`}
                >
                  {/* Phase icon / check */}
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-500 ${
                    isActive
                      ? 'bg-tmc-orange/20'
                      : isCompleted
                        ? 'bg-green-500/20'
                        : 'bg-gray-700/40'
                  }`}>
                    {isCompleted ? (
                      <Check className="w-5 h-5 text-green-400" />
                    ) : (
                      <PhaseIcon className={`w-5 h-5 transition-all ${
                        isActive ? 'text-tmc-orange animate-pulse' : 'text-gray-500'
                      }`} />
                    )}
                  </div>

                  {/* Label */}
                  <div className="flex-1 min-w-0">
                    <span className={`text-sm font-medium transition-all ${
                      isActive ? 'text-white' : isCompleted ? 'text-green-400/80' : 'text-gray-500'
                    }`}>
                      {phase.label}
                    </span>
                    {isActive && (
                      <p className="text-xs text-gray-400 mt-0.5">{phase.description}</p>
                    )}
                  </div>

                  {/* Status */}
                  <div className="flex-shrink-0">
                    {isActive && (
                      <div className="flex gap-1">
                        <span className="w-1.5 h-1.5 bg-tmc-orange rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 bg-tmc-orange rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 bg-tmc-orange rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    )}
                    {isCompleted && (
                      <span className="text-xs text-green-400/60">OK</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-700/40 rounded-full h-2 mb-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-tmc-orange to-orange-500 h-2 rounded-full transition-all duration-300 relative"
              style={{ width: `${generationProgress}%` }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
            </div>
          </div>

          <p className="text-center text-xs text-gray-500">
            {Math.round(generationProgress)}% concluído
          </p>

          <p className="text-center text-xs text-gray-500 mt-6">
            Não atualize ou saia da página durante a geração.
          </p>
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
            <span className="text-sm font-medium hidden sm:inline">Ajuda</span>
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

        {/* Prompt source badge */}
        {fonte?.tipo === 'prompt' && (
          <div className="flex items-center gap-2 text-sm text-tmc-orange font-medium mb-4">
            <Search size={14} />
            <span>Fonte: Pesquisa na Web ({textoBase?.variantSelections?.promptMeta?.source_count || 0} fontes)</span>
          </div>
        )}

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
                {1 + reviewData.materiais.length} (texto-base + {reviewData.materiais.length} complementares)
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
                  <p className="text-xs text-medium-gray">Estilo Editorial</p>
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
