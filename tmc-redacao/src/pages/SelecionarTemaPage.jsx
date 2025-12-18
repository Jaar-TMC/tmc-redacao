import { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  Search,
  Flame,
  TrendingUp,
  Twitter,
  X,
  Link2,
  Plus,
  FileText,
  Lightbulb,
  MessageSquare,
  Trash2,
  ExternalLink,
  CheckCircle2
} from 'lucide-react';
import { mockGoogleTrends, mockTwitterTrends, mockFeedThemes } from '../data/mockData';
import Skeleton from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';

// Dados expandidos para a tela (lista completa, não só top 5)
const expandedFeedThemes = [
  ...mockFeedThemes,
  { id: 9, theme: 'Reforma Tributária', count: 4, trend: 'up' },
  { id: 10, theme: 'Energia Solar', count: 4, trend: 'up' },
  { id: 11, theme: 'Educação', count: 3, trend: 'stable' },
  { id: 12, theme: 'Saúde Pública', count: 3, trend: 'down' },
];

const expandedGoogleTrends = [
  ...mockGoogleTrends,
  { id: 6, topic: 'ChatGPT', growth: '+120%', searches: '100K+' },
  { id: 7, topic: 'Copa América', growth: '+95%', searches: '90K+' },
  { id: 8, topic: 'Lula', growth: '+85%', searches: '80K+' },
  { id: 9, topic: 'Bolsonaro', growth: '+75%', searches: '70K+' },
  { id: 10, topic: 'Dólar Hoje', growth: '+65%', searches: '60K+' },
];

const expandedTwitterTrends = [
  ...mockTwitterTrends,
  { id: 6, hashtag: '#ForaMinistro', mentions: '38K' },
  { id: 7, hashtag: '#BrasilNoMapa', mentions: '32K' },
  { id: 8, hashtag: '#Tecnologia', mentions: '28K' },
  { id: 9, hashtag: '#Economia', mentions: '22K' },
  { id: 10, hashtag: '#Política', mentions: '18K' },
];

const contentTypes = [
  { id: 'noticia', label: 'Notícia', description: 'Fatos objetivos e atuais' },
  { id: 'analise', label: 'Análise', description: 'Interpretação aprofundada' },
  { id: 'opiniao', label: 'Opinião', description: 'Ponto de vista editorial' },
  { id: 'tutorial', label: 'Tutorial', description: 'Guia passo a passo' },
];

const SelecionarTemaPage = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('feed'); // feed, google, twitter
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTheme, setSelectedTheme] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Estado do painel de instruções
  const [links, setLinks] = useState([]);
  const [newLink, setNewLink] = useState('');
  const [instructions, setInstructions] = useState('');
  const [selectedContentType, setSelectedContentType] = useState(null);

  // Obter dados baseado na tab ativa
  const getThemesData = useCallback(() => {
    switch (activeTab) {
      case 'feed':
        return expandedFeedThemes.map(t => ({
          id: `feed-${t.id}`,
          name: t.theme,
          count: t.count,
          countLabel: 'matérias',
          trend: t.trend,
          source: 'feed'
        }));
      case 'google':
        return expandedGoogleTrends.map(t => ({
          id: `google-${t.id}`,
          name: t.topic,
          count: t.searches,
          countLabel: 'buscas',
          trend: 'up',
          growth: t.growth,
          source: 'google'
        }));
      case 'twitter':
        return expandedTwitterTrends.map(t => ({
          id: `twitter-${t.id}`,
          name: t.hashtag,
          count: t.mentions,
          countLabel: 'menções',
          trend: 'up',
          source: 'twitter'
        }));
      default:
        return [];
    }
  }, [activeTab]);

  // Filtrar temas pela busca
  const filteredThemes = useMemo(() => {
    const themes = getThemesData();
    if (!searchQuery.trim()) return themes;

    return themes.filter(t =>
      t.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [getThemesData, searchQuery]);

  // Handlers
  const handleThemeSelect = useCallback((theme) => {
    if (selectedTheme?.id === theme.id) {
      setSelectedTheme(null);
    } else {
      setSelectedTheme(theme);
    }
  }, [selectedTheme]);

  const handleAddLink = useCallback(() => {
    if (newLink.trim() && !links.includes(newLink.trim())) {
      setLinks(prev => [...prev, newLink.trim()]);
      setNewLink('');
    }
  }, [newLink, links]);

  const handleRemoveLink = useCallback((linkToRemove) => {
    setLinks(prev => prev.filter(l => l !== linkToRemove));
  }, []);

  const handleContinue = useCallback(() => {
    // Navegar para o editor com os dados do tema
    const params = new URLSearchParams();

    if (selectedTheme) {
      params.set('tema', selectedTheme.name);
      params.set('fonte', selectedTheme.source);
    }

    if (links.length > 0) {
      params.set('links', JSON.stringify(links));
    }

    if (instructions.trim()) {
      params.set('instrucoes', instructions);
    }

    if (selectedContentType) {
      params.set('tipo', selectedContentType);
    }

    const queryString = params.toString();
    navigate(`/criar/editor${queryString ? `?${queryString}` : ''}`);
  }, [navigate, selectedTheme, links, instructions, selectedContentType]);

  const handleSkip = useCallback(() => {
    navigate('/criar/editor');
  }, [navigate]);

  const handleBack = useCallback(() => {
    navigate('/');
  }, [navigate]);

  // Simular loading ao trocar tab
  const handleTabChange = useCallback((tab) => {
    setIsLoading(true);
    setActiveTab(tab);
    setSelectedTheme(null);
    setTimeout(() => setIsLoading(false), 300);
  }, []);

  const getTrendIcon = (trend) => {
    if (trend === 'up') return '↑';
    if (trend === 'down') return '↓';
    return '→';
  };

  const getTrendColor = (trend) => {
    if (trend === 'up') return 'text-green-600';
    if (trend === 'down') return 'text-red-500';
    return 'text-medium-gray';
  };

  return (
    <div className="min-h-screen bg-off-white">
      {/* Header */}
      <header className="bg-white border-b border-light-gray sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={handleBack}
              className="flex items-center gap-2 text-medium-gray hover:text-dark-gray transition-colors"
              aria-label="Voltar para redação"
            >
              <ArrowLeft size={20} />
              <span className="text-sm font-medium hidden sm:inline">Voltar</span>
            </button>

            <div className="text-center">
              <h1 className="text-lg md:text-xl font-bold text-dark-gray">
                Escolha um tema para sua matéria
              </h1>
              <p className="text-sm text-medium-gray hidden sm:block">
                Selecione uma tendência ou comece do zero
              </p>
            </div>

            <button
              onClick={handleSkip}
              className="flex items-center gap-2 text-tmc-orange hover:text-tmc-orange/80 transition-colors"
              aria-label="Pular e escrever do zero"
            >
              <span className="text-sm font-medium hidden sm:inline">Pular</span>
              <ArrowRight size={20} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-6 py-6">
        {/* Barra de Busca */}
        <div className="mb-6">
          <div className="relative max-w-2xl mx-auto">
            <Search
              className="absolute left-4 top-1/2 -translate-y-1/2 text-medium-gray"
              size={20}
              aria-hidden="true"
            />
            <input
              type="search"
              placeholder="Buscar em todas as tendências..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 border border-light-gray rounded-xl text-dark-gray placeholder:text-medium-gray focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange bg-white"
              aria-label="Buscar temas"
            />
          </div>
        </div>

        {/* Tabs */}
        <div className="flex justify-center mb-6">
          <div className="inline-flex bg-white rounded-xl p-1 border border-light-gray" role="tablist">
            <button
              role="tab"
              aria-selected={activeTab === 'feed'}
              onClick={() => handleTabChange('feed')}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'feed'
                  ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white shadow-sm'
                  : 'text-medium-gray hover:text-dark-gray hover:bg-off-white'
              }`}
            >
              <Flame size={18} />
              <span>Feed em Alta</span>
              <span className={`px-1.5 py-0.5 rounded text-xs ${
                activeTab === 'feed' ? 'bg-white/20' : 'bg-off-white'
              }`}>
                {expandedFeedThemes.length}
              </span>
            </button>

            <button
              role="tab"
              aria-selected={activeTab === 'google'}
              onClick={() => handleTabChange('google')}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'google'
                  ? 'bg-tmc-orange text-white shadow-sm'
                  : 'text-medium-gray hover:text-dark-gray hover:bg-off-white'
              }`}
            >
              <TrendingUp size={18} />
              <span>Google Trends</span>
              <span className={`px-1.5 py-0.5 rounded text-xs ${
                activeTab === 'google' ? 'bg-white/20' : 'bg-off-white'
              }`}>
                {expandedGoogleTrends.length}
              </span>
            </button>

            <button
              role="tab"
              aria-selected={activeTab === 'twitter'}
              onClick={() => handleTabChange('twitter')}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'twitter'
                  ? 'bg-[#1DA1F2] text-white shadow-sm'
                  : 'text-medium-gray hover:text-dark-gray hover:bg-off-white'
              }`}
            >
              <Twitter size={18} />
              <span>Twitter</span>
              <span className={`px-1.5 py-0.5 rounded text-xs ${
                activeTab === 'twitter' ? 'bg-white/20' : 'bg-off-white'
              }`}>
                {expandedTwitterTrends.length}
              </span>
            </button>
          </div>
        </div>

        {/* Conteúdo Principal */}
        <div className={`flex flex-col lg:flex-row gap-6 ${selectedTheme ? '' : ''}`}>
          {/* Grid de Temas */}
          <div className={`${selectedTheme ? 'lg:w-1/2' : 'w-full'} transition-all duration-300`}>
            <div className="bg-white rounded-xl border border-light-gray p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-dark-gray flex items-center gap-2">
                  {activeTab === 'feed' && <Flame size={18} className="text-orange-500" />}
                  {activeTab === 'google' && <TrendingUp size={18} className="text-tmc-orange" />}
                  {activeTab === 'twitter' && <Twitter size={18} className="text-[#1DA1F2]" />}
                  {activeTab === 'feed' && 'Temas dos Concorrentes'}
                  {activeTab === 'google' && 'Google Trends Brasil'}
                  {activeTab === 'twitter' && 'Twitter Trending'}
                </h2>
                <span className="text-xs text-medium-gray">
                  {filteredThemes.length} temas
                </span>
              </div>

              {isLoading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {[...Array(6)].map((_, i) => (
                    <Skeleton key={i} className="h-28 rounded-lg" />
                  ))}
                </div>
              ) : filteredThemes.length === 0 ? (
                <EmptyState
                  icon={Search}
                  title="Nenhum tema encontrado"
                  description="Tente ajustar sua busca"
                  className="py-12"
                />
              ) : (
                <div className={`grid gap-3 ${
                  selectedTheme
                    ? 'grid-cols-1 sm:grid-cols-2'
                    : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'
                }`}>
                  {filteredThemes.map((theme, index) => {
                    const isSelected = selectedTheme?.id === theme.id;

                    return (
                      <button
                        key={theme.id}
                        onClick={() => handleThemeSelect(theme)}
                        className={`relative p-4 rounded-lg border-2 text-left transition-all duration-200 group ${
                          isSelected
                            ? 'border-tmc-orange bg-tmc-orange/5 shadow-md'
                            : 'border-light-gray bg-white hover:border-tmc-orange/50 hover:shadow-sm'
                        }`}
                        aria-pressed={isSelected}
                        aria-label={`Selecionar tema ${theme.name}`}
                      >
                        {/* Badge de posição */}
                        <div className="flex items-start justify-between mb-2">
                          <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                            index < 3
                              ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white'
                              : 'bg-off-white text-medium-gray'
                          }`}>
                            #{index + 1}
                          </span>

                          {/* Google Trends - mostrar crescimento */}
                          {theme.growth && (
                            <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-0.5 rounded">
                              {theme.growth}
                            </span>
                          )}
                        </div>

                        {/* Nome do tema */}
                        <h3 className={`font-semibold mb-1 transition-colors ${
                          isSelected ? 'text-tmc-orange' : 'text-dark-gray group-hover:text-tmc-orange'
                        }`}>
                          {theme.name}
                        </h3>

                        {/* Contagem */}
                        <p className="text-sm text-medium-gray">
                          {theme.count} {theme.countLabel}
                        </p>

                        {/* Indicador de selecionado */}
                        {isSelected && (
                          <div className="absolute top-2 right-2">
                            <CheckCircle2 size={20} className="text-tmc-orange" />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Painel de Instruções */}
          {selectedTheme && (
            <div className="lg:w-1/2 animate-in slide-in-from-right duration-300">
              <div className="bg-white rounded-xl border border-light-gray p-6 sticky top-24">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="font-semibold text-dark-gray flex items-center gap-2">
                    <MessageSquare size={18} className="text-tmc-orange" />
                    Instruções para a IA
                  </h2>
                  <button
                    onClick={() => setSelectedTheme(null)}
                    className="p-1 hover:bg-off-white rounded transition-colors"
                    aria-label="Fechar painel"
                  >
                    <X size={18} className="text-medium-gray" />
                  </button>
                </div>

                {/* Tema Selecionado */}
                <div className="mb-6">
                  <label className="text-sm font-medium text-dark-gray mb-2 block">
                    Tema Selecionado
                  </label>
                  <div className="flex items-center justify-between p-3 bg-tmc-orange/10 border border-tmc-orange/30 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Flame size={18} className="text-tmc-orange" />
                      <span className="font-medium text-dark-gray">{selectedTheme.name}</span>
                    </div>
                    <button
                      onClick={() => setSelectedTheme(null)}
                      className="text-xs text-tmc-orange hover:underline"
                    >
                      Remover
                    </button>
                  </div>
                </div>

                {/* Links de Referência */}
                <div className="mb-6">
                  <label className="text-sm font-medium text-dark-gray mb-2 block">
                    Links de Referência
                    <span className="text-medium-gray font-normal ml-1">(opcional)</span>
                  </label>
                  <p className="text-xs text-medium-gray mb-3">
                    Cole links que a IA deve usar como base para a matéria
                  </p>

                  <div className="flex gap-2 mb-3">
                    <input
                      type="url"
                      placeholder="https://exemplo.com/materia"
                      value={newLink}
                      onChange={(e) => setNewLink(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAddLink()}
                      className="flex-1 px-3 py-2 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                    />
                    <button
                      onClick={handleAddLink}
                      disabled={!newLink.trim()}
                      className="px-3 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label="Adicionar link"
                    >
                      <Plus size={18} />
                    </button>
                  </div>

                  {links.length > 0 && (
                    <div className="space-y-2">
                      {links.map((link, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 bg-off-white rounded-lg group"
                        >
                          <div className="flex items-center gap-2 min-w-0 flex-1">
                            <Link2 size={14} className="text-medium-gray flex-shrink-0" />
                            <span className="text-sm text-dark-gray truncate">{link}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <a
                              href={link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1 hover:bg-white rounded opacity-0 group-hover:opacity-100 transition-opacity"
                              aria-label="Abrir link"
                            >
                              <ExternalLink size={14} className="text-medium-gray" />
                            </a>
                            <button
                              onClick={() => handleRemoveLink(link)}
                              className="p-1 hover:bg-white rounded opacity-0 group-hover:opacity-100 transition-opacity"
                              aria-label="Remover link"
                            >
                              <Trash2 size={14} className="text-red-500" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Instruções Adicionais */}
                <div className="mb-6">
                  <label className="text-sm font-medium text-dark-gray mb-2 block">
                    Instruções Adicionais
                    <span className="text-medium-gray font-normal ml-1">(opcional)</span>
                  </label>
                  <textarea
                    placeholder="Ex: Foque no impacto para a classe média, inclua dados históricos dos últimos 6 meses, mencione a opinião de economistas..."
                    value={instructions}
                    onChange={(e) => setInstructions(e.target.value)}
                    rows={4}
                    className="w-full px-3 py-2 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange resize-none"
                  />
                </div>

                {/* Tipo de Conteúdo */}
                <div className="mb-6">
                  <label className="text-sm font-medium text-dark-gray mb-2 block">
                    Tipo de Conteúdo
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {contentTypes.map((type) => (
                      <button
                        key={type.id}
                        onClick={() => setSelectedContentType(
                          selectedContentType === type.id ? null : type.id
                        )}
                        className={`p-3 rounded-lg border-2 text-left transition-all ${
                          selectedContentType === type.id
                            ? 'border-tmc-orange bg-tmc-orange/5'
                            : 'border-light-gray hover:border-tmc-orange/50'
                        }`}
                      >
                        <span className={`text-sm font-medium block ${
                          selectedContentType === type.id ? 'text-tmc-orange' : 'text-dark-gray'
                        }`}>
                          {type.label}
                        </span>
                        <span className="text-xs text-medium-gray">{type.description}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Info */}
                <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg mb-6">
                  <Lightbulb size={16} className="text-blue-500 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-blue-700">
                    Deixe os campos em branco para a IA gerar o conteúdo livremente com base apenas no tema selecionado.
                  </p>
                </div>

                {/* Botões de Ação */}
                <div className="flex gap-3">
                  <button
                    onClick={handleSkip}
                    className="flex-1 px-4 py-3 border border-light-gray text-medium-gray rounded-lg hover:bg-off-white transition-colors font-medium"
                  >
                    Escrever do zero
                  </button>
                  <button
                    onClick={handleContinue}
                    className="flex-1 px-4 py-3 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium flex items-center justify-center gap-2"
                  >
                    <FileText size={18} />
                    Criar matéria
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer com botões (quando nenhum tema selecionado) */}
        {!selectedTheme && (
          <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-light-gray p-4">
            <div className="max-w-7xl mx-auto flex justify-center gap-4">
              <button
                onClick={handleSkip}
                className="px-6 py-3 border border-light-gray text-medium-gray rounded-lg hover:bg-off-white transition-colors font-medium"
              >
                Escrever do zero, sem tema
              </button>
              <button
                disabled
                className="px-6 py-3 bg-light-gray text-medium-gray rounded-lg font-medium cursor-not-allowed flex items-center gap-2"
              >
                Selecione um tema para continuar
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Espaço para o footer fixo */}
      {!selectedTheme && <div className="h-24" />}
    </div>
  );
};

export default SelecionarTemaPage;
