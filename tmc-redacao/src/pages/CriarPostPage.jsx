import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  Bold,
  Italic,
  Underline,
  List,
  ListOrdered,
  Link2,
  Image,
  Undo,
  Redo,
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
  ExternalLink,
  Tag,
  Plus,
  Loader2
} from 'lucide-react';
import { mockTones, mockPersonas } from '../data/mockData';
import Tooltip from '../components/ui/Tooltip';
import { SEOAnalyzerPanel } from '../components/editor';

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

  const [title, setTitle] = useState('');
  const [linhaFina, setLinhaFina] = useState('');
  const [content, setContent] = useState('');
  const [selectedTone, setSelectedTone] = useState(null);
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [selectedArticleType, setSelectedArticleType] = useState(null);
  const [openDropdown, setOpenDropdown] = useState(null);
  const [spellCheck, setSpellCheck] = useState(false);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);

  // Estado para tópicos/tags
  const [tags, setTags] = useState([]);
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

  const [chatMessages, setChatMessages] = useState(getInitialMessages);
  const [chatInput, setChatInput] = useState('');

  // Sugestões rápidas contextualizadas
  const quickSuggestions = useMemo(() => {
    if (themeContext.tema) {
      return [
        `Pesquise sobre ${themeContext.tema}`,
        'Crie uma introdução impactante',
        'Sugira um título chamativo',
        'Monte a estrutura da matéria'
      ];
    }
    return [
      'Pesquise sobre o tema',
      'Sugira uma introdução',
      'Melhore este parágrafo',
      'Crie um resumo'
    ];
  }, [themeContext.tema]);

  const handleSendMessage = () => {
    if (!chatInput.trim()) return;

    const userMessage = {
      id: chatMessages.length + 1,
      type: 'user',
      content: chatInput
    };

    setChatMessages([...chatMessages, userMessage]);
    setChatInput('');

    // Simulate AI response
    setTimeout(() => {
      const aiResponse = {
        id: chatMessages.length + 2,
        type: 'ai',
        content: 'Analisando sua solicitação... Aqui está uma sugestão baseada no contexto do seu texto: Considere adicionar dados estatísticos para fortalecer seu argumento e incluir citações de especialistas para maior credibilidade.'
      };
      setChatMessages((prev) => [...prev, aiResponse]);
    }, 1000);
  };

  const handleQuickSuggestion = (suggestion) => {
    setChatInput(suggestion);
  };

  const wordCount = content.split(/\s+/).filter(Boolean).length;
  const seoScore = Math.min(100, Math.floor(wordCount / 5) + 30);

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

  // Função para gerar tags com IA
  const handleGenerateTagsWithAI = async () => {
    // Verificar se há conteúdo para analisar
    const hasContent = title.trim() || linhaFina.trim() || content.trim() || themeContext.tema;
    if (!hasContent) return;

    setIsGeneratingTags(true);

    // Simular chamada à API de IA (mock)
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // Tags mock baseadas no contexto
    const mockGeneratedTags = [];

    // Extrair palavras-chave do título
    if (title) {
      const titleWords = title.split(' ').filter((w) => w.length > 4);
      if (titleWords.length > 0) mockGeneratedTags.push(titleWords[0]);
    }

    // Tags baseadas no tema do contexto
    if (themeContext.tema) {
      mockGeneratedTags.push(themeContext.tema);
    }

    // Tags genéricas de exemplo
    const genericTags = ['Notícias', 'Brasil', 'Atualidades', 'Economia', 'Política', 'Tecnologia'];
    const randomTags = genericTags.sort(() => 0.5 - Math.random()).slice(0, 3);
    mockGeneratedTags.push(...randomTags);

    // Filtrar duplicatas e tags já existentes
    const newTags = [...new Set(mockGeneratedTags)]
      .filter((tag) => tag && !tags.includes(tag))
      .slice(0, 5);

    // Adicionar tags com pequeno delay para animação
    for (const tag of newTags) {
      setTags((prev) => [...prev, tag]);
      await new Promise((resolve) => setTimeout(resolve, 150));
    }

    setIsGeneratingTags(false);
  };

  return (
    <div className="min-h-screen pt-16 bg-off-white">
      {/* Header */}
      <div className="bg-white border-b border-light-gray sticky top-16 z-40">
        <div className="flex items-center justify-between px-4 md:px-6 py-3">
          <button
            onClick={() => navigate('/criar')}
            className="flex items-center gap-2 text-medium-gray hover:text-dark-gray transition-colors"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium hidden sm:inline">Voltar</span>
          </button>

          <div className="flex-1 max-w-2xl mx-4 md:mx-8">
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
            <button
              onClick={() => {
                setIsSavingDraft(true);
                setTimeout(() => setIsSavingDraft(false), 1000);
              }}
              disabled={isSavingDraft}
              className="hidden sm:block px-3 md:px-4 py-2 text-sm font-medium text-medium-gray hover:text-dark-gray border border-light-gray rounded-lg hover:bg-off-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSavingDraft ? 'Salvando...' : 'Salvar como rascunho'}
            </button>
            <button
              onClick={() => {
                setIsPublishing(true);
                setTimeout(() => setIsPublishing(false), 1500);
              }}
              disabled={!title || !content || isPublishing}
              className="px-3 md:px-4 py-2 text-sm font-semibold text-white bg-tmc-orange rounded-lg hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPublishing ? 'Publicando...' : 'Publicar'}
            </button>
          </div>
        </div>
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
            {/* Formatting */}
            <div className="flex items-center gap-1">
              <Tooltip content="Negrito" shortcut="Ctrl+B">
                <button className="p-2 hover:bg-off-white rounded transition-colors" aria-label="Negrito">
                  <Bold size={18} className="text-medium-gray" />
                </button>
              </Tooltip>
              <Tooltip content="Itálico" shortcut="Ctrl+I">
                <button className="p-2 hover:bg-off-white rounded transition-colors" aria-label="Itálico">
                  <Italic size={18} className="text-medium-gray" />
                </button>
              </Tooltip>
              <Tooltip content="Sublinhado" shortcut="Ctrl+U">
                <button className="p-2 hover:bg-off-white rounded transition-colors" aria-label="Sublinhado">
                  <Underline size={18} className="text-medium-gray" />
                </button>
              </Tooltip>
              <div className="w-px h-6 bg-light-gray mx-2" />
              <Tooltip content="Lista com marcadores">
                <button className="p-2 hover:bg-off-white rounded transition-colors" aria-label="Lista com marcadores">
                  <List size={18} className="text-medium-gray" />
                </button>
              </Tooltip>
              <Tooltip content="Lista numerada">
                <button className="p-2 hover:bg-off-white rounded transition-colors" aria-label="Lista numerada">
                  <ListOrdered size={18} className="text-medium-gray" />
                </button>
              </Tooltip>
              <div className="w-px h-6 bg-light-gray mx-2" />
              <Tooltip content="Inserir hyperlink" shortcut="Ctrl+K">
                <button className="p-2 hover:bg-off-white rounded transition-colors" aria-label="Inserir hyperlink">
                  <Link2 size={18} className="text-medium-gray" />
                </button>
              </Tooltip>
              <Tooltip content="Inserir imagem">
                <button className="p-2 hover:bg-off-white rounded transition-colors" aria-label="Inserir imagem">
                  <Image size={18} className="text-medium-gray" />
                </button>
              </Tooltip>
              <div className="w-px h-6 bg-light-gray mx-2" />
              <Tooltip content="Desfazer" shortcut="Ctrl+Z">
                <button className="p-2 hover:bg-off-white rounded transition-colors" aria-label="Desfazer">
                  <Undo size={18} className="text-medium-gray" />
                </button>
              </Tooltip>
              <Tooltip content="Refazer" shortcut="Ctrl+Y">
                <button className="p-2 hover:bg-off-white rounded transition-colors" aria-label="Refazer">
                  <Redo size={18} className="text-medium-gray" />
                </button>
              </Tooltip>
            </div>

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
                <button className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-off-white text-dark-gray hover:bg-light-gray rounded-lg text-sm font-medium transition-colors flex-shrink-0" aria-label="Insights SEO">
                  <BarChart3 size={16} />
                  <span>Insights SEO</span>
                </button>
              </Tooltip>

              <Tooltip content="Gerar sugestões de título com base no conteúdo" position="bottom">
                <button className="hidden lg:flex items-center gap-2 px-3 py-1.5 bg-off-white text-dark-gray hover:bg-light-gray rounded-lg text-sm font-medium transition-colors flex-shrink-0" aria-label="Sugerir título">
                  <Lightbulb size={16} />
                  <span>Sugerir título</span>
                </button>
              </Tooltip>
            </div>
          </div>

          {/* Editor */}
          <div className="flex-1 p-4 md:p-8 overflow-y-auto">
            <textarea
              placeholder="Comece a escrever seu texto aqui ou use o assistente de IA para obter sugestões..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full h-full resize-none text-dark-gray text-base leading-relaxed focus:outline-none placeholder:text-light-gray"
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
                  <button className="p-2 hover:bg-off-white rounded-lg transition-colors" aria-label="Limpar histórico do chat">
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
                          : 'bg-off-white text-dark-gray rounded-bl-none'
                      }`}
                    >
                      <p className="text-sm">{message.content}</p>
                      {message.type === 'ai' && (
                        <button className="mt-2 text-xs text-tmc-orange hover:underline">
                          Inserir no texto
                        </button>
                      )}
                    </div>
                  </div>
                ))}
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
                  <label htmlFor="chat-input" className="sr-only">Mensagem para o assistente de IA</label>
                  <input
                    id="chat-input"
                    type="text"
                    placeholder="Ex: como melhorar a introdução?"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                    className="flex-1 px-4 py-2.5 bg-off-white border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                  />
                  <Tooltip content="Enviar mensagem" shortcut="Enter" position="top">
                    <button
                      onClick={handleSendMessage}
                      disabled={!chatInput.trim()}
                      className="p-2.5 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="Enviar mensagem"
                    >
                      <Send size={18} />
                    </button>
                  </Tooltip>
                </div>
                <p className="text-xs text-medium-gray mt-2 text-center">
                  Pressione Enter para enviar
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
                onOptimizeWithAI={() => {
                  // Mudar para aba do assistente e enviar sugestão
                  setActiveSidebarTab('assistente');
                  setChatInput('Analise meu texto e sugira melhorias para SEO');
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
