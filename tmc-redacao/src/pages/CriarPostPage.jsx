import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Sparkles,
  UserCircle,
  SpellCheck,
  Languages,
  BarChart3,
  Lightbulb,
  Send,
  Trash2,
  Bot,
  ChevronDown,
  Newspaper,
  Flame,
  X,
  Link2,
  Tag,
  Plus,
  Loader2,
  Copy,
  Check,
  Eye,
  Edit3,
  FileText,
  Save,
  Code,
  AlertTriangle
} from 'lucide-react';
import { countWords, markdownToHtml } from '../utils/markdownRenderer';
import { mockTones, mockPersonas } from '../data/mockData';
import Tooltip from '../components/ui/Tooltip';
import { SEOAnalyzerPanel, calculateSEOScore, RichTextEditor, EditorToolbar } from '../components/editor';
import { useCriar } from '../context';
import { useVersionHistory, useChatEditor } from '../hooks';
import { createUserArticle, updateUserArticle, getUserArticle, generateTags, editArticle } from '../services/api';
import { generateSEOOptimizationPrompt } from '../utils/seoPromptGenerator';

// Tipos de matéria disponíveis
const articleTypes = [
  { id: 'destaque', name: 'Destaque Principal', description: 'Matéria principal da home' },
  { id: 'principal-secao', name: 'Principal da Seção', description: 'Destaque dentro de uma editoria' },
  { id: 'secundaria', name: 'Secundária da Seção', description: 'Matéria de apoio na editoria' },
  { id: 'coluna', name: 'Coluna', description: 'Texto opinativo ou de colunista' },
  { id: 'mais-lidas', name: 'Mais Lidas', description: 'Conteúdo para seção popular' },
  { id: 'original', name: 'Conteúdo Original', description: 'Reportagem exclusiva' },
  { id: 'servico', name: 'Serviço', description: 'Informação útil ao leitor' }
];

const CriarPostPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { articleId: editArticleId } = useParams(); // For editing existing articles
  const { resultado } = useCriar();

  // State for loading existing article
  const [isLoadingArticle, setIsLoadingArticle] = useState(false);
  const [loadedArticle, setLoadedArticle] = useState(null);

  // Extrair parâmetros da URL (vindos da tela de seleção de tema)
  const themeContext = useMemo(() => {
    const tema = searchParams.get('tema');
    const fonte = searchParams.get('fonte');
    const linksParam = searchParams.get('links');
    const instrucoes = searchParams.get('instrucoes');
    const tipo = searchParams.get('tipo');

    return {
      tema,
      fonte,
      links: linksParam ? JSON.parse(linksParam) : [],
      instrucoes,
      tipo
    };
  }, [searchParams]);

  // Mock data para demonstração - matéria bem formatada com boa nota SEO
  const mockArticle = {
    title: 'Brasil bate recorde histórico em exportações de soja em 2024',
    linhaFina: 'País consolida liderança mundial no mercado de commodities agrícolas com aumento de 15% nas vendas externas e perspectivas otimistas para o segundo semestre',
    content: `O Brasil alcançou um marco histórico nas exportações de soja em 2024, consolidando sua posição como principal fornecedor global do grão. Os dados divulgados pelo Ministério da Agricultura mostram que o país exportou mais de 100 milhões de toneladas no primeiro semestre, um aumento de 15% em relação ao mesmo período do ano anterior.

A demanda aquecida da China, principal compradora da soja brasileira, foi um dos fatores determinantes para esse resultado expressivo. O país asiático adquiriu aproximadamente 70% de toda a produção exportada pelo Brasil, fortalecendo ainda mais as relações comerciais entre as duas nações.

Especialistas do setor apontam que a combinação de condições climáticas favoráveis nas principais regiões produtoras, como Mato Grosso, Goiás e Paraná, aliada aos investimentos em tecnologia agrícola, foram fundamentais para o aumento da produtividade. A safra 2023/2024 registrou média de 3,5 toneladas por hectare, superando as expectativas iniciais dos analistas.

O impacto econômico dessas exportações é significativo para a balança comercial brasileira. O agronegócio continua sendo o principal pilar das exportações nacionais, representando mais de 40% do total exportado pelo país. Os recursos gerados beneficiam não apenas o setor agrícola, mas toda a cadeia produtiva, incluindo transporte, logística e serviços.

Para o segundo semestre, as projeções indicam manutenção do ritmo positivo. Analistas estimam que o Brasil pode encerrar 2024 com exportações superiores a 150 milhões de toneladas, estabelecendo um novo recorde absoluto na história do país.

A diversificação dos mercados compradores também contribui para essa perspectiva otimista. Além da China, países do Oriente Médio e da África têm aumentado significativamente suas compras de soja brasileira, reduzindo a dependência de um único mercado.

O governo federal anunciou medidas para apoiar os produtores rurais, incluindo linhas de crédito com juros reduzidos e programas de incentivo à sustentabilidade. A meta é garantir que o crescimento do setor ocorra de forma responsável, respeitando os compromissos ambientais assumidos internacionalmente.

Com esse desempenho, o Brasil reafirma sua posição estratégica no cenário global de commodities e projeta um futuro promissor para o agronegócio nacional.`,
    tags: ['Agronegócio', 'Exportações', 'Soja', 'Economia', 'Brasil']
  };

  // Load article data when editing
  useEffect(() => {
    const loadArticle = async () => {
      if (!editArticleId) return;

      setIsLoadingArticle(true);
      try {
        const article = await getUserArticle(editArticleId);
        setLoadedArticle(article);
        setArticleId(editArticleId); // Set the articleId for saving
      } catch (err) {
        console.error('Error loading article:', err);
        setSaveError('Erro ao carregar matéria para edição');
      } finally {
        setIsLoadingArticle(false);
      }
    };

    loadArticle();
  }, [editArticleId]);

  // Use loaded article, resultado from context, or fall back to mock data
  const initialTitle = loadedArticle?.title || resultado?.titulo || mockArticle.title;
  const initialLinhaFina = loadedArticle?.linhaFina || resultado?.linhaFina || mockArticle.linhaFina;
  const initialContent = loadedArticle?.content || resultado?.conteudo || mockArticle.content;
  // Ensure initialTags is always an array
  const rawTags = loadedArticle?.tags || resultado?.tagsSugeridas || mockArticle.tags;
  const initialTags = Array.isArray(rawTags) ? rawTags : [];

  // Update state when loaded article changes
  useEffect(() => {
    if (loadedArticle) {
      setTitle(loadedArticle.title || '');
      setLinhaFina(loadedArticle.linhaFina || '');
      setContent(loadedArticle.content || '');
      setTags(Array.isArray(loadedArticle.tags) ? loadedArticle.tags : []);
    }
  }, [loadedArticle]);

  // Version history for undo/redo support
  const {
    currentContent,
    canUndo,
    canRedo,
    undo,
    redo,
    pushVersion,
    updateCurrentContent,
    resetHistory,
    versionCount,
    versions,
    currentIndex,
    goToVersion
  } = useVersionHistory({
    title: initialTitle,
    linhaFina: initialLinhaFina,
    body: initialContent,
    tags: initialTags
  });

  // Local state synced with version history
  const [title, setTitle] = useState(currentContent?.title || '');
  const [linhaFina, setLinhaFina] = useState(currentContent?.linhaFina || '');
  const [content, setContent] = useState(currentContent?.body || '');
  const [tags, setTags] = useState(Array.isArray(currentContent?.tags) ? currentContent.tags : []);

  // Sync local state when version changes (undo/redo)
  useEffect(() => {
    if (currentContent) {
      setTitle(currentContent.title || '');
      setLinhaFina(currentContent.linhaFina || '');
      setContent(currentContent.body || '');
      setTags(Array.isArray(currentContent.tags) ? currentContent.tags : []);
    }
  }, [currentContent]);

  const [selectedTone, setSelectedTone] = useState(null);
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [selectedArticleType, setSelectedArticleType] = useState(null);
  const [openDropdown, setOpenDropdown] = useState(null);
  const [spellCheck, setSpellCheck] = useState(false);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [showCopyDropdown, setShowCopyDropdown] = useState(false);
  const [copyType, setCopyType] = useState(null); // 'html' or 'text'
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const [showVersionDropdown, setShowVersionDropdown] = useState(false);
  const [isGeneratingTitle, setIsGeneratingTitle] = useState(false);

  // Rich text editor ref
  const editorRef = useRef(null);

  // Persistence state
  const [articleId, setArticleId] = useState(null);
  const [saveError, setSaveError] = useState(null);
  const [lastSavedAt, setLastSavedAt] = useState(null);

  // Update state when resultado changes (e.g., when navigating from RevisarPage)
  useEffect(() => {
    if (resultado?.geradoEm) {
      // Ensure tags is always an array
      const resultTags = Array.isArray(resultado.tagsSugeridas) ? resultado.tagsSugeridas : [];
      const newTags = resultTags.length > 0 ? resultTags : tags;
      // Convert markdown content to HTML for TipTap editor
      const htmlContent = markdownToHtml(resultado.conteudo || '');
      // Reset version history with new content
      resetHistory({
        title: resultado.titulo || '',
        linhaFina: resultado.linhaFina || '',
        body: htmlContent,
        tags: Array.isArray(newTags) ? newTags : []
      });
    }
  }, [resultado?.geradoEm, resetHistory]);
  const [newTagInput, setNewTagInput] = useState('');
  const [isGeneratingTags, setIsGeneratingTags] = useState(false);

  // Estado para controlar a aba ativa do painel lateral (assistente ou seo)
  const [activeSidebarTab, setActiveSidebarTab] = useState('assistente');

  // Mensagem inicial baseada no contexto do tema
  const getInitialMessages = () => {
    if (themeContext.tema) {
      const messages = [
        {
          id: 1,
          type: 'ai',
          content: `Olá! Vejo que você quer criar uma matéria sobre **"${themeContext.tema}"**. Estou pronto para ajudar!`
        }
      ];

      if (themeContext.links?.length > 0) {
        messages.push({
          id: 2,
          type: 'ai',
          content: `📎 Você forneceu ${themeContext.links.length} link(s) de referência. Vou usar essas fontes como base para sugestões.`
        });
      }

      if (themeContext.instrucoes) {
        messages.push({
          id: messages.length + 1,
          type: 'ai',
          content: `📝 Suas instruções: "${themeContext.instrucoes}"\n\nVou considerar isso ao fazer sugestões. Como deseja começar?`
        });
      } else {
        messages.push({
          id: messages.length + 1,
          type: 'ai',
          content: 'Como deseja começar? Posso sugerir uma introdução, pesquisar dados atuais sobre o tema, ou criar um esboço da estrutura.'
        });
      }

      return messages;
    }

    return [
      {
        id: 1,
        type: 'ai',
        content: 'Olá! Sou seu assistente de redação. Como posso ajudá-lo hoje? Posso pesquisar informações, sugerir melhorias ou ajudar com SEO.'
      }
    ];
  };

  // Chat editor hook - connects chat to article editing with AI
  const {
    messages: chatMessages,
    sendMessage: sendEditMessage,
    isProcessing: isChatProcessing,
    clearMessages: clearChatMessages,
    setWelcomeMessages,
    approveEdit,
    rejectEdit,
    requestModification
  } = useChatEditor({
    articleState: { title, linhaFina, content, tags },
    onEdit: (newContent, summary, messageId) => {
      // Always convert markdown to HTML
      // Even if content has some HTML, it may have markdown links/formatting that need conversion
      const bodyContent = newContent.body || '';
      const convertedBody = markdownToHtml(bodyContent);

      const contentWithHtmlBody = {
        ...newContent,
        body: convertedBody
      };
      // Push new version when AI edits are applied
      pushVersion(contentWithHtmlBody, 'ai', summary, messageId);
    },
    categoria: selectedPersona?.id || 'geral',
    tom: selectedTone?.id || 'conversacional'
  });

  // Set initial welcome messages
  useEffect(() => {
    const initialMessages = getInitialMessages();
    setWelcomeMessages(initialMessages);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const [chatInput, setChatInput] = useState('');

  // State for edit approval workflow
  const [modifyingMessageId, setModifyingMessageId] = useState(null);
  const [modificationInput, setModificationInput] = useState('');

  // Sugestões rápidas contextualizadas para edição
  const quickSuggestions = useMemo(() => {
    if (themeContext.tema) {
      return [
        'Melhore o SEO do título',
        'Torne o texto mais conciso',
        'Adicione mais contexto',
        'Corrija erros gramaticais'
      ];
    }
    return [
      'Melhore o SEO do título',
      'Torne o texto mais formal',
      'Resuma o conteúdo',
      'Expanda o último parágrafo'
    ];
  }, [themeContext.tema]);

  const handleSendMessage = async () => {
    if (!chatInput.trim() || isChatProcessing) return;

    const instruction = chatInput;
    setChatInput('');

    // Send edit instruction to AI
    await sendEditMessage(instruction);
  };

  const handleQuickSuggestion = (suggestion) => {
    setChatInput(suggestion);
  };

  // Word count - strip HTML tags for accurate count
  const wordCount = useMemo(() => {
    // Strip HTML tags and count words
    const textContent = content.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    return textContent ? textContent.split(/\s+/).filter(Boolean).length : 0;
  }, [content]);

  // Score SEO sincronizado com o painel SEO
  const seoScore = useMemo(() => {
    return calculateSEOScore({ title, linhaFina, content, tags });
  }, [title, linhaFina, content, tags]);

  // Funções para gerenciar tags
  const handleAddTag = () => {
    const trimmedTag = newTagInput.trim();
    if (trimmedTag && !tags.includes(trimmedTag)) {
      setTags([...tags, trimmedTag]);
      setNewTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setTags(tags.filter((tag) => tag !== tagToRemove));
  };

  const handleTagKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  // Função para gerar tags com IA - conectada ao API real
  const handleGenerateTagsWithAI = async () => {
    // Strip HTML tags for plain text analysis
    const plainContent = content.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    const textToAnalyze = [title, linhaFina, plainContent, themeContext.tema].filter(Boolean).join('\n\n');

    if (!textToAnalyze.trim()) return;

    setIsGeneratingTags(true);

    try {
      const result = await generateTags({ texto: textToAnalyze, max_tags: 10 });
      const generatedTags = result.tags || [];

      // Filter duplicates and already existing tags
      const newTags = generatedTags.filter(tag => tag && !tags.includes(tag));

      // Add tags with small delay for animation
      for (const tag of newTags) {
        setTags((prev) => [...prev, tag]);
        await new Promise((resolve) => setTimeout(resolve, 150));
      }
    } catch (err) {
      console.error('Error generating tags:', err);
      // Fallback: extract keywords from title
      if (title) {
        const titleWords = title.split(' ').filter((w) => w.length > 4 && !tags.includes(w));
        if (titleWords.length > 0) {
          setTags((prev) => [...prev, titleWords[0]]);
        }
      }
    } finally {
      setIsGeneratingTags(false);
    }
  };

  // Função para sugerir título com IA
  const handleSuggestTitle = async () => {
    const plainContent = content.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    if (!plainContent.trim()) return;

    setIsGeneratingTitle(true);

    try {
      const result = await editArticle({
        currentArticle: {
          title: title || '',
          linhaFina: linhaFina || '',
          content: plainContent,
          tags: tags
        },
        instruction: 'Sugira um título mais atraente e otimizado para SEO. Mantenha o título conciso (máximo 100 caracteres). Retorne APENAS o título sugerido.',
        editScope: 'title',
        categoria: selectedPersona?.id || 'geral',
        tom: selectedTone?.id || 'conversacional'
      });

      if (result.titulo) {
        setTitle(result.titulo);
        // Push version for undo support
        pushVersion({
          title: result.titulo,
          linhaFina,
          body: content,
          tags
        }, 'ai', 'Título sugerido pela IA');
      }
    } catch (err) {
      console.error('Error suggesting title:', err);
    } finally {
      setIsGeneratingTitle(false);
    }
  };

  // Helper para remover tags HTML e obter texto limpo
  const stripHtmlTags = (html) => {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || '';
  };

  // Função para copiar matéria para área de transferência
  const handleCopyToClipboard = async (format = 'text') => {
    let bodyContent;

    if (format === 'html') {
      // Manter tags HTML para colar em editores rich text
      bodyContent = content;
    } else {
      // Remover tags HTML para texto simples
      bodyContent = stripHtmlTags(content);
    }

    const formattedContent = [
      title,
      '',
      linhaFina,
      '',
      bodyContent,
      '',
      tags.length > 0 ? `Tags: ${tags.join(', ')}` : ''
    ].filter(Boolean).join('\n');

    try {
      await navigator.clipboard.writeText(formattedContent);
      setCopyType(format);
      setShowCopyDropdown(false);
      setTimeout(() => setCopyType(null), 2000);
    } catch (err) {
      console.error('Erro ao copiar:', err);
      // Fallback para navegadores antigos
      const textArea = document.createElement('textarea');
      textArea.value = formattedContent;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopyType(format);
      setShowCopyDropdown(false);
      setTimeout(() => setCopyType(null), 2000);
    }
  };

  // Build article data for API
  const buildArticleData = useCallback((status) => {
    return {
      title: title,
      linhaFina: linhaFina,
      content: content,
      status: status,
      category: selectedPersona?.name || selectedArticleType?.name || null,
      tags: tags,
      authorName: null, // Could be set from user context
      sourceArticleIds: themeContext.links?.map(link => link.id).filter(Boolean) || [],
      generationConfig: {
        tom: selectedTone?.id || null,
        persona: selectedPersona?.id || null,
        tipoMateria: selectedArticleType?.id || null,
        tema: themeContext.tema || null,
        geradoEm: resultado?.geradoEm || null
      }
    };
  }, [title, linhaFina, content, tags, selectedTone, selectedPersona, selectedArticleType, themeContext, resultado]);

  // Save as draft handler
  const handleSaveDraft = useCallback(async () => {
    if (!title.trim() && !content.trim()) {
      setSaveError('Adicione pelo menos um título ou conteúdo para salvar');
      return;
    }

    setIsSavingDraft(true);
    setSaveError(null);

    try {
      const articleData = buildArticleData('draft');

      let savedArticle;
      if (articleId) {
        // Update existing article
        savedArticle = await updateUserArticle(articleId, articleData);
      } else {
        // Create new article
        savedArticle = await createUserArticle(articleData);
        setArticleId(savedArticle.id);
      }

      setLastSavedAt(new Date());
      console.log('Draft saved:', savedArticle.id);
    } catch (err) {
      console.error('Error saving draft:', err);
      setSaveError(err.message || 'Erro ao salvar rascunho');
    } finally {
      setIsSavingDraft(false);
    }
  }, [title, content, articleId, buildArticleData]);

  // Publish handler
  const handlePublish = useCallback(async () => {
    if (!title.trim()) {
      setSaveError('Título é obrigatório para publicar');
      return;
    }
    if (!content.trim()) {
      setSaveError('Conteúdo é obrigatório para publicar');
      return;
    }

    setIsPublishing(true);
    setSaveError(null);

    try {
      const articleData = buildArticleData('published');

      let savedArticle;
      if (articleId) {
        // Update existing article
        savedArticle = await updateUserArticle(articleId, articleData);
      } else {
        // Create new article
        savedArticle = await createUserArticle(articleData);
      }

      console.log('Article published:', savedArticle.id);

      // Navigate to Minhas Matérias on success
      navigate('/minhas-materias');
    } catch (err) {
      console.error('Error publishing:', err);
      setSaveError(err.message || 'Erro ao publicar matéria');
    } finally {
      setIsPublishing(false);
    }
  }, [title, content, articleId, buildArticleData, navigate]);

  // Inline Version Dropdown component
  const VersionDropdown = ({ versions: versionsList, currentIdx, onSelect, onClose }) => {
    // Format relative time
    const formatTime = (timestamp) => {
      const diff = Date.now() - timestamp;
      const mins = Math.floor(diff / 60000);
      if (mins < 1) return 'agora';
      if (mins < 60) return `há ${mins} min`;
      const hours = Math.floor(mins / 60);
      if (hours < 24) return `há ${hours}h`;
      return `há ${Math.floor(hours / 24)}d`;
    };

    // Source icon
    const getSourceIcon = (source) => {
      if (source === 'ai') return <Bot size={12} className="text-tmc-orange" />;
      if (source === 'user') return <Edit3 size={12} className="text-blue-500" />;
      return <FileText size={12} className="text-medium-gray" />;
    };

    return (
      <>
        {/* Backdrop to close dropdown */}
        <div
          className="fixed inset-0 z-40"
          onClick={onClose}
        />
        <div className="absolute top-full left-0 mt-1 w-56 bg-white rounded-lg shadow-lg
                        border border-light-gray py-1 z-50 max-h-64 overflow-y-auto">
          <div className="px-3 py-2 border-b border-light-gray">
            <span className="text-xs font-semibold text-medium-gray">
              Histórico de Versões
            </span>
          </div>
          {versionsList.map((version, index) => {
            const isCurrent = index === currentIdx;
            const versionNum = index + 1;

            return (
              <button
                key={version.id}
                onClick={() => onSelect(version.id)}
                className={`w-full px-3 py-2 text-left hover:bg-off-white transition-colors ${
                  isCurrent ? 'bg-tmc-orange/5 border-l-2 border-tmc-orange' : ''
                }`}
              >
                <div className="flex items-center gap-2">
                  {getSourceIcon(version.source)}
                  <span className={`text-sm ${isCurrent ? 'font-semibold text-dark-gray' : 'text-medium-gray'}`}>
                    v{versionNum}
                  </span>
                  <span className="flex-1 text-xs text-medium-gray truncate">
                    {version.label}
                  </span>
                </div>
                <span className="text-[10px] text-light-gray ml-5">
                  {formatTime(version.timestamp)}
                </span>
              </button>
            );
          })}
        </div>
      </>
    );
  };

  // Show loading state when loading article for editing
  if (isLoadingArticle) {
    return (
      <div className="min-h-screen pt-16 bg-off-white flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 size={40} className="animate-spin text-tmc-orange" />
          <p className="text-medium-gray">Carregando matéria...</p>
        </div>
      </div>
    );
  }

  const isEditing = !!editArticleId;

  return (
    <div className="min-h-screen pt-16 bg-off-white">
      {/* Header */}
      <div className="bg-white border-b border-light-gray sticky top-16 z-40">
        <div className="flex items-center justify-between px-4 md:px-6 py-3">
          <button
            onClick={() => navigate(isEditing ? '/minhas-materias' : '/criar')}
            className="flex items-center gap-2 text-medium-gray hover:text-dark-gray transition-colors"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium hidden sm:inline">
              {isEditing ? 'Voltar para Minhas Matérias' : 'Voltar'}
            </span>
          </button>

          <div className="flex-1 max-w-4xl mx-4 md:mx-6">
            {/* Título */}
            <div className="relative">
              <label htmlFor="post-title" className="sr-only">Título da postagem</label>
              <input
                id="post-title"
                type="text"
                placeholder="Título da matéria"
                maxLength={100}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full text-center text-lg md:text-xl font-bold text-dark-gray placeholder:text-light-gray focus:outline-none"
              />
              <span className="absolute -bottom-3 right-0 text-xs text-medium-gray">
                {title.length}/100
              </span>
            </div>

            {/* Linha Fina (Subtítulo) */}
            <div className="relative mt-4">
              <label htmlFor="post-linha-fina" className="sr-only">Linha fina (subtítulo)</label>
              <input
                id="post-linha-fina"
                type="text"
                placeholder="Linha fina: complemento do título que contextualiza a notícia"
                maxLength={200}
                value={linhaFina}
                onChange={(e) => setLinhaFina(e.target.value)}
                className="w-full text-center text-sm md:text-base text-medium-gray placeholder:text-light-gray focus:outline-none italic"
              />
              <span className="absolute -bottom-3 right-0 text-xs text-medium-gray">
                {linhaFina.length}/200
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 md:gap-3">
            {/* Copy Dropdown */}
            <div className="relative">
              <Tooltip content={copyType ? 'Copiado!' : 'Copiar matéria'} position="bottom">
                <button
                  onClick={() => setShowCopyDropdown(!showCopyDropdown)}
                  disabled={!title && !content}
                  className={`flex items-center gap-2 px-3 md:px-4 py-2 text-sm font-medium border rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                    copyType
                      ? 'bg-success text-white border-success'
                      : 'text-medium-gray hover:text-dark-gray border-light-gray hover:bg-off-white'
                  }`}
                  aria-label="Copiar matéria"
                >
                  {copyType ? (
                    <>
                      <Check size={16} />
                      <span className="hidden sm:inline">Copiado!</span>
                    </>
                  ) : (
                    <>
                      <Copy size={16} />
                      <span className="hidden sm:inline">Copiar</span>
                      <ChevronDown size={14} />
                    </>
                  )}
                </button>
              </Tooltip>

              {showCopyDropdown && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowCopyDropdown(false)} />
                  <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-light-gray py-1 z-50">
                    <button
                      onClick={() => handleCopyToClipboard('text')}
                      className="w-full px-4 py-2 text-left text-sm text-dark-gray hover:bg-off-white flex items-center gap-2"
                    >
                      <FileText size={14} />
                      Copiar texto simples
                    </button>
                    <button
                      onClick={() => handleCopyToClipboard('html')}
                      className="w-full px-4 py-2 text-left text-sm text-dark-gray hover:bg-off-white flex items-center gap-2"
                    >
                      <Code size={14} />
                      Copiar com HTML
                    </button>
                  </div>
                </>
              )}
            </div>

            <Tooltip content={lastSavedAt ? `Último salvamento: ${lastSavedAt.toLocaleTimeString()}` : 'Salvar rascunho'} position="bottom">
              <button
                onClick={handleSaveDraft}
                disabled={isSavingDraft || (!title.trim() && !content.trim())}
                className="hidden sm:flex items-center gap-2 px-3 md:px-4 py-2 text-sm font-medium text-medium-gray hover:text-dark-gray border border-light-gray rounded-lg hover:bg-off-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSavingDraft ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Salvando...</span>
                  </>
                ) : (
                  <>
                    <Save size={16} />
                    <span>{articleId ? 'Salvar' : 'Salvar rascunho'}</span>
                  </>
                )}
              </button>
            </Tooltip>
            <button
              onClick={handlePublish}
              disabled={!title.trim() || !content.trim() || isPublishing}
              className="flex items-center gap-2 px-3 md:px-4 py-2 text-sm font-semibold text-white bg-tmc-orange rounded-lg hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPublishing ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Publicando...</span>
                </>
              ) : (
                <span>Publicar</span>
              )}
            </button>
          </div>
        </div>

        {/* Error banner */}
        {saveError && (
          <div className="bg-red-50 border-t border-red-200 px-4 py-2 flex items-center justify-between">
            <span className="text-sm text-red-700">{saveError}</span>
            <button
              onClick={() => setSaveError(null)}
              className="text-red-500 hover:text-red-700"
              aria-label="Fechar erro"
            >
              <X size={16} />
            </button>
          </div>
        )}
      </div>

      {/* Banner de Contexto do Tema */}
      {themeContext.tema && (
        <div className="bg-gradient-to-r from-orange-50 to-red-50 border-b border-orange-200 px-4 md:px-6 py-2">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <div className="p-1 bg-gradient-to-br from-orange-500 to-red-500 rounded">
                <Flame size={14} className="text-white" />
              </div>
              <span className="text-sm text-medium-gray">Tema:</span>
              <span className="font-semibold text-dark-gray">{themeContext.tema}</span>
              {themeContext.tipo && (
                <span className="px-2 py-0.5 bg-white border border-orange-200 rounded text-xs font-medium text-orange-700 capitalize">
                  {themeContext.tipo}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              {themeContext.links?.length > 0 && (
                <span className="flex items-center gap-1 text-xs text-medium-gray">
                  <Link2 size={12} />
                  {themeContext.links.length} link(s)
                </span>
              )}
              <button
                onClick={() => navigate('/criar')}
                className="text-xs text-tmc-orange hover:underline font-medium"
              >
                Trocar tema
              </button>
            </div>
          </div>
        </div>
      )}

      <div className={`flex flex-col lg:flex-row ${themeContext.tema ? 'h-[calc(100vh-11rem)]' : 'h-[calc(100vh-8rem)]'}`}>
        {/* Editor Area */}
        <div className="flex-1 flex flex-col lg:border-r border-light-gray overflow-visible">
          {/* Toolbar */}
          <div className="bg-white border-b border-light-gray p-2 md:p-3 space-y-2 overflow-visible relative z-30 isolate">
            {/* Rich Text Formatting Toolbar */}
            <EditorToolbar
              editor={editorRef.current?.editor}
              onUndo={undo}
              onRedo={redo}
              canUndo={canUndo}
              canRedo={canRedo}
              versionCount={versionCount}
              currentIndex={currentIndex}
              showVersionDropdown={showVersionDropdown}
              onToggleVersionDropdown={() => setShowVersionDropdown(!showVersionDropdown)}
              VersionDropdownComponent={
                showVersionDropdown && (
                  <VersionDropdown
                    versions={versions}
                    currentIdx={currentIndex}
                    onSelect={(id) => {
                      goToVersion(id);
                      setShowVersionDropdown(false);
                    }}
                    onClose={() => setShowVersionDropdown(false)}
                  />
                )
              }
            />

            {/* AI Tools */}
            <div className="flex flex-wrap items-center gap-2 pb-2">
              {/* Tone Dropdown */}
              <div className="relative flex-shrink-0">
                <Tooltip content="Escolha o tom de voz da matéria (formal, casual, etc.)" position="bottom">
                  <button
                    onClick={() => setOpenDropdown(openDropdown === 'tone' ? null : 'tone')}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      selectedTone
                        ? 'bg-tmc-orange text-white'
                        : 'bg-off-white text-dark-gray hover:bg-light-gray'
                    }`}
                    aria-label="Selecionar tom de voz"
                    aria-expanded={openDropdown === 'tone'}
                  >
                    <Sparkles size={16} />
                    <span className="hidden sm:inline">{selectedTone?.name || 'Tom'}</span>
                    <ChevronDown size={14} />
                  </button>
                </Tooltip>
                {openDropdown === 'tone' && (
                  <div className="absolute top-full left-0 mt-1 w-64 bg-white rounded-lg shadow-lg border border-light-gray py-2 z-50">
                    {mockTones.map((tone) => (
                      <button
                        key={tone.id}
                        onClick={() => {
                          setSelectedTone(tone);
                          setOpenDropdown(null);
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-off-white"
                      >
                        <p className="text-sm font-medium text-dark-gray">{tone.name}</p>
                        <p className="text-xs text-medium-gray">{tone.description}</p>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Persona Dropdown */}
              <div className="relative flex-shrink-0">
                <Tooltip content="Defina para qual público-alvo você está escrevendo" position="bottom">
                  <button
                    onClick={() => setOpenDropdown(openDropdown === 'persona' ? null : 'persona')}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      selectedPersona
                        ? 'bg-tmc-dark-green text-white'
                        : 'bg-off-white text-dark-gray hover:bg-light-gray'
                    }`}
                    aria-label="Selecionar persona"
                    aria-expanded={openDropdown === 'persona'}
                  >
                    <UserCircle size={16} />
                    <span className="hidden sm:inline">{selectedPersona?.name || 'Persona'}</span>
                    <ChevronDown size={14} />
                  </button>
                </Tooltip>
                {openDropdown === 'persona' && (
                  <div className="absolute top-full left-0 mt-1 w-64 bg-white rounded-lg shadow-lg border border-light-gray py-2 z-50">
                    {mockPersonas.map((persona) => (
                      <button
                        key={persona.id}
                        onClick={() => {
                          setSelectedPersona(persona);
                          setOpenDropdown(null);
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-off-white"
                      >
                        <p className="text-sm font-medium text-dark-gray">{persona.name}</p>
                        <p className="text-xs text-medium-gray">{persona.description}</p>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Article Type Dropdown */}
              <div className="relative flex-shrink-0">
                <Tooltip content="Escolha o tipo de matéria (destaque, coluna, serviço, etc.)" position="bottom">
                  <button
                    onClick={() => setOpenDropdown(openDropdown === 'articleType' ? null : 'articleType')}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      selectedArticleType
                        ? 'bg-blue-600 text-white'
                        : 'bg-off-white text-dark-gray hover:bg-light-gray'
                    }`}
                    aria-label="Selecionar tipo de matéria"
                    aria-expanded={openDropdown === 'articleType'}
                  >
                    <Newspaper size={16} />
                    <span className="hidden sm:inline">{selectedArticleType?.name || 'Tipo'}</span>
                    <ChevronDown size={14} />
                  </button>
                </Tooltip>
                {openDropdown === 'articleType' && (
                  <div className="absolute top-full left-0 mt-1 w-64 bg-white rounded-lg shadow-lg border border-light-gray py-2 z-50">
                    {articleTypes.map((type) => (
                      <button
                        key={type.id}
                        onClick={() => {
                          setSelectedArticleType(type);
                          setOpenDropdown(null);
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-off-white"
                      >
                        <p className="text-sm font-medium text-dark-gray">{type.name}</p>
                        <p className="text-xs text-medium-gray">{type.description}</p>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <Tooltip content="Ativar/desativar correção ortográfica automática" position="bottom">
                <button
                  onClick={() => setSpellCheck(!spellCheck)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex-shrink-0 ${
                    spellCheck
                      ? 'bg-success text-white'
                      : 'bg-off-white text-dark-gray hover:bg-light-gray'
                  }`}
                  aria-label="Correção ortográfica"
                  aria-pressed={spellCheck}
                >
                  <SpellCheck size={16} />
                  <span className="hidden md:inline">Correção</span>
                </button>
              </Tooltip>

              <Tooltip content="Traduzir texto selecionado para outro idioma" position="bottom">
                <button className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-off-white text-dark-gray hover:bg-light-gray rounded-lg text-sm font-medium transition-colors flex-shrink-0" aria-label="Traduzir texto">
                  <Languages size={16} />
                  <span>Traduzir</span>
                </button>
              </Tooltip>

              <Tooltip content="Analisar e otimizar seu texto para mecanismos de busca" position="bottom">
                <button
                  onClick={() => setActiveSidebarTab('seo')}
                  className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-off-white text-dark-gray hover:bg-light-gray rounded-lg text-sm font-medium transition-colors flex-shrink-0"
                  aria-label="Insights SEO"
                >
                  <BarChart3 size={16} />
                  <span>Insights SEO</span>
                </button>
              </Tooltip>

              <Tooltip content="Gerar sugestões de título com base no conteúdo" position="bottom">
                <button
                  onClick={handleSuggestTitle}
                  disabled={isGeneratingTitle || !content.trim()}
                  className="hidden lg:flex items-center gap-2 px-3 py-1.5 bg-off-white text-dark-gray hover:bg-light-gray rounded-lg text-sm font-medium transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Sugerir título"
                >
                  {isGeneratingTitle ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>Gerando...</span>
                    </>
                  ) : (
                    <>
                      <Lightbulb size={16} />
                      <span>Sugerir título</span>
                    </>
                  )}
                </button>
              </Tooltip>
            </div>
          </div>

          {/* Editor */}
          <div className="flex-1 p-4 md:p-8 overflow-y-auto bg-white">
            <RichTextEditor
              ref={editorRef}
              content={content}
              onChange={setContent}
              placeholder="Comece a escrever seu texto aqui ou use o assistente de IA para obter sugestões..."
              spellCheck={spellCheck}
              className="text-dark-gray text-base leading-relaxed"
            />
          </div>

          {/* Seção de Tópicos/Tags */}
          <div className="bg-white border-t border-light-gray px-4 md:px-6 py-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Tag size={16} className="text-medium-gray" />
                <span className="text-sm font-medium text-dark-gray">Tópicos</span>
                <span className="text-xs text-medium-gray">({tags.length})</span>
              </div>

              {/* Botão Gerar com IA */}
              <Tooltip content="Gerar tópicos automaticamente com IA baseado no conteúdo" position="top">
                <button
                  onClick={handleGenerateTagsWithAI}
                  disabled={isGeneratingTags || (!title.trim() && !linhaFina.trim() && !content.trim() && !themeContext.tema)}
                  className={`
                    flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full transition-all
                    ${isGeneratingTags
                      ? 'bg-tmc-orange/10 text-tmc-orange cursor-wait'
                      : 'border border-dashed border-light-gray text-medium-gray hover:border-tmc-orange hover:text-tmc-orange hover:bg-tmc-orange/5'
                    }
                    disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:border-light-gray disabled:hover:text-medium-gray disabled:hover:bg-transparent
                  `}
                  aria-label="Gerar tópicos com IA"
                >
                  {isGeneratingTags ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      <span className="hidden sm:inline">Gerando...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles size={14} />
                      <span className="hidden sm:inline">Gerar com IA</span>
                    </>
                  )}
                </button>
              </Tooltip>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {/* Tags existentes */}
              {tags.map((tag, index) => (
                <span
                  key={index}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-off-white border border-light-gray text-dark-gray text-sm rounded-full group hover:border-tmc-orange transition-colors animate-in fade-in slide-in-from-left-2 duration-200"
                >
                  {tag}
                  <button
                    onClick={() => handleRemoveTag(tag)}
                    className="ml-1 p-0.5 hover:bg-light-gray rounded-full transition-colors"
                    aria-label={`Remover tag ${tag}`}
                  >
                    <X size={12} className="text-medium-gray group-hover:text-error" />
                  </button>
                </span>
              ))}

              {/* Input para nova tag */}
              <div className="inline-flex items-center">
                <input
                  type="text"
                  placeholder="Adicionar tópico..."
                  value={newTagInput}
                  onChange={(e) => setNewTagInput(e.target.value)}
                  onKeyDown={handleTagKeyDown}
                  className="w-32 md:w-40 px-3 py-1.5 text-sm bg-transparent border border-dashed border-light-gray rounded-full focus:outline-none focus:border-tmc-orange placeholder:text-medium-gray"
                />
                {newTagInput.trim() && (
                  <Tooltip content="Adicionar tópico" shortcut="Enter" position="top">
                    <button
                      onClick={handleAddTag}
                      className="ml-2 p-1.5 bg-tmc-orange text-white rounded-full hover:bg-tmc-orange/90 transition-colors"
                      aria-label="Adicionar tópico"
                    >
                      <Plus size={14} />
                    </button>
                  </Tooltip>
                )}
              </div>
            </div>
            {tags.length === 0 && !isGeneratingTags && (
              <p className="text-xs text-medium-gray mt-2">
                Adicione tópicos manualmente ou clique em "Gerar com IA" para sugestões automáticas
              </p>
            )}
          </div>

          {/* Footer Stats */}
          <div className="bg-white border-t border-light-gray px-4 md:px-6 py-2 flex items-center justify-between">
            <span className="text-xs text-medium-gray">{wordCount} palavras</span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-medium-gray hidden sm:inline">Score SEO:</span>
              <div className="w-16 sm:w-24 h-2 bg-off-white rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    seoScore >= 70 ? 'bg-success' : seoScore >= 40 ? 'bg-warning' : 'bg-error'
                  }`}
                  style={{ width: `${seoScore}%` }}
                />
              </div>
              <span className="text-xs font-medium text-dark-gray">{seoScore}</span>
            </div>
          </div>
        </div>

        {/* Sidebar com Abas - Hidden on mobile, show as modal */}
        <div className="hidden lg:flex lg:w-96 bg-white flex-col border-l border-light-gray">
          {/* Tabs Header */}
          <div className="flex border-b border-light-gray">
            <button
              onClick={() => setActiveSidebarTab('assistente')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeSidebarTab === 'assistente'
                  ? 'text-tmc-orange border-b-2 border-tmc-orange bg-tmc-orange/5'
                  : 'text-medium-gray hover:text-dark-gray hover:bg-off-white'
              }`}
            >
              <Bot size={16} />
              <span>Assistente</span>
            </button>
            <button
              onClick={() => setActiveSidebarTab('seo')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeSidebarTab === 'seo'
                  ? 'text-tmc-orange border-b-2 border-tmc-orange bg-tmc-orange/5'
                  : 'text-medium-gray hover:text-dark-gray hover:bg-off-white'
              }`}
            >
              <BarChart3 size={16} />
              <span>SEO</span>
            </button>
          </div>

          {/* Conteúdo do Assistente */}
          {activeSidebarTab === 'assistente' && (
            <>
              {/* Chat Header */}
              <div className="px-4 py-3 border-b border-light-gray flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-tmc-orange rounded-lg flex items-center justify-center">
                    <Bot size={18} className="text-white" />
                  </div>
                  <span className="font-semibold text-dark-gray">Assistente de redação</span>
                </div>
                <Tooltip content="Limpar histórico do chat" position="left">
                  <button
                    onClick={clearChatMessages}
                    className="p-2 hover:bg-off-white rounded-lg transition-colors"
                    aria-label="Limpar histórico do chat"
                  >
                    <Trash2 size={16} className="text-medium-gray" />
                  </button>
                </Tooltip>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatMessages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-xl px-4 py-2.5 ${
                        message.type === 'user'
                          ? 'bg-tmc-orange text-white rounded-br-none'
                          : message.type === 'error'
                          ? 'bg-red-50 text-red-700 border border-red-200 rounded-bl-none'
                          : message.type === 'system'
                          ? 'bg-blue-50 text-blue-700 border border-blue-200 rounded-bl-none'
                          : 'bg-off-white text-dark-gray rounded-bl-none'
                      }`}
                    >
                      {message.isLoading ? (
                        <div className="flex items-center gap-2">
                          <Loader2 size={14} className="animate-spin" />
                          <p className="text-sm">{message.content}</p>
                        </div>
                      ) : (
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      )}

                      {/* SEO Compliance Warnings */}
                      {message.seoWarnings && message.seoWarnings.length > 0 && message.type === 'ai' && (
                        <div className="mt-3 pt-3 border-t border-light-gray">
                          <div className="flex items-center gap-1.5 mb-2">
                            <AlertTriangle size={12} className="text-warning" />
                            <span className="text-xs font-medium text-warning">Avisos SEO:</span>
                          </div>
                          <div className="space-y-1.5">
                            {message.seoWarnings.map((warning, idx) => (
                              <div
                                key={idx}
                                className={`text-xs px-2 py-1.5 rounded ${
                                  warning.severity === 'error'
                                    ? 'bg-red-50 text-red-700 border border-red-200'
                                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                                }`}
                              >
                                <p className="font-medium">{warning.message}</p>
                                <p className="text-[10px] opacity-80 mt-0.5">{warning.suggestion}</p>
                              </div>
                            ))}
                          </div>
                          <p className="text-[10px] text-medium-gray mt-2">
                            Use "Modificar" para pedir ajustes nos caracteres.
                          </p>
                        </div>
                      )}

                      {/* Pending Approval - Show action buttons */}
                      {message.isPendingApproval && message.type === 'ai' && (
                        <div className="mt-3 pt-3 border-t border-light-gray">
                          <p className="text-xs text-medium-gray mb-2">Deseja aplicar estas alterações?</p>

                          {/* Show modification input if user clicked "Modificar" */}
                          {modifyingMessageId === message.id ? (
                            <div className="space-y-2">
                              <input
                                type="text"
                                placeholder="Descreva o ajuste desejado..."
                                value={modificationInput}
                                onChange={(e) => setModificationInput(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter' && modificationInput.trim()) {
                                    requestModification(message.id, modificationInput);
                                    setModifyingMessageId(null);
                                    setModificationInput('');
                                  }
                                }}
                                disabled={isChatProcessing}
                                className="w-full px-3 py-1.5 bg-white border border-light-gray rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-tmc-orange"
                                autoFocus
                              />
                              <div className="flex gap-2">
                                <button
                                  onClick={() => {
                                    if (modificationInput.trim()) {
                                      requestModification(message.id, modificationInput);
                                      setModifyingMessageId(null);
                                      setModificationInput('');
                                    }
                                  }}
                                  disabled={!modificationInput.trim() || isChatProcessing}
                                  className="flex-1 px-3 py-1.5 bg-tmc-orange text-white text-xs font-medium rounded-lg hover:bg-tmc-orange/90 transition-colors disabled:opacity-50"
                                >
                                  Enviar Ajuste
                                </button>
                                <button
                                  onClick={() => {
                                    setModifyingMessageId(null);
                                    setModificationInput('');
                                  }}
                                  className="px-3 py-1.5 bg-light-gray text-medium-gray text-xs font-medium rounded-lg hover:bg-medium-gray/20 transition-colors"
                                >
                                  Cancelar
                                </button>
                              </div>
                            </div>
                          ) : (
                            /* Show approve/reject/modify buttons */
                            <div className="flex gap-2">
                              <button
                                onClick={() => approveEdit(message.id)}
                                className="flex-1 px-3 py-1.5 bg-success text-white text-xs font-medium rounded-lg hover:bg-success/90 transition-colors flex items-center justify-center gap-1"
                              >
                                <Check size={12} />
                                Aprovar
                              </button>
                              <button
                                onClick={() => setModifyingMessageId(message.id)}
                                className="flex-1 px-3 py-1.5 bg-tmc-orange text-white text-xs font-medium rounded-lg hover:bg-tmc-orange/90 transition-colors flex items-center justify-center gap-1"
                              >
                                <Edit3 size={12} />
                                Modificar
                              </button>
                              <button
                                onClick={() => rejectEdit(message.id)}
                                className="flex-1 px-3 py-1.5 bg-medium-gray text-white text-xs font-medium rounded-lg hover:bg-medium-gray/90 transition-colors flex items-center justify-center gap-1"
                              >
                                <X size={12} />
                                Rejeitar
                              </button>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Approved - Show success badge */}
                      {message.isApproved && message.type === 'ai' && (
                        <div className="mt-2 pt-2 border-t border-light-gray flex items-center gap-2">
                          <Check size={12} className="text-success" />
                          <span className="text-xs text-success font-medium">
                            Alterações aplicadas
                          </span>
                        </div>
                      )}

                      {/* Modified - Show modified badge */}
                      {message.isModified && message.type === 'ai' && (
                        <div className="mt-2 pt-2 border-t border-light-gray flex items-center gap-2">
                          <Edit3 size={12} className="text-tmc-orange" />
                          <span className="text-xs text-tmc-orange font-medium">
                            Proposta ajustada
                          </span>
                        </div>
                      )}

                      {/* Rejected - Show rejected badge */}
                      {message.isRejected && message.type === 'ai' && (
                        <div className="mt-2 pt-2 border-t border-light-gray flex items-center gap-2">
                          <X size={12} className="text-medium-gray" />
                          <span className="text-xs text-medium-gray font-medium">
                            Alterações rejeitadas
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {isChatProcessing && chatMessages.length === 0 && (
                  <div className="flex justify-start">
                    <div className="bg-off-white rounded-xl px-4 py-2.5 rounded-bl-none">
                      <div className="flex items-center gap-2">
                        <Loader2 size={14} className="animate-spin text-tmc-orange" />
                        <p className="text-sm text-medium-gray">Processando...</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Quick Suggestions */}
              <div className="px-4 py-2 border-t border-light-gray">
                <div className="flex flex-wrap gap-2">
                  {quickSuggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => handleQuickSuggestion(suggestion)}
                      className="px-3 py-1 bg-off-white text-medium-gray text-xs rounded-full hover:bg-light-gray transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>

              {/* Chat Input */}
              <div className="p-4 border-t border-light-gray">
                <div className="flex items-center gap-2">
                  <label htmlFor="chat-input" className="sr-only">Instrução de edição para a IA</label>
                  <input
                    id="chat-input"
                    type="text"
                    placeholder="Ex: melhore o SEO do título"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !isChatProcessing && handleSendMessage()}
                    disabled={isChatProcessing}
                    className="flex-1 px-4 py-2.5 bg-off-white border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange disabled:opacity-50"
                  />
                  <Tooltip content="Enviar instrução de edição" shortcut="Enter" position="top">
                    <button
                      onClick={handleSendMessage}
                      disabled={!chatInput.trim() || isChatProcessing}
                      className="p-2.5 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="Enviar instrução de edição"
                    >
                      {isChatProcessing ? (
                        <Loader2 size={18} className="animate-spin" />
                      ) : (
                        <Send size={18} />
                      )}
                    </button>
                  </Tooltip>
                </div>
                <p className="text-xs text-medium-gray mt-2 text-center">
                  {isChatProcessing
                    ? 'Editando o artigo...'
                    : 'Descreva como quer editar o artigo'
                  }
                </p>
              </div>
            </>
          )}

          {/* Conteúdo do SEO Analyzer */}
          {activeSidebarTab === 'seo' && (
            <div className="flex-1 overflow-hidden p-4">
              <SEOAnalyzerPanel
                title={title}
                linhaFina={linhaFina}
                content={content}
                tags={tags}
                articleType={selectedArticleType?.id || 'default'}
                onOptimizeWithAI={(seoAnalysis) => {
                  // Generate intelligent, data-driven prompt based on SEO analysis
                  // Now includes exact scoring rules and keyword extraction
                  const prompt = generateSEOOptimizationPrompt(
                    seoAnalysis,
                    selectedArticleType?.id || 'default',
                    'quick', // Use quick mode by default
                    [], // No specific focus areas
                    { title, content, tags } // Article data for keyword extraction
                  );

                  // Switch to assistant tab
                  setActiveSidebarTab('assistente');

                  // Auto-send the generated prompt
                  sendEditMessage(prompt);
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Close dropdowns */}
      {openDropdown && (
        <div className="fixed inset-0 z-10" onClick={() => setOpenDropdown(null)} />
      )}
    </div>
  );
};

export default CriarPostPage;
