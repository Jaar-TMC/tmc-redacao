import { useState, useCallback, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCriar } from '../../context/CriarContext';
import {
  ArrowLeft, ArrowRight, HelpCircle, Calendar, FileText, Quote,
  Info, Building2, Palette, MessageSquare, Newspaper, Layers,
  X, Plus, Eye, EyeOff, Edit3, Code
} from 'lucide-react';
import {
  Stepper,
  ConfigField,
  PromptPreview,
  CategorySelector,
  CategoryGuidelines,
  OpinionToggle
} from '../../components/criar';
import { RequirePermission } from '../../components/auth';
import { PERMISSIONS } from '../../constants/permissions';
import {
  CATEGORIAS_EDITORIAIS,
  CREDITO_OPTIONS,
  getTonesForCategory,
  getDefaultToneForCategory,
  categoryAllowsOpinion
} from '../../constants/editorial';

/**
 * ConfigurarPage - Etapa 3 do fluxo de criação de matéria
 *
 * Permite ao usuário configurar parâmetros de geração e revisar
 * o texto base antes de gerar a matéria.
 *
 * Refactored to use TMC's category-based editorial guidelines.
 */

// Tooltips content
const tooltips = {
  dataPublicacao: {
    title: 'Data de Publicação',
    content: (
      <div className="space-y-2">
        <p>Quando o conteúdo original foi publicado ou quando o evento aconteceu.</p>
        <p>Isso ajuda a IA a contextualizar temporalmente e usar verbos no tempo correto.</p>
        <p className="text-tmc-orange"><strong>Exemplo:</strong> Se o texto-base é de ontem, a IA saberá usar "anunciou ontem" em vez de "anuncia hoje".</p>
      </div>
    )
  },
  lide: {
    title: 'Orientação sobre o Lead',
    content: (
      <div className="space-y-2">
        <p>O lide é o primeiro parágrafo da matéria - deve responder às perguntas: O quê? Quem? Quando? Onde? Por quê? Como?</p>
        <p><strong>Indique qual ângulo destacar:</strong></p>
        <ul className="list-disc list-inside space-y-1 text-medium-gray">
          <li>"Focar no impacto econômico para o cidadão"</li>
          <li>"Destacar a reação do mercado financeiro"</li>
          <li>"Priorizar as declarações do ministro"</li>
        </ul>
      </div>
    )
  },
  citacoes: {
    title: 'Declarações de Fontes',
    content: (
      <div className="space-y-2">
        <p>Citações diretas de especialistas, autoridades ou envolvidos dão credibilidade e humanizam a matéria.</p>
        <p><strong>Formato sugerido:</strong></p>
        <p className="text-medium-gray italic">"Nome, cargo/função: 'Declaração entre aspas simples'"</p>
        <p className="text-tmc-orange mt-2"><strong>Exemplo:</strong> "João Silva, economista da FGV: 'As medidas terão efeito positivo em até 6 meses'"</p>
      </div>
    )
  },
  contexto: {
    title: 'Contexto Adicional',
    content: (
      <div className="space-y-2">
        <p>Informações de background que a IA deve considerar mas que não estão no texto-base:</p>
        <ul className="list-disc list-inside space-y-1 text-medium-gray">
          <li>Histórico do tema ("Essa é a terceira tentativa...")</li>
          <li>Nuances políticas ("O partido X é contra...")</li>
          <li>Dados complementares ("Segundo o IBGE...")</li>
          <li>Conexões com outros fatos</li>
        </ul>
      </div>
    )
  },
  creditos: {
    title: 'Créditos a Instituições',
    content: (
      <div className="space-y-2">
        <p>Alguns conteúdos exigem atribuição obrigatória:</p>
        <ul className="list-disc list-inside space-y-1 text-medium-gray">
          <li>Material de agências (Agência Brasil, Reuters, AFP)</li>
          <li>Conteúdo de assessorias de imprensa</li>
          <li>Dados de institutos de pesquisa</li>
        </ul>
        <p>Se marcado, a atribuição aparecerá no final da matéria.</p>
      </div>
    )
  },
  categoria: {
    title: 'Estilo Editorial',
    content: (
      <div className="space-y-2">
        <p>Define a voz e regras editoriais específicas do TMC:</p>
        <ul className="list-disc list-inside space-y-1 text-medium-gray">
          <li><strong>Esportes:</strong> Gírias moderadas, paixão, proximidade com torcedor</li>
          <li><strong>Entretenimento:</strong> Leve, pop, trocadilhos</li>
          <li><strong>Política:</strong> Sóbrio, didático, sem piadas</li>
          <li><strong>Economia:</strong> Traduzir para cotidiano</li>
          <li><strong>Geral:</strong> Conversacional, próximo</li>
        </ul>
        <p className="text-tmc-orange">Cada categoria tem tons específicos disponíveis.</p>
      </div>
    )
  },
  tom: {
    title: 'Tom da Escrita',
    content: (
      <div className="space-y-2">
        <p>O tom varia de acordo com a categoria selecionada.</p>
        <p>Cada categoria tem tons específicos que fazem sentido para aquele tipo de conteúdo.</p>
        <p className="text-tmc-orange">Selecione a categoria primeiro para ver os tons disponíveis.</p>
      </div>
    )
  },
  instrucoes: {
    title: 'Instruções Adicionais',
    content: (
      <div className="space-y-2">
        <p>Comandos específicos para a IA seguir:</p>
        <p><strong>Exemplos úteis:</strong></p>
        <ul className="list-disc list-inside space-y-1 text-medium-gray">
          <li>"Evitar termos muito técnicos"</li>
          <li>"Explicar siglas na primeira menção"</li>
          <li>"Manter parágrafos curtos (3-4 linhas)"</li>
          <li>"Incluir dados numéricos quando disponíveis"</li>
        </ul>
      </div>
    )
  },
  tipoMateria: {
    title: 'Tipo de Conteúdo',
    content: (
      <div className="space-y-2">
        <p>Define o tipo de conteúdo a ser gerado.</p>
        <p className="text-tmc-orange">Atualmente disponível: Matéria editorial para publicação no site.</p>
      </div>
    )
  }
};

const ConfigurarPage = () => {
  const navigate = useNavigate();

  // Context - dados e funções do fluxo de criação
  const {
    configuracoes,
    fonte,
    getTextoBaseParaGeracao,
    getTotalPalavras,
    setConfiguracoes,
    confirmarConfiguracoes,
  } = useCriar();

  // Guard: redirect to /criar if no fonte type is set
  useEffect(() => {
    if (!fonte?.tipo) {
      navigate('/criar', { replace: true });
    }
  }, [fonte?.tipo, navigate]);

  // Form state - inicializado com valores do context (para quando usuário voltar)
  const [dataPublicacao, setDataPublicacao] = useState(configuracoes.data || '');
  const [orientacaoLide, setOrientacaoLide] = useState(configuracoes.orientacaoLide || '');
  const [citacoes, setCitacoes] = useState(configuracoes.citacoes || []);
  const [novaCitacao, setNovaCitacao] = useState('');
  const [contextoAdicional, setContextoAdicional] = useState(configuracoes.contexto || '');
  const [precisaCredito, setPrecisaCredito] = useState(!!configuracoes.creditos);
  const [creditosSelecionados, setCreditosSelecionados] = useState(() => {
    if (!configuracoes.creditos) return [];
    // Backward compat: old format stored a single ID
    const asId = CREDITO_OPTIONS.find(o => o.id === configuracoes.creditos);
    if (asId) return [asId.id];
    // New format: comma-separated labels
    const parts = configuracoes.creditos.split(',').map(s => s.trim()).filter(Boolean);
    return CREDITO_OPTIONS.filter(o => parts.includes(o.label)).map(o => o.id);
  });
  const [instrucoes, setInstrucoes] = useState(configuracoes.instrucoes || '');
  const [tipoMateria, setTipoMateria] = useState(configuracoes.tipoMateria || 'destaque');

  // NEW: Category-based state
  const [categoria, setCategoria] = useState(configuracoes.categoria || 'geral');
  const [tom, setTom] = useState(configuracoes.tom || getDefaultToneForCategory('geral'));
  const [modoOpinativo, setModoOpinativo] = useState(configuracoes.modoOpinativo || false);

  // Advanced mode toggle state
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Get available tones for selected category
  const availableTones = useMemo(() => getTonesForCategory(categoria), [categoria]);

  // Get texto base from context
  const textoBase = useMemo(() => getTextoBaseParaGeracao(), [getTextoBaseParaGeracao]);
  const totalPalavras = useMemo(() => getTotalPalavras(), [getTotalPalavras]);

  // Handle category change - update tone to category default
  const handleCategoryChange = useCallback((newCategoria) => {
    setCategoria(newCategoria);
    setTom(getDefaultToneForCategory(newCategoria));
    // Reset opinion mode if new category doesn't allow it
    if (!categoryAllowsOpinion(newCategoria)) {
      setModoOpinativo(false);
    }
  }, []);

  // Build current config for prompt preview
  const currentPromptConfig = useMemo(() => ({
    categoria,
    tom,
    tipoMateria,
    modoOpinativo,
    orientacaoLide,
    citacoes,
    contexto: contextoAdicional,
    creditos: precisaCredito && creditosSelecionados.length > 0
      ? creditosSelecionados.map(id => CREDITO_OPTIONS.find(o => o.id === id)?.label || id).join(', ')
      : '',
    instrucoes,
  }), [categoria, tom, tipoMateria, modoOpinativo, orientacaoLide, citacoes, contextoAdicional, precisaCredito, creditosSelecionados, instrucoes]);

  // Get source info
  const fonteInfo = useMemo(() => {
    if (!fonte?.tipo) return null;

    switch (fonte.tipo) {
      case 'feed': {
        const articles = fonte.dados || [];
        return {
          tipo: 'Feed RSS',
          descricao: `${articles.length} matéria${articles.length !== 1 ? 's' : ''} selecionada${articles.length !== 1 ? 's' : ''}`,
          titulos: articles.map(a => a.title).slice(0, 3)
        };
      }
      case 'tema':
        return {
          tipo: 'Tema',
          descricao: fonte.dados?.tema || 'Tema personalizado',
          titulos: []
        };
      case 'link':
        return {
          tipo: 'Link',
          descricao: fonte.dados?.url || 'URL externa',
          titulos: []
        };
      case 'transcription':
        return {
          tipo: 'Transcrição',
          descricao: 'Áudio/Vídeo transcrito',
          titulos: []
        };
      default:
        return {
          tipo: 'Fonte',
          descricao: 'Conteúdo selecionado',
          titulos: []
        };
    }
  }, [fonte]);

  // Sincronizar estados locais com o context
  useEffect(() => {
    setConfiguracoes({
      data: dataPublicacao,
      orientacaoLide,
      citacoes,
      contexto: contextoAdicional,
      creditos: precisaCredito && creditosSelecionados.length > 0
        ? creditosSelecionados.map(id => CREDITO_OPTIONS.find(o => o.id === id)?.label || id).join(', ')
        : '',
      categoria,
      tom,
      modoOpinativo,
      instrucoes,
      tipoMateria,
    });
  }, [dataPublicacao, orientacaoLide, citacoes, contextoAdicional, precisaCredito, creditosSelecionados, categoria, tom, modoOpinativo, instrucoes, tipoMateria, setConfiguracoes]);

  // Handlers
  const handleAddCitacao = useCallback(() => {
    if (novaCitacao.trim()) {
      setCitacoes(prev => [...prev, { id: Date.now(), text: novaCitacao.trim() }]);
      setNovaCitacao('');
    }
  }, [novaCitacao]);

  const handleRemoveCitacao = useCallback((id) => {
    setCitacoes(prev => prev.filter(c => c.id !== id));
  }, []);

  const handleToggleCredito = useCallback((id) => {
    setCreditosSelecionados(prev =>
      prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
    );
  }, []);

  const handleStepClick = useCallback((stepIndex) => {
    const routes = ['/criar', '/criar/texto-base', '/criar/configurar', '/criar/editor'];
    if (stepIndex < 2) {
      navigate(routes[stepIndex]);
    }
  }, [navigate]);

  return (
    <div className="min-h-screen bg-off-white pt-20">
      <div className="max-w-6xl mx-auto px-4 py-6">
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

          <div className="flex items-center gap-3">
            <RequirePermission permission={PERMISSIONS.VIEW_ADVANCED_MODE}>
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors ${
                  showAdvanced
                    ? 'bg-gray-800 text-white'
                    : 'text-medium-gray hover:text-tmc-orange hover:bg-off-white'
                }`}
                aria-label="Modo Avançado"
              >
                {showAdvanced ? <EyeOff size={18} /> : <Code size={18} />}
                <span className="text-sm font-medium hidden sm:inline">
                  {showAdvanced ? 'Ocultar Prompt' : 'Modo Avançado'}
                </span>
              </button>
            </RequirePermission>
            <button
              className="flex items-center gap-2 text-medium-gray hover:text-tmc-orange transition-colors"
              aria-label="Ajuda"
            >
              <HelpCircle size={20} />
              <span className="text-sm font-medium hidden sm:inline">Ajuda</span>
            </button>
          </div>
        </div>

        {/* Stepper */}
        <Stepper
          steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
          currentStep={2}
          onStepClick={handleStepClick}
        />

        {/* Category Selector - Full Width */}
        <div className="bg-white rounded-xl p-6 mb-6">
          <ConfigField
            label="Estilo Editorial"
            icon={<Layers size={18} />}
            tooltip={tooltips.categoria}
          >
            <CategorySelector
              selectedCategory={categoria}
              onCategoryChange={handleCategoryChange}
            />
          </ConfigField>
        </div>

        {/* Category Guidelines */}
        <CategoryGuidelines
          categoryId={categoria}
          className="mb-6"
        />

        {/* Opinion Toggle (only for categories that allow it) */}
        {categoryAllowsOpinion(categoria) && (
          <OpinionToggle
            categoryId={categoria}
            isEnabled={modoOpinativo}
            onToggle={setModoOpinativo}
            className="mb-6"
          />
        )}

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Left Column - Configurations */}
          <div className="bg-white border border-light-gray rounded-xl p-6">
            <h2 className="text-lg font-semibold text-dark-gray mb-6 flex items-center gap-2">
              <FileText size={20} className="text-tmc-orange" />
              Configurações da Matéria
            </h2>

            <div className="space-y-6">
              {/* Tom da Escrita - Dynamic based on category */}
              <ConfigField
                label="Tom da Escrita"
                icon={<Palette size={18} />}
                tooltip={tooltips.tom}
              >
                <div className="space-y-2">
                  {availableTones.map(tone => (
                    <label
                      key={tone.id}
                      className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                        tom === tone.id
                          ? 'bg-orange-50 border border-tmc-orange'
                          : 'bg-off-white hover:bg-gray-100'
                      }`}
                    >
                      <input
                        type="radio"
                        name="tom"
                        value={tone.id}
                        checked={tom === tone.id}
                        onChange={(e) => setTom(e.target.value)}
                        className="w-4 h-4 mt-0.5 text-tmc-orange focus:ring-tmc-orange"
                      />
                      <div>
                        <span className="text-sm font-medium text-dark-gray">{tone.label}</span>
                        <p className="text-xs text-medium-gray">{tone.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </ConfigField>

              {/* Tipo de Conteúdo */}
              <ConfigField
                label="Tipo de Conteúdo"
                icon={<Newspaper size={18} />}
                tooltip={tooltips.tipoMateria}
              >
                <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-50 border border-blue-500">
                  <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                  <div>
                    <span className="text-sm font-medium text-dark-gray">Matéria para o Site</span>
                    <p className="text-xs text-medium-gray">Conteúdo editorial</p>
                  </div>
                </div>
              </ConfigField>

              {/* Data de Publicação */}
              <ConfigField
                label="Data de Publicação"
                icon={<Calendar size={18} />}
                tooltip={tooltips.dataPublicacao}
              >
                <input
                  type="date"
                  value={dataPublicacao}
                  onChange={(e) => setDataPublicacao(e.target.value)}
                  className="w-full px-4 py-2.5 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                />
              </ConfigField>

              {/* Orientação do Lead */}
              <ConfigField
                label="Orientação sobre o Lead"
                icon={<FileText size={18} />}
                tooltip={tooltips.lide}
              >
                <textarea
                  value={orientacaoLide}
                  onChange={(e) => setOrientacaoLide(e.target.value)}
                  placeholder="Ex: Focar no impacto econômico para o cidadão comum..."
                  rows={2}
                  className="w-full px-4 py-2.5 border border-light-gray rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                />
              </ConfigField>

              {/* Citações */}
              <ConfigField
                label="Declarações de Fontes"
                icon={<Quote size={18} />}
                tooltip={tooltips.citacoes}
              >
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={novaCitacao}
                      onChange={(e) => setNovaCitacao(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAddCitacao()}
                      placeholder="Nome, cargo: 'Declaração...'"
                      className="flex-1 px-4 py-2.5 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                    />
                    <button
                      onClick={handleAddCitacao}
                      disabled={!novaCitacao.trim()}
                      className="px-4 py-2.5 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <Plus size={18} />
                    </button>
                  </div>
                  {citacoes.length > 0 && (
                    <div className="space-y-2">
                      {citacoes.map(citacao => (
                        <div key={citacao.id} className="flex items-start gap-2 p-3 bg-off-white rounded-lg">
                          <Quote size={14} className="text-tmc-orange mt-0.5 flex-shrink-0" />
                          <p className="flex-1 text-sm text-dark-gray">{citacao.text}</p>
                          <button
                            onClick={() => handleRemoveCitacao(citacao.id)}
                            className="text-medium-gray hover:text-red-500 transition-colors"
                          >
                            <X size={16} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </ConfigField>

              {/* Contexto Adicional */}
              <ConfigField
                label="Contexto Adicional"
                icon={<Info size={18} />}
                tooltip={tooltips.contexto}
              >
                <textarea
                  value={contextoAdicional}
                  onChange={(e) => setContextoAdicional(e.target.value)}
                  placeholder="Informações de background relevantes para a matéria..."
                  rows={3}
                  className="w-full px-4 py-2.5 border border-light-gray rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                />
              </ConfigField>

              {/* Créditos */}
              <ConfigField
                label="Créditos a Instituição"
                icon={<Building2 size={18} />}
                tooltip={tooltips.creditos}
              >
                <div className="space-y-3">
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="credito"
                        checked={!precisaCredito}
                        onChange={() => {
                          setPrecisaCredito(false);
                          setCreditosSelecionados([]);
                        }}
                        className="w-4 h-4 text-tmc-orange focus:ring-tmc-orange"
                      />
                      <span className="text-sm text-dark-gray">Não precisa</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="credito"
                        checked={precisaCredito}
                        onChange={() => setPrecisaCredito(true)}
                        className="w-4 h-4 text-tmc-orange focus:ring-tmc-orange"
                      />
                      <span className="text-sm text-dark-gray">Sim, precisa</span>
                    </label>
                  </div>
                  {precisaCredito && (
                    <div className="space-y-2">
                      {CREDITO_OPTIONS.map(opt => (
                        <label
                          key={opt.id}
                          className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                            creditosSelecionados.includes(opt.id)
                              ? 'bg-orange-50 border border-tmc-orange'
                              : 'bg-off-white hover:bg-gray-100 border border-transparent'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={creditosSelecionados.includes(opt.id)}
                            onChange={() => handleToggleCredito(opt.id)}
                            className="w-4 h-4 text-tmc-orange focus:ring-tmc-orange rounded"
                          />
                          <span className="text-sm text-dark-gray">{opt.label}</span>
                        </label>
                      ))}
                      {creditosSelecionados.length > 0 && (
                        <p className="text-xs text-medium-gray mt-1">
                          {creditosSelecionados.length} instituição{creditosSelecionados.length !== 1 ? 'ões' : ''} selecionada{creditosSelecionados.length !== 1 ? 's' : ''}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </ConfigField>

              {/* Instruções para IA */}
              <ConfigField
                label="Instruções para a IA"
                icon={<MessageSquare size={18} />}
                tooltip={tooltips.instrucoes}
              >
                <textarea
                  value={instrucoes}
                  onChange={(e) => setInstrucoes(e.target.value)}
                  placeholder="Ex: Evitar termos técnicos, manter parágrafos curtos..."
                  rows={3}
                  className="w-full px-4 py-2.5 border border-light-gray rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                />
              </ConfigField>
            </div>
          </div>

          {/* Right Column - Texto Base Preview */}
          <div className="bg-white border border-light-gray rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-dark-gray flex items-center gap-2">
                <Eye size={20} className="text-tmc-orange" />
                Texto Base
              </h2>
              <button
                onClick={() => navigate('/criar/texto-base')}
                className="flex items-center gap-1 text-sm text-tmc-orange hover:text-tmc-orange/80 transition-colors"
              >
                <Edit3 size={14} />
                Editar
              </button>
            </div>

            {/* Source Info */}
            {fonteInfo && (
              <div className="mb-4 p-3 bg-off-white rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-tmc-orange uppercase tracking-wide">
                    {fonteInfo.tipo}
                  </span>
                </div>
                <p className="text-sm text-dark-gray font-medium">{fonteInfo.descricao}</p>
                {fonteInfo.titulos.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {fonteInfo.titulos.map((titulo, i) => (
                      <li key={i} className="text-xs text-medium-gray truncate">
                        • {titulo}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* Stats */}
            <div className="flex items-center gap-4 mb-4 text-sm">
              <div className="flex items-center gap-1.5">
                <FileText size={14} className="text-medium-gray" />
                <span className="text-dark-gray font-medium">{totalPalavras}</span>
                <span className="text-medium-gray">palavras</span>
              </div>
            </div>

            {/* Texto Preview */}
            <div className="border border-light-gray rounded-lg p-4 max-h-[500px] overflow-y-auto bg-off-white/50">
              {textoBase ? (
                <p className="text-sm text-dark-gray whitespace-pre-wrap leading-relaxed">
                  {textoBase}
                </p>
              ) : (
                <div className="text-center py-8">
                  <FileText size={32} className="text-light-gray mx-auto mb-2" />
                  <p className="text-sm text-medium-gray">
                    Nenhum texto base selecionado
                  </p>
                  <button
                    onClick={() => navigate('/criar/texto-base')}
                    className="mt-3 text-sm text-tmc-orange hover:underline"
                  >
                    Voltar e selecionar conteúdo
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Advanced Mode - Prompt Preview */}
        {showAdvanced && (
          <div className="mb-6">
            <PromptPreview
              config={currentPromptConfig}
              textoBase={textoBase || ''}
            />
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex justify-between">
          <button
            onClick={() => navigate('/criar/texto-base')}
            className="flex items-center gap-2 px-6 py-3 border border-light-gray text-medium-gray rounded-lg hover:bg-off-white transition-colors"
          >
            <ArrowLeft size={20} />
            Voltar
          </button>
          <button
            onClick={() => {
              confirmarConfiguracoes();
              navigate('/criar/revisar');
            }}
            className="flex items-center gap-2 px-6 py-3 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors"
          >
            Revisar e Gerar
            <ArrowRight size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfigurarPage;
