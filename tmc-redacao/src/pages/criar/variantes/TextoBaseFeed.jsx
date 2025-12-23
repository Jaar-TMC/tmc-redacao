import { useState, useCallback, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Plus, ExternalLink, FileText, List, AlertCircle, X } from 'lucide-react';
import {
  SourceBadge,
  ContentStats,
  SelectionToggleBar,
  ModeTabs,
  TopicCard
} from '../../../components/criar';
import { mockArticles } from '../../../data/mockData';

/**
 * TextoBaseFeed - Variante da pagina Texto-Base para Materias do Feed
 *
 * Permite:
 * - Ver materias selecionadas na etapa anterior
 * - Extrair topicos de cada materia
 * - Selecionar/desselecionar topicos
 * - Alternar entre modo topicos e texto completo
 */

// Função para extrair tópicos simulados de um artigo
const extractTopicsFromArticle = (article, index) => {
  // Em produção, isso seria feito por IA. Por ora, criamos tópicos a partir do preview/content
  const baseTopics = [
    { type: 'fato', prefix: 'Fato principal: ' },
    { type: 'contexto', prefix: 'Contexto: ' },
    { type: 'detalhe', prefix: 'Detalhe relevante: ' }
  ];

  const text = article.preview || article.content || article.title;
  const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 10);

  return baseTopics.slice(0, Math.min(sentences.length, 3)).map((topicType, i) => ({
    id: `top-${article.id}-${i}`,
    type: topicType.type,
    text: sentences[i]?.trim() || `${topicType.prefix}${article.title}`
  }));
};

// Função para transformar artigos da Redação em formato com tópicos
const transformArticlesToMaterias = (articles) => {
  if (!articles || !Array.isArray(articles) || articles.length === 0) {
    return [];
  }

  return articles.map((article, index) => ({
    id: `art-${article.id}`,
    title: article.title,
    source: article.source,
    topics: extractTopicsFromArticle(article, index),
    fullText: article.content || article.preview || article.title
  }));
};

const TextoBaseFeed = ({
  fonte,
  onChangeSource,
  onDataChange
}) => {
  // Transforma os artigos da fonte em matérias com tópicos
  const materias = useMemo(() => {
    return transformArticlesToMaterias(fonte?.dados);
  }, [fonte?.dados]);

  // States
  const [activeMateria, setActiveMateria] = useState(null);
  const [selectedTopics, setSelectedTopics] = useState(new Set());
  const [activeTab, setActiveTab] = useState('topics');
  const [editedTexts, setEditedTexts] = useState({});
  const [showAddMore, setShowAddMore] = useState(false);
  const [availableArticles, setAvailableArticles] = useState([]);
  const [newSelections, setNewSelections] = useState(new Set());

  // Inicializar quando matérias carregarem
  useEffect(() => {
    if (materias.length > 0 && !activeMateria) {
      setActiveMateria(materias[0].id);
      // Seleciona todos os tópicos por padrão
      const allTopics = new Set();
      materias.forEach(m => {
        m.topics.forEach(t => allTopics.add(t.id));
      });
      setSelectedTopics(allTopics);
    }
  }, [materias, activeMateria]);

  // Carregar artigos disponíveis (excluindo já selecionados)
  useEffect(() => {
    if (!fonte?.dados) return;

    const selectedIds = new Set(fonte.dados.map(article => article.id));
    const available = mockArticles.filter(article => !selectedIds.has(article.id));
    setAvailableArticles(available);
  }, [fonte?.dados]);

  // Materia ativa
  const currentMateria = useMemo(() => {
    return materias.find(m => m.id === activeMateria);
  }, [materias, activeMateria]);

  // Estatisticas
  const stats = useMemo(() => {
    let totalTopics = 0;
    let selectedCount = 0;
    let wordCount = 0;

    materias.forEach(materia => {
      totalTopics += materia.topics.length;
      materia.topics.forEach(topic => {
        if (selectedTopics.has(topic.id)) {
          selectedCount++;
          wordCount += topic.text.split(/\s+/).filter(Boolean).length;
        }
      });
    });

    return {
      selected: selectedCount,
      total: totalTopics,
      words: wordCount,
      sources: materias.length
    };
  }, [materias, selectedTopics]);

  // Handlers
  const handleToggleTopic = useCallback((topicId) => {
    setSelectedTopics(prev => {
      const newSet = new Set(prev);
      if (newSet.has(topicId)) {
        newSet.delete(topicId);
      } else {
        newSet.add(topicId);
      }
      return newSet;
    });
  }, []);

  const handleEditTopic = useCallback((topicId, newText) => {
    setEditedTexts(prev => ({
      ...prev,
      [topicId]: newText
    }));
  }, []);

  const handleSelectAllTopics = useCallback(() => {
    if (!currentMateria) return;
    const newSet = new Set(selectedTopics);
    currentMateria.topics.forEach(t => newSet.add(t.id));
    setSelectedTopics(newSet);
  }, [currentMateria, selectedTopics]);

  const handleClearMateriaTopics = useCallback(() => {
    if (!currentMateria) return;
    const newSet = new Set(selectedTopics);
    currentMateria.topics.forEach(t => newSet.delete(t.id));
    setSelectedTopics(newSet);
  }, [currentMateria, selectedTopics]);

  // Notificar mudancas
  useEffect(() => {
    if (onDataChange) {
      onDataChange({
        selectedTopics: Array.from(selectedTopics),
        editedTexts,
        wordCount: stats.words
      });
    }
  }, [selectedTopics, editedTexts, stats.words, onDataChange]);

  // Tabs para modo de visualizacao
  const tabs = [
    { id: 'topics', label: 'Tópicos', icon: <List size={16} /> },
    { id: 'fulltext', label: 'Texto Completo', icon: <FileText size={16} /> }
  ];

  // Estado vazio - sem matérias
  if (materias.length === 0) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-light-gray p-8 text-center">
          <div className="w-16 h-16 bg-off-white rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle size={32} className="text-medium-gray" />
          </div>
          <h3 className="font-semibold text-dark-gray mb-2">
            Nenhuma matéria selecionada
          </h3>
          <p className="text-sm text-medium-gray mb-4">
            Volte para a tela de Redação e selecione as matérias que deseja usar como base.
          </p>
          <button
            onClick={onChangeSource}
            className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium"
          >
            Selecionar matérias
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SourceBadge
        type="feed"
        title={`${materias.length} matérias do Feed selecionadas`}
        onChangeSource={onChangeSource}
      />

      {/* Layout duas colunas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Coluna esquerda - Lista de materias */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-light-gray p-4">
            <h3 className="font-semibold text-dark-gray mb-4">
              Matérias Selecionadas
            </h3>

            <div className="space-y-2">
              {materias.map(materia => {
                const selectedCount = materia.topics.filter(t => selectedTopics.has(t.id)).length;
                const isActive = materia.id === activeMateria;

                return (
                  <button
                    key={materia.id}
                    onClick={() => setActiveMateria(materia.id)}
                    className={`
                      w-full p-3 rounded-lg text-left transition-all
                      ${isActive
                        ? 'bg-tmc-orange/10 border border-tmc-orange'
                        : 'bg-off-white border border-transparent hover:border-light-gray'
                      }
                    `}
                  >
                    <div className="flex items-start gap-2">
                      <span className={`
                        w-2 h-2 rounded-full mt-2 flex-shrink-0
                        ${isActive ? 'bg-tmc-orange' : 'bg-medium-gray'}
                      `} />
                      <div className="flex-1 min-w-0">
                        <p className={`
                          text-sm font-medium line-clamp-2
                          ${isActive ? 'text-tmc-orange' : 'text-dark-gray'}
                        `}>
                          {materia.title}
                        </p>
                        <p className="text-xs text-medium-gray mt-1">
                          {materia.source} • {selectedCount}/{materia.topics.length} tópicos
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Botao adicionar mais / Lista de artigos disponíveis */}
            {showAddMore ? (
              <div className="mt-4 border border-light-gray rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-dark-gray text-sm">Adicionar matérias</h4>
                  <button onClick={() => setShowAddMore(false)} className="text-medium-gray hover:text-dark-gray">
                    <X size={16} />
                  </button>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {availableArticles.map(article => (
                    <label key={article.id} className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer ${newSelections.has(article.id) ? 'bg-orange-50' : 'hover:bg-off-white'}`}>
                      <input
                        type="checkbox"
                        checked={newSelections.has(article.id)}
                        onChange={() => {
                          const newSet = new Set(newSelections);
                          if (newSet.has(article.id)) newSet.delete(article.id);
                          else newSet.add(article.id);
                          setNewSelections(newSet);
                        }}
                        className="w-4 h-4 text-tmc-orange rounded"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-dark-gray line-clamp-1">{article.title}</p>
                        <p className="text-xs text-medium-gray">{article.source}</p>
                      </div>
                    </label>
                  ))}
                </div>
                {availableArticles.length === 0 && (
                  <p className="text-sm text-medium-gray text-center py-4">Não há mais matérias disponíveis</p>
                )}
                <button
                  onClick={() => {
                    // Adicionar matérias selecionadas
                    const newArticles = availableArticles.filter(a => newSelections.has(a.id));
                    if (onDataChange && newArticles.length > 0) {
                      onDataChange({ type: 'addArticles', articles: newArticles });
                    }
                    setShowAddMore(false);
                    setNewSelections(new Set());
                  }}
                  disabled={newSelections.size === 0}
                  className="w-full mt-3 py-2 bg-tmc-orange text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                >
                  Adicionar {newSelections.size} matéria(s)
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowAddMore(true)}
                className="w-full mt-4 p-3 border border-dashed border-light-gray rounded-lg text-medium-gray hover:border-tmc-orange hover:text-tmc-orange transition-colors flex items-center justify-center gap-2"
              >
                <Plus size={16} />
                <span className="text-sm">Adicionar mais matérias</span>
              </button>
            )}
          </div>
        </div>

        {/* Coluna direita - Conteudo extraido */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-light-gray">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-dark-gray">
                    {currentMateria?.source}
                  </h3>
                  <p className="text-sm text-medium-gray line-clamp-1">
                    {currentMateria?.title}
                  </p>
                </div>
                <a
                  href="#"
                  className="text-tmc-orange hover:underline flex items-center gap-1 text-sm"
                >
                  <ExternalLink size={14} />
                  Ver original
                </a>
              </div>

              {/* Tabs */}
              <ModeTabs
                activeTab={activeTab}
                onTabChange={setActiveTab}
                tabs={tabs}
              />
            </div>

            {/* Conteudo */}
            <div className="p-4">
              {activeTab === 'topics' ? (
                <>
                  {/* Controles de selecao */}
                  <SelectionToggleBar
                    selectedCount={currentMateria?.topics.filter(t => selectedTopics.has(t.id)).length || 0}
                    totalCount={currentMateria?.topics.length || 0}
                    onSelectAll={handleSelectAllTopics}
                    onClearSelection={handleClearMateriaTopics}
                    className="mb-4"
                  />

                  {/* Lista de topicos */}
                  <div className="space-y-3 max-h-[400px] overflow-y-auto">
                    {currentMateria?.topics.map(topic => (
                      <TopicCard
                        key={topic.id}
                        id={topic.id}
                        type={topic.type}
                        text={editedTexts[topic.id] || topic.text}
                        source={currentMateria.source}
                        selected={selectedTopics.has(topic.id)}
                        onToggle={handleToggleTopic}
                        onEdit={handleEditTopic}
                        expandable
                      />
                    ))}
                  </div>
                </>
              ) : (
                <div>
                  <label className="flex items-center gap-2 mb-2">
                    <input
                      type="checkbox"
                      className="w-4 h-4 rounded border-medium-gray text-tmc-orange focus:ring-tmc-orange"
                    />
                    <span className="text-sm text-dark-gray">Incluir texto completo</span>
                  </label>

                  <textarea
                    value={currentMateria?.fullText || ''}
                    onChange={() => {}}
                    className="w-full h-64 p-4 border border-light-gray rounded-lg resize-none text-sm text-dark-gray leading-relaxed focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                    placeholder="Texto completo da matéria..."
                  />

                  <p className="text-xs text-medium-gray mt-2">
                    💡 Edite o texto livremente. Alterações serão usadas na geração da matéria.
                  </p>
                </div>
              )}
            </div>

            {/* Footer com stats */}
            <ContentStats
              selectedCount={stats.selected}
              totalCount={stats.total}
              wordCount={stats.words}
              sourceCount={stats.sources}
              variant="feed"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

TextoBaseFeed.propTypes = {
  fonte: PropTypes.shape({
    tipo: PropTypes.string,
    dados: PropTypes.array
  }),
  onChangeSource: PropTypes.func,
  onDataChange: PropTypes.func
};

export default TextoBaseFeed;
