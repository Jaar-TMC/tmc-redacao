import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, HelpCircle, FileText, ChevronDown, ChevronUp,
  Link, Youtube, File, User, Palette, Building2, Calendar,
  MessageSquare, Edit, Sparkles, Check
} from 'lucide-react';
import { Stepper } from '../../components/criar';

/**
 * RevisarPage - Etapa 3.5 do fluxo de criação de matéria
 *
 * Permite ao usuário revisar todos os conteúdos e configurações
 * antes de gerar a matéria.
 */

// Mock data - Em produção viria do contexto/estado global
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
    persona: 'Jornalista Imparcial',
    tom: 'Formal',
    creditos: 'Agência Brasil',
    dataBase: '18/12/2024',
    orientacaoLide: 'Focar no impacto econômico para o cidadão comum',
    citacoes: 1,
    instrucoes: 'Evitar termos técnicos, manter parágrafos curtos'
  }
};

const RevisarPage = () => {
  const navigate = useNavigate();

  // State
  const [expandedSections, setExpandedSections] = useState({
    textoBase: false,
    materiais: {}
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationMessage, setGenerationMessage] = useState('');

  // Generation messages
  const generationMessages = [
    'Analisando texto-base e fontes complementares...',
    'Identificando informações principais...',
    'Aplicando persona e tom selecionados...',
    'Estruturando lide conforme orientação...',
    'Incorporando citações e declarações...',
    'Gerando parágrafos do corpo da matéria...',
    'Otimizando para legibilidade e SEO...',
    'Finalizando e revisando estrutura...'
  ];

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

  const handleGenerate = useCallback(() => {
    setIsGenerating(true);
    setGenerationProgress(0);
    setGenerationMessage(generationMessages[0]);

    // Simulate generation progress
    const interval = setInterval(() => {
      setGenerationProgress(prev => {
        const newProgress = prev + Math.random() * 15;
        if (newProgress >= 100) {
          clearInterval(interval);
          setTimeout(() => {
            navigate('/criar/editor');
          }, 500);
          return 100;
        }
        // Update message based on progress
        const messageIndex = Math.floor((newProgress / 100) * generationMessages.length);
        setGenerationMessage(generationMessages[Math.min(messageIndex, generationMessages.length - 1)]);
        return newProgress;
      });
    }, 800);
  }, [navigate, generationMessages]);

  const handleStepClick = useCallback((stepIndex) => {
    const routes = ['/criar', '/criar/texto-base', '/criar/configurar', '/criar/editor'];
    if (stepIndex < 2) {
      navigate(routes[stepIndex]);
    }
  }, [navigate]);

  const totalWords = mockReviewData.textoBase.words +
    mockReviewData.materiais.reduce((acc, m) => acc + (m.words || 0), 0);

  // Generation Overlay
  if (isGenerating) {
    return (
      <div className="min-h-screen bg-dark-gray/95 flex items-center justify-center">
        <div className="text-center max-w-md">
          {/* Animated Icon */}
          <div className="relative w-24 h-24 mx-auto mb-8">
            <div className="absolute inset-0 bg-tmc-orange/20 rounded-full animate-ping" />
            <div className="absolute inset-2 bg-tmc-orange/40 rounded-full animate-pulse" />
            <div className="absolute inset-4 bg-tmc-orange rounded-full flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-white animate-pulse" />
            </div>
          </div>

          <h2 className="text-2xl font-bold text-white mb-4">
            Gerando sua matéria...
          </h2>

          <p className="text-medium-gray mb-8 min-h-[48px]">
            {generationMessage}
          </p>

          {/* Progress Bar */}
          <div className="w-full bg-gray-700 rounded-full h-2 mb-4">
            <div
              className="bg-tmc-orange h-2 rounded-full transition-all duration-500"
              style={{ width: `${generationProgress}%` }}
            />
          </div>

          <p className="text-sm text-medium-gray">
            {Math.round(generationProgress)}% • Tempo estimado: ~25 segundos
          </p>
        </div>
      </div>
    );
  }

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
                    <p className="text-sm text-medium-gray">{mockReviewData.textoBase.type}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm text-dark-gray">{mockReviewData.textoBase.blocks} blocos</p>
                    <p className="text-xs text-medium-gray">~{mockReviewData.textoBase.words} palavras</p>
                  </div>
                  {expandedSections.textoBase ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </div>
              </button>

              {expandedSections.textoBase && (
                <div className="border-t border-light-gray p-4 bg-off-white/30">
                  <p className="text-sm text-dark-gray leading-relaxed mb-4">
                    {mockReviewData.textoBase.content}
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
            {mockReviewData.materiais.map(material => (
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
                {1 + mockReviewData.materiais.length} (texto-base + {mockReviewData.materiais.length} complementares)
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
                  <p className="text-xs text-medium-gray">Persona</p>
                  <p className="text-sm font-medium text-dark-gray">{mockReviewData.configuracoes.persona}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Palette size={18} className="text-tmc-orange" />
                <div>
                  <p className="text-xs text-medium-gray">Tom</p>
                  <p className="text-sm font-medium text-dark-gray">{mockReviewData.configuracoes.tom}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Building2 size={18} className="text-tmc-orange" />
                <div>
                  <p className="text-xs text-medium-gray">Créditos</p>
                  <p className="text-sm font-medium text-dark-gray">{mockReviewData.configuracoes.creditos}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Calendar size={18} className="text-tmc-orange" />
                <div>
                  <p className="text-xs text-medium-gray">Data base</p>
                  <p className="text-sm font-medium text-dark-gray">{mockReviewData.configuracoes.dataBase}</p>
                </div>
              </div>

              <div className="border-t border-light-gray pt-4">
                <div className="flex items-start gap-3">
                  <FileText size={18} className="text-tmc-orange mt-0.5" />
                  <div>
                    <p className="text-xs text-medium-gray">Orientação do lide</p>
                    <p className="text-sm text-dark-gray">&quot;{mockReviewData.configuracoes.orientacaoLide}&quot;</p>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <MessageSquare size={18} className="text-tmc-orange" />
                <div>
                  <p className="text-xs text-medium-gray">Citações</p>
                  <p className="text-sm font-medium text-dark-gray">{mockReviewData.configuracoes.citacoes} citação adicionada</p>
                </div>
              </div>

              {mockReviewData.configuracoes.instrucoes && (
                <div className="border-t border-light-gray pt-4">
                  <div className="flex items-start gap-3">
                    <Edit size={18} className="text-tmc-orange mt-0.5" />
                    <div>
                      <p className="text-xs text-medium-gray">Instruções</p>
                      <p className="text-sm text-dark-gray">&quot;{mockReviewData.configuracoes.instrucoes}&quot;</p>
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
