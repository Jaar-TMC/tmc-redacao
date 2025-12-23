import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCriar } from '../../context/CriarContext';
import {
  ArrowLeft, ArrowRight, HelpCircle, Calendar, FileText, Quote,
  Info, Building2, User, Palette, MessageSquare, Link, Youtube,
  FileUp, X, Plus, ExternalLink, Check
} from 'lucide-react';
import { Stepper, ConfigField } from '../../components/criar';

/**
 * ConfigurarPage - Etapa 3 do fluxo de criação de matéria
 *
 * Permite ao usuário configurar parâmetros de geração e adicionar
 * materiais complementares.
 */

// Opções de persona
const personaOptions = [
  { id: 'jornalista', label: 'Jornalista Imparcial', description: 'Objetivo, factual, sem opinião' },
  { id: 'especialista', label: 'Especialista', description: 'Análise técnica aprofundada' },
  { id: 'colunista', label: 'Colunista', description: 'Pode incluir opinião fundamentada' },
  { id: 'influencer', label: 'Influencer', description: 'Linguagem próxima e engajadora' }
];

// Opções de tom
const tomOptions = [
  { id: 'formal', label: 'Formal' },
  { id: 'informal', label: 'Informal' },
  { id: 'tecnico', label: 'Técnico' },
  { id: 'persuasivo', label: 'Persuasivo' },
  { id: 'neutro', label: 'Neutro' }
];

// Opções de crédito
const creditoOptions = [
  { id: 'agencia-brasil', label: 'Agência Brasil' },
  { id: 'reuters', label: 'Reuters' },
  { id: 'afp', label: 'AFP' },
  { id: 'assessoria', label: 'Assessoria de Imprensa' },
  { id: 'outro', label: 'Outro...' }
];

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
    title: 'Orientação sobre o Lide',
    content: (
      <div className="space-y-2">
        <p>O lide é o primeiro parágrafo da matéria - deve responder às perguntas: O quê? Quem? Quando? Onde? Por quê? Como?</p>
        <p><strong>Indique qual ângulo destacar:</strong></p>
        <ul className="list-disc list-inside space-y-1 text-gray-300">
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
        <p className="text-gray-300 italic">"Nome, cargo/função: 'Declaração entre aspas simples'"</p>
        <p className="text-tmc-orange mt-2"><strong>Exemplo:</strong> "João Silva, economista da FGV: 'As medidas terão efeito positivo em até 6 meses'"</p>
      </div>
    )
  },
  contexto: {
    title: 'Contexto Adicional',
    content: (
      <div className="space-y-2">
        <p>Informações de background que a IA deve considerar mas que não estão no texto-base:</p>
        <ul className="list-disc list-inside space-y-1 text-gray-300">
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
        <ul className="list-disc list-inside space-y-1 text-gray-300">
          <li>Material de agências (Agência Brasil, Reuters, AFP)</li>
          <li>Conteúdo de assessorias de imprensa</li>
          <li>Dados de institutos de pesquisa</li>
        </ul>
        <p>Se marcado, a atribuição aparecerá no final da matéria.</p>
      </div>
    )
  },
  persona: {
    title: 'Persona da Matéria',
    content: (
      <div className="space-y-2">
        <p>Define a "voz" e abordagem do texto:</p>
        <ul className="list-disc list-inside space-y-1 text-gray-300">
          <li><strong>Jornalista Imparcial:</strong> Objetivo, factual, sem opinião</li>
          <li><strong>Especialista:</strong> Análise técnica aprofundada</li>
          <li><strong>Colunista:</strong> Pode incluir opinião fundamentada</li>
          <li><strong>Influencer:</strong> Linguagem próxima e engajadora</li>
        </ul>
        <p className="text-tmc-orange">Para hard news, prefira "Jornalista Imparcial".</p>
      </div>
    )
  },
  tom: {
    title: 'Tom da Escrita',
    content: (
      <div className="space-y-2">
        <p>O tom afeta a escolha de palavras e construção das frases:</p>
        <ul className="list-disc list-inside space-y-1 text-gray-300">
          <li><strong>Formal:</strong> Linguagem séria, vocabulário culto</li>
          <li><strong>Informal:</strong> Mais leve, próximo do leitor</li>
          <li><strong>Técnico:</strong> Termos especializados, para público expert</li>
          <li><strong>Persuasivo:</strong> Argumentativo, para editoriais</li>
          <li><strong>Neutro:</strong> Equilibrado, sem emoção</li>
        </ul>
        <p className="text-tmc-orange">Para notícias do dia, "Formal" ou "Neutro" funcionam melhor.</p>
      </div>
    )
  },
  instrucoes: {
    title: 'Instruções Adicionais',
    content: (
      <div className="space-y-2">
        <p>Comandos específicos para a IA seguir:</p>
        <p><strong>Exemplos úteis:</strong></p>
        <ul className="list-disc list-inside space-y-1 text-gray-300">
          <li>"Evitar termos muito técnicos"</li>
          <li>"Explicar siglas na primeira menção"</li>
          <li>"Manter parágrafos curtos (3-4 linhas)"</li>
          <li>"Incluir dados numéricos quando disponíveis"</li>
          <li>"Não usar adjetivos valorativos"</li>
        </ul>
      </div>
    )
  },
  linkWeb: {
    title: 'Link Complementar (Web)',
    content: (
      <div className="space-y-2">
        <p>Adicione links de páginas que complementam a matéria. O conteúdo será extraído automaticamente.</p>
        <p><strong>Útil para:</strong></p>
        <ul className="list-disc list-inside space-y-1 text-gray-300">
          <li>Matérias relacionadas de outros veículos</li>
          <li>Páginas oficiais com dados adicionais</li>
          <li>Comunicados de imprensa</li>
        </ul>
        <p>Você poderá revisar e selecionar o que usar.</p>
      </div>
    )
  },
  videoYoutube: {
    title: 'Vídeo do YouTube',
    content: (
      <div className="space-y-2">
        <p>Adicione um vídeo complementar ao texto-base. A transcrição será extraída automaticamente.</p>
        <p><strong>Útil para:</strong></p>
        <ul className="list-disc list-inside space-y-1 text-gray-300">
          <li>Entrevistas relacionadas ao tema</li>
          <li>Coletivas de imprensa</li>
          <li>Pronunciamentos oficiais</li>
        </ul>
        <p>Você poderá revisar e selecionar trechos específicos.</p>
      </div>
    )
  },
  pdf: {
    title: 'Arquivo PDF',
    content: (
      <div className="space-y-2">
        <p>Anexe documentos PDF como fonte adicional. O texto será extraído para referência.</p>
        <p><strong>Útil para:</strong></p>
        <ul className="list-disc list-inside space-y-1 text-gray-300">
          <li>Relatórios oficiais e estudos</li>
          <li>Documentos de governo</li>
          <li>Papers e pesquisas acadêmicas</li>
          <li>Notas técnicas e comunicados</li>
        </ul>
        <p className="text-tmc-orange">Máximo: 50 páginas ou 10MB por arquivo.</p>
      </div>
    )
  }
};

const ConfigurarPage = () => {
  const navigate = useNavigate();

  // Context - dados e funções do fluxo de criação
  const {
    configuracoes,
    materiaisComplementares,
    setConfiguracoes,
    adicionarMaterial,
    removerMaterial,
    confirmarConfiguracoes,
  } = useCriar();

  // Form state - inicializado com valores do context (para quando usuário voltar)
  const [dataPublicacao, setDataPublicacao] = useState(configuracoes.data || '');
  const [orientacaoLide, setOrientacaoLide] = useState(configuracoes.orientacaoLide || '');
  const [citacoes, setCitacoes] = useState(configuracoes.citacoes || []);
  const [novaCitacao, setNovaCitacao] = useState('');
  const [contextoAdicional, setContextoAdicional] = useState(configuracoes.contexto || '');
  const [precisaCredito, setPrecisaCredito] = useState(!!configuracoes.creditos);
  const [creditoSelecionado, setCreditoSelecionado] = useState(configuracoes.creditos || '');
  const [persona, setPersona] = useState(configuracoes.persona || 'jornalista');
  const [tom, setTom] = useState(configuracoes.tom || 'formal');
  const [instrucoes, setInstrucoes] = useState(configuracoes.instrucoes || '');

  // Complementary materials state - inicializado com valores do context
  const [links, setLinks] = useState(materiaisComplementares.links || []);
  const [novoLink, setNovoLink] = useState('');
  const [videos, setVideos] = useState(materiaisComplementares.videos || []);
  const [novoVideo, setNovoVideo] = useState('');
  const [pdfs, setPdfs] = useState(materiaisComplementares.pdfs || []);

  // Sincronizar estados locais com o context
  useEffect(() => {
    setConfiguracoes({
      data: dataPublicacao,
      orientacaoLide,
      citacoes,
      contexto: contextoAdicional,
      creditos: precisaCredito ? creditoSelecionado : '',
      persona,
      tom,
      instrucoes,
    });
  }, [dataPublicacao, orientacaoLide, citacoes, contextoAdicional, precisaCredito, creditoSelecionado, persona, tom, instrucoes, setConfiguracoes]);

  // Sincronizar materiais complementares com o context
  useEffect(() => {
    // Sincroniza links
    const contextLinks = materiaisComplementares.links || [];
    if (JSON.stringify(links) !== JSON.stringify(contextLinks)) {
      links.forEach((link, index) => {
        if (!contextLinks.find(l => l.id === link.id)) {
          adicionarMaterial('links', link);
        }
      });
    }
  }, [links, materiaisComplementares.links, adicionarMaterial]);

  useEffect(() => {
    // Sincroniza videos
    const contextVideos = materiaisComplementares.videos || [];
    if (JSON.stringify(videos) !== JSON.stringify(contextVideos)) {
      videos.forEach((video) => {
        if (!contextVideos.find(v => v.id === video.id)) {
          adicionarMaterial('videos', video);
        }
      });
    }
  }, [videos, materiaisComplementares.videos, adicionarMaterial]);

  useEffect(() => {
    // Sincroniza pdfs
    const contextPdfs = materiaisComplementares.pdfs || [];
    if (JSON.stringify(pdfs) !== JSON.stringify(contextPdfs)) {
      pdfs.forEach((pdf) => {
        if (!contextPdfs.find(p => p.id === pdf.id)) {
          adicionarMaterial('pdfs', pdf);
        }
      });
    }
  }, [pdfs, materiaisComplementares.pdfs, adicionarMaterial]);

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

  const handleAddLink = useCallback(() => {
    if (novoLink.trim()) {
      setLinks(prev => [...prev, { id: Date.now(), url: novoLink.trim(), status: 'pending' }]);
      setNovoLink('');
    }
  }, [novoLink]);

  const handleRemoveLink = useCallback((id) => {
    setLinks(prev => prev.filter(l => l.id !== id));
  }, []);

  const handleAddVideo = useCallback(() => {
    if (novoVideo.trim()) {
      setVideos(prev => [...prev, { id: Date.now(), url: novoVideo.trim(), status: 'pending' }]);
      setNovoVideo('');
    }
  }, [novoVideo]);

  const handleRemoveVideo = useCallback((id) => {
    setVideos(prev => prev.filter(v => v.id !== id));
  }, []);

  const handleFileUpload = useCallback((e) => {
    const files = Array.from(e.target.files || []);
    const newPdfs = files.map(file => ({
      id: Date.now() + Math.random(),
      name: file.name,
      size: file.size,
      status: 'uploaded'
    }));
    setPdfs(prev => [...prev, ...newPdfs]);
  }, []);

  const handleRemovePdf = useCallback((id) => {
    setPdfs(prev => prev.filter(p => p.id !== id));
  }, []);

  const handleStepClick = useCallback((stepIndex) => {
    const routes = ['/criar', '/criar/texto-base', '/criar/configurar', '/criar/editor'];
    if (stepIndex < 2) {
      navigate(routes[stepIndex]);
    }
  }, [navigate]);

  const materialsCount = links.length + videos.length + pdfs.length;

  return (
    <div className="min-h-screen bg-off-white">
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

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Left Column - Configurations */}
          <div className="bg-white border border-light-gray rounded-xl p-6">
            <h2 className="text-lg font-semibold text-dark-gray mb-6 flex items-center gap-2">
              <FileText size={20} className="text-tmc-orange" />
              Configurações da Matéria
            </h2>

            <div className="space-y-6">
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

              {/* Orientação do Lide */}
              <ConfigField
                label="Orientação sobre o Lide"
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
                        onChange={() => setPrecisaCredito(false)}
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
                    <select
                      value={creditoSelecionado}
                      onChange={(e) => setCreditoSelecionado(e.target.value)}
                      className="w-full px-4 py-2.5 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                    >
                      <option value="">Selecione a instituição...</option>
                      {creditoOptions.map(opt => (
                        <option key={opt.id} value={opt.id}>{opt.label}</option>
                      ))}
                    </select>
                  )}
                </div>
              </ConfigField>

              {/* Persona */}
              <ConfigField
                label="Persona da Matéria"
                icon={<User size={18} />}
                tooltip={tooltips.persona}
              >
                <div className="space-y-2">
                  {personaOptions.map(opt => (
                    <label
                      key={opt.id}
                      className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                        persona === opt.id
                          ? 'bg-orange-50 border border-tmc-orange'
                          : 'bg-off-white hover:bg-gray-100'
                      }`}
                    >
                      <input
                        type="radio"
                        name="persona"
                        value={opt.id}
                        checked={persona === opt.id}
                        onChange={(e) => setPersona(e.target.value)}
                        className="w-4 h-4 mt-0.5 text-tmc-orange focus:ring-tmc-orange"
                      />
                      <div>
                        <span className="text-sm font-medium text-dark-gray">{opt.label}</span>
                        <p className="text-xs text-medium-gray">{opt.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </ConfigField>

              {/* Tom */}
              <ConfigField
                label="Tom da Escrita"
                icon={<Palette size={18} />}
                tooltip={tooltips.tom}
              >
                <select
                  value={tom}
                  onChange={(e) => setTom(e.target.value)}
                  className="w-full px-4 py-2.5 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                >
                  {tomOptions.map(opt => (
                    <option key={opt.id} value={opt.id}>{opt.label}</option>
                  ))}
                </select>
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

          {/* Right Column - Complementary Materials */}
          <div className="bg-white border border-light-gray rounded-xl p-6">
            <h2 className="text-lg font-semibold text-dark-gray mb-2 flex items-center gap-2">
              <Plus size={20} className="text-tmc-orange" />
              Materiais Complementares
            </h2>
            <p className="text-sm text-medium-gray mb-6">
              Adicione fontes extras para enriquecer a matéria
            </p>

            <div className="space-y-6">
              {/* Link da Web */}
              <ConfigField
                label="Link da Web"
                icon={<Link size={18} />}
                tooltip={tooltips.linkWeb}
              >
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <input
                      type="url"
                      value={novoLink}
                      onChange={(e) => setNovoLink(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAddLink()}
                      placeholder="https://exemplo.com/noticia..."
                      className="flex-1 px-4 py-2.5 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                    />
                    <button
                      onClick={handleAddLink}
                      disabled={!novoLink.trim()}
                      className="px-4 py-2.5 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <Plus size={18} />
                    </button>
                  </div>
                  {links.length > 0 && (
                    <div className="space-y-2">
                      {links.map(link => (
                        <div key={link.id} className="flex items-center gap-2 p-3 bg-off-white rounded-lg">
                          <Link size={14} className="text-tmc-orange flex-shrink-0" />
                          <span className="flex-1 text-sm text-dark-gray truncate">{link.url}</span>
                          <span className="text-xs text-green-600 flex items-center gap-1">
                            <Check size={12} /> Adicionado
                          </span>
                          <button
                            onClick={() => handleRemoveLink(link.id)}
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

              {/* Vídeo YouTube */}
              <ConfigField
                label="Vídeo do YouTube"
                icon={<Youtube size={18} />}
                tooltip={tooltips.videoYoutube}
              >
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <input
                      type="url"
                      value={novoVideo}
                      onChange={(e) => setNovoVideo(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAddVideo()}
                      placeholder="https://youtube.com/watch?v=..."
                      className="flex-1 px-4 py-2.5 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                    />
                    <button
                      onClick={handleAddVideo}
                      disabled={!novoVideo.trim()}
                      className="px-4 py-2.5 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <Plus size={18} />
                    </button>
                  </div>
                  {videos.length > 0 && (
                    <div className="space-y-2">
                      {videos.map(video => (
                        <div key={video.id} className="flex items-center gap-2 p-3 bg-off-white rounded-lg">
                          <Youtube size={14} className="text-red-500 flex-shrink-0" />
                          <span className="flex-1 text-sm text-dark-gray truncate">{video.url}</span>
                          <span className="text-xs text-green-600 flex items-center gap-1">
                            <Check size={12} /> Adicionado
                          </span>
                          <button
                            onClick={() => handleRemoveVideo(video.id)}
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

              {/* Arquivo PDF */}
              <ConfigField
                label="Arquivo PDF"
                icon={<FileUp size={18} />}
                tooltip={tooltips.pdf}
              >
                <div className="space-y-2">
                  <label className="flex items-center justify-center gap-2 px-4 py-4 border-2 border-dashed border-light-gray rounded-lg cursor-pointer hover:border-tmc-orange hover:bg-orange-50/30 transition-colors">
                    <FileUp size={20} className="text-medium-gray" />
                    <span className="text-sm text-medium-gray">Clique para anexar PDF</span>
                    <input
                      type="file"
                      accept=".pdf"
                      multiple
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                  </label>
                  {pdfs.length > 0 && (
                    <div className="space-y-2">
                      {pdfs.map(pdf => (
                        <div key={pdf.id} className="flex items-center gap-2 p-3 bg-off-white rounded-lg">
                          <FileText size={14} className="text-red-600 flex-shrink-0" />
                          <span className="flex-1 text-sm text-dark-gray truncate">{pdf.name}</span>
                          <span className="text-xs text-medium-gray">
                            {(pdf.size / 1024).toFixed(0)} KB
                          </span>
                          <button
                            onClick={() => handleRemovePdf(pdf.id)}
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

              {/* Summary */}
              {materialsCount > 0 && (
                <div className="pt-4 border-t border-light-gray">
                  <p className="text-sm text-medium-gray">
                    <strong className="text-dark-gray">{materialsCount}</strong> {materialsCount === 1 ? 'material adicionado' : 'materiais adicionados'}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

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
