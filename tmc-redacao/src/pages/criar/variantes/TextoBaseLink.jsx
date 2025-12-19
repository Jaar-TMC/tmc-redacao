import { useState, useCallback, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import { ExternalLink, RefreshCw, FileText, List, Globe, Calendar, User, Hash } from 'lucide-react';
import {
  SourceBadge,
  ContentStats,
  SelectionToggleBar,
  ModeTabs,
  TopicCard
} from '../../../components/criar';

/**
 * TextoBaseLink - Variante da pagina Texto-Base para Link da Web
 *
 * Permite:
 * - Ver metadados do link extraido
 * - Ver topicos gerados automaticamente
 * - Selecionar/desselecionar topicos
 * - Editar topicos individualmente
 * - Alternar entre modo topicos e texto completo
 */

// Dados mockados de link extraido
const mockLinkData = {
  url: 'https://g1.globo.com/economia/noticia/dolar-atinge-r-620.html',
  title: 'Dólar atinge R$ 6,20 e renova máxima histórica',
  source: 'G1',
  favicon: '🌐',
  publishedDate: '18/12/2024',
  author: 'Redação G1',
  category: 'Economia',
  wordCount: 850,
  topics: [
    { id: 'link-top-1', type: 'fato', text: 'Dólar comercial fechou cotado a R$ 6,20, com alta de 1,2% em relação ao fechamento do dia anterior' },
    { id: 'link-top-2', type: 'contexto', text: 'O valor representa a maior cotação nominal da história da moeda americana no Brasil' },
    { id: 'link-top-3', type: 'causa', text: 'Movimento reflete incertezas fiscais domésticas e cenário externo de fortalecimento do dólar frente às moedas emergentes' },
    { id: 'link-top-4', type: 'acao', text: 'Banco Central vendeu US$ 1 bilhão em leilão de dólares para tentar conter a alta, mas efeito foi limitado' },
    { id: 'link-top-5', type: 'declaracao', text: '"A expectativa é de estabilização nos próximos dias", afirmou o presidente do BC em nota oficial' }
  ],
  fullText: `A moeda americana subiu 1,2% nesta terça-feira, fechando cotada a R$ 6,20, renovando a máxima histórica nominal. O valor representa o maior patamar nominal já registrado para a moeda americana no Brasil.

O movimento reflete as incertezas fiscais domésticas e o cenário externo de fortalecimento do dólar frente às moedas emergentes. Analistas apontam que a combinação de déficit fiscal crescente e indefinições sobre a política econômica afetam a confiança dos investidores.

O Banco Central vendeu US$ 1 bilhão em leilão de dólares para tentar conter a alta, mas o efeito foi limitado. Foi a terceira intervenção da autoridade monetária no mercado de câmbio apenas nesta semana.

"A expectativa é de estabilização nos próximos dias", afirmou o presidente do BC em nota oficial divulgada após o fechamento do mercado.

Especialistas alertam que, como consequência da alta do dólar, produtos importados devem ficar mais caros nos próximos meses, pressionando a inflação.`
};

const TextoBaseLink = ({
  fonte,
  onChangeSource,
  onDataChange
}) => {
  // States
  const [selectedTopics, setSelectedTopics] = useState(
    () => new Set(mockLinkData.topics.map(t => t.id))
  );
  const [editedTexts, setEditedTexts] = useState({});
  const [activeTab, setActiveTab] = useState('topics');
  const [fullText, setFullText] = useState(mockLinkData.fullText);
  const [isReprocessing, setIsReprocessing] = useState(false);

  // URL da fonte ou mock
  const linkUrl = fonte?.dados?.url || mockLinkData.url;
  const linkTitle = fonte?.dados?.preview?.title || mockLinkData.title;

  // Estatisticas
  const stats = useMemo(() => {
    let wordCount = 0;

    if (activeTab === 'topics') {
      selectedTopics.forEach(id => {
        const topic = mockLinkData.topics.find(t => t.id === id);
        if (topic) {
          const text = editedTexts[id] || topic.text;
          wordCount += text.split(/\s+/).filter(Boolean).length;
        }
      });
    } else {
      wordCount = fullText.split(/\s+/).filter(Boolean).length;
    }

    return {
      selected: selectedTopics.size,
      total: mockLinkData.topics.length,
      words: wordCount
    };
  }, [selectedTopics, editedTexts, activeTab, fullText]);

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

  const handleSelectAll = useCallback(() => {
    setSelectedTopics(new Set(mockLinkData.topics.map(t => t.id)));
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedTopics(new Set());
  }, []);

  const handleReprocess = useCallback(() => {
    setIsReprocessing(true);
    // Simular reprocessamento
    setTimeout(() => {
      setIsReprocessing(false);
    }, 2000);
  }, []);

  // Notificar mudancas
  useEffect(() => {
    if (onDataChange) {
      onDataChange({
        selectedTopics: Array.from(selectedTopics),
        editedTexts,
        fullText: activeTab === 'fulltext' ? fullText : undefined,
        editMode: activeTab,
        wordCount: stats.words
      });
    }
  }, [selectedTopics, editedTexts, activeTab, fullText, stats.words, onDataChange]);

  // Tabs para modo de visualizacao
  const tabs = [
    { id: 'topics', label: 'Tópicos', icon: <List size={16} /> },
    { id: 'fulltext', label: 'Texto Completo', icon: <FileText size={16} /> }
  ];

  return (
    <div className="space-y-6">
      <SourceBadge
        type="link"
        title={new URL(linkUrl).hostname.replace('www.', '')}
        subtitle={linkTitle}
        onChangeSource={onChangeSource}
      />

      {/* Layout duas colunas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Coluna esquerda - Metadados do link */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-light-gray p-4">
            <h3 className="font-semibold text-dark-gray mb-4">
              Informações do Link
            </h3>

            {/* Card de info */}
            <div className="bg-off-white rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 mb-3">
                <Globe size={20} className="text-tmc-orange" />
                <span className="font-medium text-dark-gray">{mockLinkData.source}</span>
              </div>

              <h4 className="font-semibold text-dark-gray mb-3 leading-tight">
                {linkTitle}
              </h4>

              <div className="space-y-2 text-sm text-medium-gray">
                <div className="flex items-center gap-2">
                  <Calendar size={14} />
                  <span>Publicado: {mockLinkData.publishedDate}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Hash size={14} />
                  <span>Categoria: {mockLinkData.category}</span>
                </div>
                <div className="flex items-center gap-2">
                  <User size={14} />
                  <span>Autor: {mockLinkData.author}</span>
                </div>
                <div className="flex items-center gap-2">
                  <FileText size={14} />
                  <span>~{mockLinkData.wordCount} palavras</span>
                </div>
              </div>
            </div>

            {/* Acoes */}
            <div className="space-y-2">
              <button
                onClick={handleReprocess}
                disabled={isReprocessing}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-light-gray rounded-lg text-medium-gray hover:border-tmc-orange hover:text-tmc-orange transition-colors disabled:opacity-50"
              >
                <RefreshCw size={16} className={isReprocessing ? 'animate-spin' : ''} />
                {isReprocessing ? 'Reprocessando...' : 'Reprocessar extração'}
              </button>

              <a
                href={linkUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-light-gray rounded-lg text-medium-gray hover:border-tmc-orange hover:text-tmc-orange transition-colors"
              >
                <ExternalLink size={16} />
                Abrir link original
              </a>
            </div>
          </div>
        </div>

        {/* Coluna direita - Conteudo extraido */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
            {/* Header com tabs */}
            <div className="p-4 border-b border-light-gray">
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
                    selectedCount={selectedTopics.size}
                    totalCount={mockLinkData.topics.length}
                    onSelectAll={handleSelectAll}
                    onClearSelection={handleClearSelection}
                    className="mb-4"
                  />

                  {/* Lista de topicos */}
                  <div className="space-y-3 max-h-[450px] overflow-y-auto">
                    {mockLinkData.topics.map(topic => (
                      <TopicCard
                        key={topic.id}
                        id={topic.id}
                        type={topic.type}
                        text={editedTexts[topic.id] || topic.text}
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
                  <textarea
                    value={fullText}
                    onChange={(e) => setFullText(e.target.value)}
                    className="w-full h-80 p-4 border border-light-gray rounded-lg resize-none text-sm text-dark-gray leading-relaxed focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                    placeholder="Texto extraído do link..."
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
              variant="link"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

TextoBaseLink.propTypes = {
  fonte: PropTypes.shape({
    tipo: PropTypes.string,
    dados: PropTypes.shape({
      url: PropTypes.string,
      preview: PropTypes.object
    })
  }),
  onChangeSource: PropTypes.func,
  onDataChange: PropTypes.func
};

export default TextoBaseLink;
