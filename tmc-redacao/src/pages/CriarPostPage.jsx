import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  ChevronDown
} from 'lucide-react';
import { mockTones, mockPersonas } from '../data/mockData';

const CriarPostPage = () => {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [selectedTone, setSelectedTone] = useState(null);
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [openDropdown, setOpenDropdown] = useState(null);
  const [spellCheck, setSpellCheck] = useState(false);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    {
      id: 1,
      type: 'ai',
      content: 'Olá! Sou seu assistente de redação. Como posso ajudá-lo hoje? Posso pesquisar informações, sugerir melhorias ou ajudar com SEO.'
    }
  ]);
  const [chatInput, setChatInput] = useState('');

  const quickSuggestions = [
    'Pesquise sobre o tema',
    'Sugira uma introdução',
    'Melhore este parágrafo',
    'Crie um resumo'
  ];

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

  return (
    <div className="min-h-screen pt-16 bg-off-white">
      {/* Header */}
      <div className="bg-white border-b border-light-gray sticky top-16 z-40">
        <div className="flex items-center justify-between px-4 md:px-6 py-3">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-medium-gray hover:text-dark-gray transition-colors"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium hidden sm:inline">Voltar para redação</span>
          </button>

          <div className="flex-1 max-w-xl mx-4 md:mx-8 relative">
            <label htmlFor="post-title" className="sr-only">Título da postagem</label>
            <input
              id="post-title"
              type="text"
              placeholder="Ex: Nova análise sobre economia brasileira"
              maxLength={100}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full text-center text-lg md:text-xl font-bold text-dark-gray placeholder:text-light-gray focus:outline-none"
            />
            <span className="absolute -bottom-4 right-0 text-xs text-medium-gray">
              {title.length}/100
            </span>
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

      <div className="flex flex-col lg:flex-row h-[calc(100vh-8rem)]">
        {/* Editor Area */}
        <div className="flex-1 flex flex-col lg:border-r border-light-gray">
          {/* Toolbar */}
          <div className="bg-white border-b border-light-gray p-2 md:p-3 space-y-2 overflow-visible">
            {/* Formatting */}
            <div className="flex items-center gap-1">
              <button className="p-2 hover:bg-off-white rounded transition-colors">
                <Bold size={18} className="text-medium-gray" />
              </button>
              <button className="p-2 hover:bg-off-white rounded transition-colors">
                <Italic size={18} className="text-medium-gray" />
              </button>
              <button className="p-2 hover:bg-off-white rounded transition-colors">
                <Underline size={18} className="text-medium-gray" />
              </button>
              <div className="w-px h-6 bg-light-gray mx-2" />
              <button className="p-2 hover:bg-off-white rounded transition-colors">
                <List size={18} className="text-medium-gray" />
              </button>
              <button className="p-2 hover:bg-off-white rounded transition-colors">
                <ListOrdered size={18} className="text-medium-gray" />
              </button>
              <div className="w-px h-6 bg-light-gray mx-2" />
              <button className="p-2 hover:bg-off-white rounded transition-colors">
                <Link2 size={18} className="text-medium-gray" />
              </button>
              <button className="p-2 hover:bg-off-white rounded transition-colors">
                <Image size={18} className="text-medium-gray" />
              </button>
              <div className="w-px h-6 bg-light-gray mx-2" />
              <button className="p-2 hover:bg-off-white rounded transition-colors">
                <Undo size={18} className="text-medium-gray" />
              </button>
              <button className="p-2 hover:bg-off-white rounded transition-colors">
                <Redo size={18} className="text-medium-gray" />
              </button>
            </div>

            {/* AI Tools */}
            <div className="flex items-center gap-2 overflow-x-auto pb-2">
              {/* Tone Dropdown */}
              <div className="relative flex-shrink-0">
                <button
                  onClick={() => setOpenDropdown(openDropdown === 'tone' ? null : 'tone')}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    selectedTone
                      ? 'bg-tmc-orange text-white'
                      : 'bg-off-white text-dark-gray hover:bg-light-gray'
                  }`}
                >
                  <Sparkles size={16} />
                  <span className="hidden sm:inline">{selectedTone?.name || 'Tom'}</span>
                  <ChevronDown size={14} />
                </button>
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
                <button
                  onClick={() => setOpenDropdown(openDropdown === 'persona' ? null : 'persona')}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    selectedPersona
                      ? 'bg-tmc-dark-green text-white'
                      : 'bg-off-white text-dark-gray hover:bg-light-gray'
                  }`}
                >
                  <UserCircle size={16} />
                  <span className="hidden sm:inline">{selectedPersona?.name || 'Persona'}</span>
                  <ChevronDown size={14} />
                </button>
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

              <button
                onClick={() => setSpellCheck(!spellCheck)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex-shrink-0 ${
                  spellCheck
                    ? 'bg-success text-white'
                    : 'bg-off-white text-dark-gray hover:bg-light-gray'
                }`}
              >
                <SpellCheck size={16} />
                <span className="hidden md:inline">Correção</span>
              </button>

              <button className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-off-white text-dark-gray hover:bg-light-gray rounded-lg text-sm font-medium transition-colors flex-shrink-0">
                <Languages size={16} />
                <span>Traduzir</span>
              </button>

              <button className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-off-white text-dark-gray hover:bg-light-gray rounded-lg text-sm font-medium transition-colors flex-shrink-0">
                <BarChart3 size={16} />
                <span>Insights SEO (Otimização para Mecanismos de Busca)</span>
              </button>

              <button className="hidden lg:flex items-center gap-2 px-3 py-1.5 bg-off-white text-dark-gray hover:bg-light-gray rounded-lg text-sm font-medium transition-colors flex-shrink-0">
                <Lightbulb size={16} />
                <span>Sugerir título</span>
              </button>
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

        {/* AI Chat Sidebar - Hidden on mobile, show as modal */}
        <div className="hidden lg:flex lg:w-96 bg-white flex-col border-l border-light-gray">
          {/* Chat Header */}
          <div className="px-4 py-3 border-b border-light-gray flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-tmc-orange rounded-lg flex items-center justify-center">
                <Bot size={18} className="text-white" />
              </div>
              <span className="font-semibold text-dark-gray">Assistente de redação</span>
            </div>
            <button className="p-2 hover:bg-off-white rounded-lg transition-colors">
              <Trash2 size={16} className="text-medium-gray" />
            </button>
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
              <button
                onClick={handleSendMessage}
                disabled={!chatInput.trim()}
                className="p-2.5 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Enviar mensagem"
              >
                <Send size={18} />
              </button>
            </div>
            <p className="text-xs text-medium-gray mt-2 text-center">
              Pressione Enter para enviar
            </p>
          </div>
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
