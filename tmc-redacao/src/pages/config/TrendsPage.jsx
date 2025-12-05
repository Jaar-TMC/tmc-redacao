import { useState, useCallback, useMemo } from 'react';
import { Plus, X, TrendingUp, Eye } from 'lucide-react';
import { mockMonitoredTopics, mockExcludedTerms } from '../../data/mockData';
import TabButton from '../../components/ui/TabButton';

/**
 * TrendsPage - Configuration page for Google Trends monitoring
 * Allows users to configure which topics to monitor and which terms to exclude
 */

const TrendsPage = () => {
  const [activeTab, setActiveTab] = useState('monitorar');
  const [monitoredTopics, setMonitoredTopics] = useState(mockMonitoredTopics);
  const [excludedTerms, setExcludedTerms] = useState(mockExcludedTerms);
  const [newTopic, setNewTopic] = useState('');
  const [newExcludedTerm, setNewExcludedTerm] = useState('');
  const [selectedRegion, setSelectedRegion] = useState('BR');
  const [selectedCategories, setSelectedCategories] = useState(['noticias', 'tecnologia']);
  const [isSaving, setIsSaving] = useState(false);

  const regions = useMemo(() => [
    { value: 'BR', label: 'Brasil' },
    { value: 'US', label: 'Estados Unidos' },
    { value: 'GLOBAL', label: 'Global' }
  ], []);

  const categories = useMemo(() => [
    { id: 'noticias', label: 'Notícias' },
    { id: 'tecnologia', label: 'Tecnologia' },
    { id: 'esportes', label: 'Esportes' },
    { id: 'entretenimento', label: 'Entretenimento' },
    { id: 'negocios', label: 'Negócios' }
  ], []);

  const handleAddTopic = useCallback(() => {
    if (!newTopic.trim()) return;
    const topic = {
      id: Date.now(),
      topic: newTopic.trim(),
      addedAt: new Date(),
      trendsFound: 0
    };
    setMonitoredTopics(prev => [...prev, topic]);
    setNewTopic('');
  }, [newTopic]);

  const handleRemoveTopic = useCallback((id) => {
    setMonitoredTopics(prev => prev.filter(t => t.id !== id));
  }, []);

  const handleAddExcludedTerm = useCallback(() => {
    if (!newExcludedTerm.trim()) return;
    setExcludedTerms(prev => [...prev, newExcludedTerm.trim()]);
    setNewExcludedTerm('');
  }, [newExcludedTerm]);

  const handleRemoveExcludedTerm = useCallback((term) => {
    setExcludedTerms(prev => prev.filter(t => t !== term));
  }, []);

  const handleToggleCategory = useCallback((catId) => {
    setSelectedCategories(prev => {
      if (prev.includes(catId)) {
        return prev.filter(c => c !== catId);
      }
      return [...prev, catId];
    });
  }, []);

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-dark-gray">Google Trends</h1>
        <p className="text-medium-gray mt-1">
          Configure quais temas você quer monitorar e quais termos devem ser excluídos das tendências
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-off-white p-1 rounded-lg w-fit" role="tablist" aria-label="Configurações de tendências">
        <TabButton
          active={activeTab === 'monitorar'}
          onClick={() => setActiveTab('monitorar')}
          ariaLabel="Aba de monitoramento de temas"
        >
          Monitorar
        </TabButton>
        <TabButton
          active={activeTab === 'excluir'}
          onClick={() => setActiveTab('excluir')}
          ariaLabel="Aba de exclusão de termos"
        >
          Excluir
        </TabButton>
      </div>

      {/* Monitor Tab */}
      {activeTab === 'monitorar' && (
        <div
          id="monitorar-panel"
          role="tabpanel"
          aria-labelledby="monitorar-tab"
          className="space-y-6"
        >
          {/* Add Topic */}
          <div className="bg-white rounded-xl border border-light-gray p-6">
            <h3 className="font-semibold text-dark-gray mb-2">Adicionar temas</h3>
            <p className="text-xs text-medium-gray mb-4">Digite temas que você quer acompanhar nas tendências do Google</p>
            <div className="flex gap-3">
              <div className="flex-1">
                <label htmlFor="new-topic" className="sr-only">Novo tema para monitorar</label>
                <div className="flex flex-wrap gap-2 items-center p-3 bg-off-white rounded-lg min-h-[48px]">
                  {newTopic && (
                    <span className="px-3 py-1 bg-tmc-orange text-white text-sm rounded-full flex items-center gap-1">
                      {newTopic}
                      <button onClick={() => setNewTopic('')} aria-label="Remover tema">
                        <X size={14} />
                      </button>
                    </span>
                  )}
                  <input
                    id="new-topic"
                    type="text"
                    value={newTopic}
                    onChange={(e) => setNewTopic(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddTopic()}
                    placeholder="Ex: eleições 2024, taxa de juros..."
                    className="flex-1 bg-transparent focus:outline-none min-w-[200px] text-sm"
                  />
                </div>
                <p className="text-xs text-medium-gray mt-1">Pressione Enter para adicionar</p>
              </div>
              <button
                type="button"
                onClick={handleAddTopic}
                disabled={!newTopic.trim()}
                className="px-6 py-3 bg-tmc-orange text-white rounded-lg font-semibold hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]"
                aria-label="Adicionar tema para monitorar"
              >
                Adicionar tema
              </button>
            </div>
          </div>

          {/* Monitored Topics */}
          <div className="bg-white rounded-xl border border-light-gray p-6">
            <h3 className="font-semibold text-dark-gray mb-4">Temas monitorados</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {monitoredTopics.map((topic) => (
                <div
                  key={topic.id}
                  className="border border-light-gray rounded-xl p-4 hover:border-tmc-orange/50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <TrendingUp size={18} className="text-tmc-orange" />
                      <span className="font-semibold text-dark-gray">{topic.topic}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveTopic(topic.id)}
                      className="p-1 hover:bg-off-white rounded transition-colors min-h-[44px] min-w-[44px]"
                      aria-label={`Remover tema ${topic.topic}`}
                      title="Remover"
                    >
                      <X size={16} className="text-medium-gray" aria-hidden="true" />
                    </button>
                  </div>
                  <p className="text-xs text-medium-gray mb-3">
                    Adicionado em: {topic.addedAt.toLocaleDateString('pt-BR')}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-medium-gray">
                      Tendências encontradas:{' '}
                      <span className="font-semibold text-dark-gray">{topic.trendsFound}</span>
                    </span>
                    <button
                      type="button"
                      className="flex items-center gap-1 text-sm text-tmc-orange hover:underline min-h-[44px]"
                      aria-label={`Ver tendências para ${topic.topic}`}
                    >
                      <Eye size={14} aria-hidden="true" />
                      Ver detalhes
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Exclude Tab */}
      {activeTab === 'excluir' && (
        <div
          id="excluir-panel"
          role="tabpanel"
          aria-labelledby="excluir-tab"
          className="space-y-6"
        >
          {/* Description */}
          <div className="bg-warning/10 border border-warning/30 rounded-xl p-4">
            <p className="text-sm text-dark-gray">
              Termos e frases adicionados aqui serão ignorados ao buscar tendências do Google Trends.
            </p>
          </div>

          {/* Add Excluded Term */}
          <div className="bg-white rounded-xl border border-light-gray p-6">
            <h3 className="font-semibold text-dark-gray mb-2">Adicionar termo a excluir</h3>
            <p className="text-xs text-medium-gray mb-4">Digite palavras ou frases que devem ser ignoradas</p>
            <div className="flex gap-3">
              <div className="flex-1">
                <label htmlFor="new-excluded-term" className="sr-only">Novo termo para excluir</label>
                <input
                  id="new-excluded-term"
                  type="text"
                  value={newExcludedTerm}
                  onChange={(e) => setNewExcludedTerm(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddExcludedTerm()}
                  placeholder="Ex: Reality Show, Celebridade..."
                  className="w-full px-4 py-2.5 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                />
                <p className="text-xs text-medium-gray mt-1">Pressione Enter para adicionar</p>
              </div>
              <button
                type="button"
                onClick={handleAddExcludedTerm}
                disabled={!newExcludedTerm.trim()}
                className="px-6 py-2.5 bg-error text-white rounded-lg font-semibold hover:bg-error/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 min-h-[44px]"
                aria-label="Adicionar termo à lista de exclusão"
              >
                <Plus size={18} aria-hidden="true" />
                Adicionar à lista
              </button>
            </div>
          </div>

          {/* Excluded Terms List */}
          <div className="bg-white rounded-xl border border-light-gray p-6">
            <h3 className="font-semibold text-dark-gray mb-4">Lista de exclusão</h3>
            <div className="flex flex-wrap gap-2">
              {excludedTerms.map((term) => (
                <span
                  key={term}
                  className="px-4 py-2 bg-error/10 text-error rounded-full text-sm flex items-center gap-2"
                >
                  {term}
                  <button
                    type="button"
                    onClick={() => handleRemoveExcludedTerm(term)}
                    className="hover:bg-error/20 rounded-full p-0.5 transition-colors"
                    aria-label={`Remover ${term} da lista de exclusão`}
                    title="Remover"
                  >
                    <X size={14} aria-hidden="true" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Additional Settings */}
          <div className="bg-white rounded-xl border border-light-gray p-6">
            <h3 className="font-semibold text-dark-gray mb-2">Configurações adicionais</h3>
            <p className="text-xs text-medium-gray mb-6">Personalize como as tendências são filtradas</p>

            {/* Region Section */}
            <fieldset className="mb-6 pb-6 border-b border-light-gray">
              <legend className="block text-sm font-medium text-dark-gray mb-2">Região</legend>
              <p className="text-xs text-medium-gray mb-3">Escolha de qual região deseja ver as tendências</p>
              <label htmlFor="region-select" className="sr-only">Selecione a região</label>
              <select
                id="region-select"
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value)}
                className="w-full max-w-xs px-4 py-2.5 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
              >
                {regions.map((region) => (
                  <option key={region.value} value={region.value}>
                    {region.label}
                  </option>
                ))}
              </select>
            </fieldset>

            {/* Categories Section */}
            <fieldset>
              <legend className="block text-sm font-medium text-dark-gray mb-2">
                Categorias de interesse
              </legend>
              <p className="text-xs text-medium-gray mb-3">Selecione as categorias que você quer monitorar</p>
              <div className="flex flex-wrap gap-2">
                {categories.map((cat) => (
                  <label
                    key={cat.id}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg cursor-pointer transition-colors ${
                      selectedCategories.includes(cat.id)
                        ? 'bg-tmc-orange text-white'
                        : 'bg-off-white text-dark-gray hover:bg-light-gray'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedCategories.includes(cat.id)}
                      onChange={() => handleToggleCategory(cat.id)}
                      className="sr-only"
                    />
                    {cat.label}
                  </label>
                ))}
              </div>
            </fieldset>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => {
                setIsSaving(true);
                setTimeout(() => setIsSaving(false), 1000);
              }}
              disabled={isSaving}
              className="px-6 py-3 bg-tmc-dark-green text-white rounded-lg font-semibold hover:bg-tmc-light-green transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]"
              aria-label="Salvar configurações de exclusão de tendências"
            >
              {isSaving ? 'Salvando...' : 'Salvar configurações'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TrendsPage;
