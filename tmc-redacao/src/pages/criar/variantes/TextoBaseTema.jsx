import { useState, useCallback, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Search, Flame, TrendingUp, TrendingDown, Minus, ArrowLeft, Eye, ExternalLink } from 'lucide-react';
import {
  SourceBadge,
  ContentStats,
  SelectionToggleBar
} from '../../../components/criar';
import TipBox from '../../../components/ui/TipBox';

/**
 * TextoBaseTema - Variante da pagina Texto-Base para Tema em Alta
 *
 * Fluxo em duas etapas:
 * 1. Selecionar um tema (grid de cards)
 * 2. Selecionar materias do tema (lista de artigos do RSS)
 */

// Dados mockados de temas
const mockTemas = [
  { id: 't1', name: 'Dólar', trend: 'up', count: 45, sources: ['feed', 'trends'] },
  { id: 't2', name: 'Petrobras', trend: 'up', count: 32, sources: ['feed'] },
  { id: 't3', name: 'Brasil x Argentina', trend: 'stable', count: 28, sources: ['twitter'] },
  { id: 't4', name: 'Selic', trend: 'up', count: 24, sources: ['feed', 'trends'] },
  { id: 't5', name: 'OpenAI', trend: 'up', count: 18, sources: ['trends'] },
  { id: 't6', name: 'Inflação', trend: 'down', count: 15, sources: ['feed'] }
];

// Dados mockados de materias por tema
const mockMaterias = {
  't1': [
    {
      id: 'm1',
      title: 'Dólar atinge R$ 6,20 e renova máxima histórica',
      source: 'G1',
      sourceUrl: 'https://g1.com.br',
      category: 'Economia',
      time: 'há 2 horas',
      preview: 'A moeda americana subiu 1,2% nesta terça-feira, renovando a máxima histórica nominal...',
      wordCount: 450
    },
    {
      id: 'm2',
      title: 'BC intervém no câmbio pela terceira vez na semana',
      source: 'Valor Econômico',
      sourceUrl: 'https://valor.com.br',
      category: 'Mercados',
      time: 'há 3 horas',
      preview: 'Banco Central vendeu US$ 1 bilhão em leilão para tentar conter a alta do dólar...',
      wordCount: 380
    },
    {
      id: 'm3',
      title: 'Especialistas explicam alta do dólar e perspectivas',
      source: 'Estadão',
      sourceUrl: 'https://estadao.com.br',
      category: 'Análise',
      time: 'há 5 horas',
      preview: 'Incertezas fiscais e cenário externo pressionam a moeda americana frente ao real...',
      wordCount: 620
    },
    {
      id: 'm4',
      title: 'Turistas sentem impacto do dólar nas viagens',
      source: 'UOL',
      sourceUrl: 'https://uol.com.br',
      category: 'Comportamento',
      time: 'há 6 horas',
      preview: 'Pacotes internacionais ficam até 30% mais caros com alta da moeda americana...',
      wordCount: 340
    }
  ]
};

// Componente TemaCard
const TemaCard = ({ tema, onClick, selected }) => {
  const trendIcon = {
    up: <TrendingUp size={14} className="text-green-500" />,
    down: <TrendingDown size={14} className="text-red-500" />,
    stable: <Minus size={14} className="text-medium-gray" />
  };

  const trendLabel = {
    up: 'Em alta',
    down: 'Em queda',
    stable: 'Estável'
  };

  // Mostrar indicador de tendência apenas para Google Trends e Twitter (não para Feed RSS)
  const showTrend = tema.sources.includes('trends') || tema.sources.includes('twitter');

  return (
    <button
      onClick={() => onClick(tema)}
      className={`
        w-full p-4 rounded-xl border text-left transition-all
        ${selected
          ? 'border-tmc-orange bg-orange-50 shadow-md'
          : 'border-light-gray bg-white hover:border-tmc-orange/50 hover:shadow-md'
        }
      `}
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-bold text-dark-gray">{tema.name}</h3>
        {showTrend && (
          <div className="flex items-center gap-1 text-xs">
            {trendIcon[tema.trend]}
            <span className={`
              ${tema.trend === 'up' ? 'text-green-500' : ''}
              ${tema.trend === 'down' ? 'text-red-500' : ''}
              ${tema.trend === 'stable' ? 'text-medium-gray' : ''}
            `}>
              {trendLabel[tema.trend]}
            </span>
          </div>
        )}
      </div>

      <p className="text-sm text-medium-gray mb-3">
        {tema.count} matérias disponíveis
      </p>

      <div className="flex flex-wrap gap-2">
        {tema.sources.includes('feed') && (
          <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
            Feed RSS
          </span>
        )}
        {tema.sources.includes('trends') && (
          <span className="text-xs px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full">
            Google Trends
          </span>
        )}
        {tema.sources.includes('twitter') && (
          <span className="text-xs px-2 py-0.5 bg-cyan-100 text-cyan-700 rounded-full">
            Twitter/X
          </span>
        )}
      </div>
    </button>
  );
};

// Componente ArticleCard
const ArticleCard = ({ article, selected, onToggle, onPreview }) => {
  return (
    <div
      className={`
        p-4 rounded-xl border transition-all cursor-pointer
        ${selected
          ? 'border-tmc-orange bg-orange-50'
          : 'border-light-gray bg-white hover:border-tmc-orange/50'
        }
      `}
      onClick={() => onToggle(article.id)}
    >
      <div className="flex items-start gap-3">
        {/* Checkbox */}
        <div
          className={`
            w-5 h-5 rounded border-2 flex-shrink-0 mt-0.5
            flex items-center justify-center
            ${selected
              ? 'bg-tmc-orange border-tmc-orange'
              : 'border-medium-gray'
            }
          `}
        >
          {selected && (
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </div>

        {/* Conteudo */}
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-dark-gray mb-1 leading-tight">
            {article.title}
          </h4>

          <div className="flex items-center gap-2 text-xs text-medium-gray mb-2">
            <span className="flex items-center gap-1">
              <ExternalLink size={12} />
              {article.source}
            </span>
            <span>•</span>
            <span>{article.time}</span>
            <span>•</span>
            <span className="text-tmc-orange">{article.category}</span>
          </div>

          <p className="text-sm text-medium-gray line-clamp-2">
            {article.preview}
          </p>
        </div>

        {/* Acoes */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onPreview(article);
          }}
          className="p-2 text-medium-gray hover:text-tmc-orange hover:bg-tmc-orange/10 rounded-lg transition-colors"
          title="Visualizar"
        >
          <Eye size={18} />
        </button>
      </div>
    </div>
  );
};

const TextoBaseTema = ({
  fonte,
  onChangeSource,
  onDataChange,
  onSkipToConfig,
  onContinueWithArticles,
  initialTemaData
}) => {
  // Etapa atual: 'tema' ou 'materias'
  const [step, setStep] = useState('tema');
  const [selectedTema, setSelectedTema] = useState(null);
  const [selectedArticles, setSelectedArticles] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState('all'); // all, feed, trends, twitter
  const [previewArticle, setPreviewArticle] = useState(null);

  // Restaurar estado do tema se houver dados iniciais (voltando da edição de tópicos)
  useEffect(() => {
    if (initialTemaData?.tema) {
      setSelectedTema(initialTemaData.tema);
      setStep('materias');
      if (initialTemaData.selectedArticleIds) {
        setSelectedArticles(new Set(initialTemaData.selectedArticleIds));
      }
    }
  }, [initialTemaData]);

  // Se vier com tema pre-selecionado, ir direto para materias
  // Se fonte.dados estiver vazio, mostrar seleção de temas
  useEffect(() => {
    // Se há dados iniciais (voltando da edição), não processar fonte
    if (initialTemaData?.tema) {
      return;
    }

    const temaData = fonte?.dados;

    // Se não houver dados ou dados estiverem vazios, ficar na seleção de tema
    if (!temaData || Object.keys(temaData).length === 0) {
      setStep('tema');
      return;
    }

    // Se fonte.dados tem um 'name' ou 'id', é o objeto tema diretamente
    if (temaData.name || temaData.id) {
      // Tentar encontrar o tema nos mocks pelo id ou nome
      const tema = mockTemas.find(t =>
        t.id === temaData.id ||
        t.name === temaData.name ||
        t.name === temaData.tema
      );
      if (tema) {
        setSelectedTema(tema);
        setStep('materias');
      } else {
        // Se não encontrou nos mocks, criar um tema baseado nos dados recebidos
        setSelectedTema({
          id: temaData.id || `temp-${Date.now()}`,
          name: temaData.name || temaData.tema || 'Tema Selecionado',
          trend: temaData.trend || 'stable',
          count: temaData.count || 0,
          sources: temaData.sources || ['feed']
        });
        setStep('materias');
      }
    }
  }, [fonte, initialTemaData]);

  // Filtrar temas
  const filteredTemas = useMemo(() => {
    return mockTemas.filter(tema => {
      if (searchQuery) {
        if (!tema.name.toLowerCase().includes(searchQuery.toLowerCase())) {
          return false;
        }
      }
      if (sourceFilter !== 'all' && !tema.sources.includes(sourceFilter)) {
        return false;
      }
      return true;
    });
  }, [searchQuery, sourceFilter]);

  // Materias do tema selecionado
  const materias = useMemo(() => {
    if (!selectedTema) return [];
    return mockMaterias[selectedTema.id] || [];
  }, [selectedTema]);

  // Estatisticas
  const stats = useMemo(() => {
    let wordCount = 0;
    selectedArticles.forEach(id => {
      const article = materias.find(m => m.id === id);
      if (article) {
        wordCount += article.wordCount;
      }
    });

    return {
      selected: selectedArticles.size,
      total: materias.length,
      words: wordCount
    };
  }, [selectedArticles, materias]);

  // Handlers
  const handleSelectTema = useCallback((tema) => {
    setSelectedTema(tema);
    setSelectedArticles(new Set());
    setStep('materias');
  }, []);

  const handleBackToTemas = useCallback(() => {
    setStep('tema');
    setSelectedTema(null);
    setSelectedArticles(new Set());
  }, []);

  const handleToggleArticle = useCallback((articleId) => {
    setSelectedArticles(prev => {
      const newSet = new Set(prev);
      if (newSet.has(articleId)) {
        newSet.delete(articleId);
      } else {
        newSet.add(articleId);
      }
      return newSet;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedArticles(new Set(materias.map(m => m.id)));
  }, [materias]);

  const handleClearSelection = useCallback(() => {
    setSelectedArticles(new Set());
  }, []);

  // Notificar mudancas
  useEffect(() => {
    if (onDataChange) {
      onDataChange({
        tema: selectedTema,
        selectedArticles: Array.from(selectedArticles),
        wordCount: stats.words
      });
    }
  }, [selectedTema, selectedArticles, stats.words, onDataChange]);

  // Etapa 1: Selecao de tema
  if (step === 'tema') {
    return (
      <div className="space-y-6">
        <SourceBadge
          type="tema"
          title="Tema em Alta"
          onChangeSource={onChangeSource}
        />

        <div className="bg-white rounded-xl border border-light-gray p-6">
          <div className="flex items-center gap-2 mb-6">
            <Flame size={24} className="text-tmc-orange" />
            <h2 className="text-xl font-bold text-dark-gray">
              Escolha o Tema para sua Matéria
            </h2>
          </div>

          {/* Busca */}
          <div className="relative mb-4">
            <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-medium-gray" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar tema..."
              className="w-full pl-10 pr-4 py-2 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
            />
          </div>

          {/* Filtros de fonte */}
          <div className="flex gap-2 mb-6">
            {['all', 'feed', 'trends', 'twitter'].map(filter => (
              <button
                key={filter}
                onClick={() => setSourceFilter(filter)}
                className={`
                  px-4 py-2 text-sm rounded-lg border transition-colors
                  ${sourceFilter === filter
                    ? 'bg-tmc-orange text-white border-tmc-orange'
                    : 'bg-white text-medium-gray border-light-gray hover:border-tmc-orange'
                  }
                `}
              >
                {filter === 'all' ? 'Todos' : filter === 'feed' ? 'Feed RSS' : filter === 'trends' ? 'Google Trends' : 'Twitter/X'}
              </button>
            ))}
          </div>

          {/* Grid de temas */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTemas.map(tema => (
              <TemaCard
                key={tema.id}
                tema={tema}
                onClick={handleSelectTema}
                selected={selectedTema?.id === tema.id}
              />
            ))}
          </div>

          {filteredTemas.length === 0 && (
            <div className="text-center py-8 text-medium-gray">
              <p>Nenhum tema encontrado</p>
            </div>
          )}

          {/* Dica */}
          <TipBox className="mt-6">
            Selecione um tema para ver matérias relacionadas dos seus feeds configurados.
          </TipBox>
        </div>
      </div>
    );
  }

  // Etapa 2: Selecao de materias
  return (
    <div className="space-y-6">
      <SourceBadge
        type="tema"
        title={`Tema: ${selectedTema?.name}`}
        subtitle={`${materias.length} matérias disponíveis`}
        onChangeSource={handleBackToTemas}
      />

      <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-light-gray">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={handleBackToTemas}
              className="flex items-center gap-2 text-medium-gray hover:text-tmc-orange transition-colors"
            >
              <ArrowLeft size={16} />
              <span className="text-sm">Trocar Tema</span>
            </button>
          </div>

          <h2 className="text-lg font-bold text-dark-gray mb-4">
            Matérias sobre "{selectedTema?.name}"
          </h2>

          {/* Controles de selecao */}
          <SelectionToggleBar
            selectedCount={selectedArticles.size}
            totalCount={materias.length}
            onSelectAll={handleSelectAll}
            onClearSelection={handleClearSelection}
          />
        </div>

        {/* Lista de materias */}
        <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
          {materias.map(article => (
            <ArticleCard
              key={article.id}
              article={article}
              selected={selectedArticles.has(article.id)}
              onToggle={handleToggleArticle}
              onPreview={setPreviewArticle}
            />
          ))}
        </div>

        {/* Footer com stats */}
        <ContentStats
          selectedCount={stats.selected}
          totalCount={stats.total}
          wordCount={stats.words}
          variant="tema"
        />
      </div>

      {/* Botões de ação */}
      <div className="flex flex-col items-center gap-3 mt-6">
        {/* Continuar - aparece quando tem matérias selecionadas */}
        {selectedArticles.size > 0 && onContinueWithArticles && (
          <button
            onClick={() => {
              const selectedMaterias = materias.filter(m => selectedArticles.has(m.id));
              onContinueWithArticles(selectedMaterias, selectedTema);
            }}
            className="px-6 py-3 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium"
          >
            Continuar com {selectedArticles.size} matéria(s) selecionada(s)
          </button>
        )}

        {/* Pular - sempre disponível */}
        {onSkipToConfig && (
          <button
            onClick={onSkipToConfig}
            className="text-medium-gray hover:text-tmc-orange text-sm"
          >
            {selectedArticles.size > 0
              ? 'Ou pular edição e ir direto para Configurações'
              : 'Pular seleção de matérias e ir direto para Configurações →'
            }
          </button>
        )}
      </div>
    </div>
  );
};

TextoBaseTema.propTypes = {
  fonte: PropTypes.shape({
    tipo: PropTypes.string,
    dados: PropTypes.shape({
      tema: PropTypes.string
    })
  }),
  onChangeSource: PropTypes.func,
  onDataChange: PropTypes.func,
  onSkipToConfig: PropTypes.func,
  onContinueWithArticles: PropTypes.func,
  initialTemaData: PropTypes.shape({
    tema: PropTypes.object,
    selectedArticleIds: PropTypes.arrayOf(PropTypes.string)
  })
};

export default TextoBaseTema;
