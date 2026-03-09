import { useState, useCallback, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Plus, ExternalLink, FileText, List, AlertCircle, X, RefreshCw, Loader2 } from 'lucide-react';
import {
  SourceBadge,
  ContentStats,
  SelectionToggleBar,
  ModeTabs,
  TopicCard,
  StoryFusionView
} from '../../../components/criar';
import { getArticles, extractTopics } from '../../../services/api';

// Threshold for using Story Fusion View (2 or more articles)
const STORY_FUSION_THRESHOLD = 2;

/**
 * TextoBaseFeed - Variante da pagina Texto-Base para Materias do Feed
 *
 * Permite:
 * - Ver materias selecionadas na etapa anterior
 * - Extrair topicos de cada materia (usando IA)
 * - Selecionar/desselecionar topicos
 * - Alternar entre modo topicos e texto completo
 */

// Fallback function for topic extraction when API fails
const extractTopicsFromArticleFallback = (article, _index) => {
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

// Async function to extract topics using AI API
const extractTopicsWithAI = async (article) => {
  const text = article.content || article.preview || article.title;

  try {
    const result = await extractTopics({ texto: text });

    if (result.topics && result.topics.length > 0) {
      return result.topics.map((topic, i) => ({
        id: `top-${article.id}-${i}`,
        type: topic.type || 'fato',
        text: topic.content || topic.text
      }));
    }
  } catch (err) {
    console.error('Error extracting topics with AI:', err);
  }

  // Fallback to simple extraction if API fails
  return extractTopicsFromArticleFallback(article, 0);
};

// Function to transform articles with topics (initially uses fallback, then updates with AI)
const transformArticlesToMateriasInitial = (articles) => {
  if (!articles || !Array.isArray(articles) || articles.length === 0) {
    return [];
  }

  return articles.map((article, index) => ({
    id: `art-${article.id}`,
    title: article.title,
    source: article.source,
    url: article.url,
    topics: extractTopicsFromArticleFallback(article, index),
    fullText: article.content || article.preview || article.title,
    isLoadingTopics: true
  }));
};

const TextoBaseFeed = ({
  fonte,
  onChangeSource,
  onDataChange,
  savedSelections
}) => {
  // States
  const [materias, setMaterias] = useState([]);
  const [_isExtractingTopics, setIsExtractingTopics] = useState(false);
  const [activeMateria, setActiveMateria] = useState(null);
  const [selectedTopics, setSelectedTopics] = useState(new Set());
  const [activeTab, setActiveTab] = useState('topics');
  const [editedTexts, setEditedTexts] = useState({});
  const [showAddMore, setShowAddMore] = useState(false);
  const [availableArticles, setAvailableArticles] = useState([]);
  const [newSelections, setNewSelections] = useState(new Set());
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState(null);

  // Initialize materias when fonte changes (with fallback topics)
  useEffect(() => {
    // If returning from another step with cached materias, restore instantly
    if (savedSelections?.cachedMaterias?.length > 0) {
      setMaterias(savedSelections.cachedMaterias);
      setActiveMateria(savedSelections.cachedMaterias[0].id);
      if (savedSelections.selectedTopics?.length > 0) {
        setSelectedTopics(new Set(savedSelections.selectedTopics));
      }
      if (savedSelections.editedTexts) {
        setEditedTexts(savedSelections.editedTexts);
      }
      return;
    }

    // First visit - transform articles with fallback topics, then AI will extract
    if (fonte?.dados && fonte.dados.length > 0) {
      const initialMaterias = transformArticlesToMateriasInitial(fonte.dados);
      setMaterias(initialMaterias);

      if (initialMaterias.length > 0) {
        setActiveMateria(initialMaterias[0].id);

        // First visit: select all topics by default
        const allTopics = new Set();
        initialMaterias.forEach(m => {
          m.topics.forEach(t => allTopics.add(t.id));
        });
        setSelectedTopics(allTopics);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fonte?.dados]);

  // Extract topics with AI after initial load
  useEffect(() => {
    const extractAllTopics = async () => {
      if (!fonte?.dados || fonte.dados.length === 0) return;

      setIsExtractingTopics(true);

      try {
        // Process articles one by one to avoid overwhelming the API
        const updatedMaterias = [...materias];

        for (let i = 0; i < fonte.dados.length; i++) {
          const article = fonte.dados[i];
          const aiTopics = await extractTopicsWithAI(article);

          // Update the materia with AI-extracted topics
          const materiaIndex = updatedMaterias.findIndex(m => m.id === `art-${article.id}`);
          if (materiaIndex >= 0) {
            updatedMaterias[materiaIndex] = {
              ...updatedMaterias[materiaIndex],
              topics: aiTopics,
              isLoadingTopics: false
            };

            // Update state incrementally for better UX
            setMaterias([...updatedMaterias]);

            // Update selected topics to include new AI topics
            setSelectedTopics(prev => {
              const newSet = new Set(prev);
              aiTopics.forEach(t => newSet.add(t.id));
              return newSet;
            });
          }
        }
      } catch (err) {
        console.error('Error extracting topics:', err);
      } finally {
        setIsExtractingTopics(false);
      }
    };

    // Only run if we have materias with isLoadingTopics=true
    if (materias.some(m => m.isLoadingTopics)) {
      extractAllTopics();
    }
  }, [materias.length]); // Only run when materias array length changes

  // Carregar artigos disponíveis do API (excluindo já selecionados)
  const loadAvailableArticles = useCallback(async () => {
    if (!fonte?.dados) return;

    setIsLoadingMore(true);
    setLoadMoreError(null);

    try {
      const response = await getArticles({ limit: 50 });
      const allArticles = (response?.articles || []).map(article => ({
        id: article.id,
        title: article.title,
        preview: article.summary || article.content?.substring(0, 200) || '',
        content: article.content,
        category: article.category || 'Geral',
        source: article.source_name || article.source,
        url: article.link || article.url,
        favicon: article.favicon_url || `https://www.google.com/s2/favicons?domain=${new URL(article.link || article.url || 'https://example.com').hostname}`,
        publishedAt: article.published_at ? new Date(article.published_at) : new Date(),
        tags: article.tags || []
      }));

      const selectedIds = new Set(fonte.dados.map(article => article.id));
      const available = allArticles.filter(article => !selectedIds.has(article.id));
      setAvailableArticles(available);
    } catch (err) {
      console.error('Error loading available articles:', err);
      setLoadMoreError(err.message || 'Erro ao carregar matérias');
    } finally {
      setIsLoadingMore(false);
    }
  }, [fonte?.dados]);

  // Carregar artigos quando showAddMore for ativado
  useEffect(() => {
    if (showAddMore && availableArticles.length === 0 && !isLoadingMore) {
      loadAvailableArticles();
    }
  }, [showAddMore, availableArticles.length, isLoadingMore, loadAvailableArticles]);

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

  // Notificar mudancas - include actual topic texts for context
  useEffect(() => {
    if (onDataChange) {
      // Build a map of topic ID to actual text content
      const topicTexts = {};
      materias.forEach(materia => {
        materia.topics.forEach(topic => {
          // Use edited text if available, otherwise original
          topicTexts[topic.id] = editedTexts[topic.id] || topic.text;
        });
      });

      const data = {
        selectedTopics: Array.from(selectedTopics),
        editedTexts,
        topicTexts, // Include the actual texts
        wordCount: stats.words
      };

      // Cache materias once AI extraction is complete (for instant restore on return)
      if (materias.length > 0 && materias.every(m => !m.isLoadingTopics)) {
        data.cachedMaterias = materias;
      }

      onDataChange(data);
    }
  }, [selectedTopics, editedTexts, stats.words, materias, onDataChange]);

  // Tabs para modo de visualizacao
  const tabs = [
    { id: 'topics', label: 'Tópicos', icon: <List size={16} /> },
    { id: 'fulltext', label: 'Texto Completo', icon: <FileText size={16} /> }
  ];

  // Determine if we should use Story Fusion View (2+ articles)
  const shouldUseStoryFusion = fonte?.dados?.length >= STORY_FUSION_THRESHOLD;

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

  // Use Story Fusion View for multiple articles (2-3)
  if (shouldUseStoryFusion) {
    return (
      <StoryFusionView
        fonte={fonte}
        onChangeSource={onChangeSource}
        onDataChange={onDataChange}
      />
    );
  }

  // Single article view - use traditional topic extraction
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
                          {materia.source} • {materia.isLoadingTopics ? (
                            <span className="inline-flex items-center gap-1">
                              <Loader2 size={10} className="animate-spin" />
                              Extraindo...
                            </span>
                          ) : (
                            `${selectedCount}/${materia.topics.length} tópicos`
                          )}
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

                {/* Loading state */}
                {isLoadingMore && (
                  <div className="flex items-center justify-center py-6">
                    <RefreshCw size={20} className="text-tmc-orange animate-spin mr-2" />
                    <span className="text-sm text-medium-gray">Carregando...</span>
                  </div>
                )}

                {/* Error state */}
                {loadMoreError && !isLoadingMore && (
                  <div className="text-center py-4">
                    <p className="text-sm text-red-500 mb-2">{loadMoreError}</p>
                    <button
                      onClick={loadAvailableArticles}
                      className="text-sm text-tmc-orange hover:underline"
                    >
                      Tentar novamente
                    </button>
                  </div>
                )}

                {/* Articles list */}
                {!isLoadingMore && !loadMoreError && (
                  <>
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
                  </>
                )}
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
                {currentMateria?.url && (
                  <a
                    href={currentMateria.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-tmc-orange hover:underline flex items-center gap-1 text-sm"
                  >
                    <ExternalLink size={14} />
                    Ver original
                  </a>
                )}
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
                  {currentMateria?.isLoadingTopics ? (
                    /* Loading skeleton while AI extracts topics */
                    <div className="space-y-3">
                      <div className="flex items-center gap-3 mb-4">
                        <Loader2 size={18} className="text-tmc-orange animate-spin" />
                        <span className="text-sm text-medium-gray">
                          Extraindo tópicos com IA...
                        </span>
                      </div>
                      {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} className="animate-pulse border border-light-gray rounded-lg p-4">
                          <div className="flex items-start gap-3">
                            <div className="w-4 h-4 bg-gray-200 rounded mt-0.5" />
                            <div className="flex-1 space-y-2">
                              <div className="flex items-center gap-2">
                                <div className="w-16 h-5 bg-gray-200 rounded-full" />
                              </div>
                              <div className="h-4 bg-gray-200 rounded w-full" />
                              <div className="h-4 bg-gray-200 rounded w-3/4" />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
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
                  )}
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
  onDataChange: PropTypes.func,
  savedSelections: PropTypes.shape({
    selectedTopics: PropTypes.array,
    editedTexts: PropTypes.object,
    topicTexts: PropTypes.object
  })
};

export default TextoBaseFeed;
