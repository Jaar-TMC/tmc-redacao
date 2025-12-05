import PropTypes from 'prop-types';
import { ArrowLeft, ChevronDown, ChevronUp, Check, Sparkles } from 'lucide-react';
import { mockTones, mockPersonas } from '../../data/mockData';

/**
 * Step One component - Article selection and configuration
 * @param {Object} props
 * @param {Array} props.articles - List of articles to select from
 * @param {number|null} props.expandedArticle - ID of currently expanded article
 * @param {Function} props.onExpandArticle - Handler for expanding/collapsing articles
 * @param {Object} props.selectedParagraphs - Map of selected paragraphs per article
 * @param {Function} props.onToggleParagraph - Handler for toggling paragraph selection
 * @param {Object|null} props.selectedTone - Currently selected tone
 * @param {Function} props.onSelectTone - Handler for selecting tone
 * @param {Object|null} props.selectedPersona - Currently selected persona
 * @param {Function} props.onSelectPersona - Handler for selecting persona
 * @param {Function} props.onCancel - Handler for cancel action
 * @param {Function} props.onGenerate - Handler for generate action
 */
const StepOne = ({
  articles,
  expandedArticle,
  onExpandArticle,
  selectedParagraphs,
  onToggleParagraph,
  selectedTone,
  onSelectTone,
  selectedPersona,
  onSelectPersona,
  onCancel,
  onGenerate
}) => {
  const getTotalSelectedParagraphs = () => {
    return Object.values(selectedParagraphs).reduce((sum, arr) => sum + arr.length, 0);
  };

  return (
    <div className="min-h-screen pt-16 bg-off-white">
      {/* Header */}
      <div className="bg-white border-b border-light-gray sticky top-16 z-40">
        <div className="flex items-center justify-between px-4 md:px-6 py-3">
          <div className="flex items-center gap-2 md:gap-4">
            <button
              onClick={onCancel}
              className="flex items-center gap-2 text-medium-gray hover:text-dark-gray transition-colors"
              aria-label="Voltar"
            >
              <ArrowLeft size={20} />
            </button>
            <div>
              <p className="text-xs text-medium-gray hidden sm:block">Redação &gt; Criar com Inspiração</p>
              <h1 className="text-base md:text-lg font-bold text-dark-gray">Selecione as Matérias (Passo 1 de 3)</h1>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-medium-gray">
            <span className="w-6 h-6 bg-tmc-orange text-white rounded-full flex items-center justify-center text-xs font-bold">
              1
            </span>
            <span className="hidden sm:inline">de 3</span>
          </div>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row h-auto lg:h-[calc(100vh-8rem)]">
        {/* Left: Articles List */}
        <div className="flex-1 p-4 md:p-6 overflow-y-auto">
          <div className="space-y-4">
            {articles.map((article) => {
              const paragraphs = article.content.split('. ');
              const isExpanded = expandedArticle === article.id;
              const selectedCount = (selectedParagraphs[article.id] || []).length;

              return (
                <div
                  key={article.id}
                  className="bg-white rounded-xl border border-light-gray overflow-hidden"
                >
                  {/* Article Header */}
                  <div
                    className="flex items-center justify-between p-4 cursor-pointer hover:bg-off-white transition-colors"
                    onClick={() => onExpandArticle(isExpanded ? null : article.id)}
                  >
                    <div className="flex items-center gap-3">
                      <img
                        src={article.favicon}
                        alt={article.source}
                        className="w-6 h-6 rounded"
                      />
                      <div>
                        <h3 className="font-semibold text-dark-gray line-clamp-1">
                          {article.title}
                        </h3>
                        <p className="text-xs text-medium-gray">{article.source}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-medium-gray bg-off-white px-2 py-1 rounded">
                        {selectedCount}/{paragraphs.length} selecionados
                      </span>
                      {isExpanded ? (
                        <ChevronUp size={20} className="text-medium-gray" />
                      ) : (
                        <ChevronDown size={20} className="text-medium-gray" />
                      )}
                    </div>
                  </div>

                  {/* Article Content - Expandable */}
                  {isExpanded && (
                    <div className="border-t border-light-gray p-4 space-y-3">
                      {paragraphs.map((paragraph, index) => {
                        const isSelected = (selectedParagraphs[article.id] || []).includes(index);
                        const paragraphId = `article-${article.id}-paragraph-${index}`;

                        return (
                          <div
                            key={paragraphId}
                            onClick={() => onToggleParagraph(article.id, index)}
                            className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                              isSelected
                                ? 'bg-tmc-orange/10 border border-tmc-orange'
                                : 'bg-off-white hover:bg-light-gray border border-transparent'
                            }`}
                          >
                            <div
                              className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 ${
                                isSelected
                                  ? 'bg-tmc-orange border-tmc-orange'
                                  : 'border-light-gray'
                              }`}
                            >
                              {isSelected && <Check size={12} className="text-white" />}
                            </div>
                            <p className="text-sm text-dark-gray">{paragraph}.</p>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <button className="w-full mt-4 py-3 border-2 border-dashed border-light-gray rounded-xl text-medium-gray hover:border-tmc-orange hover:text-tmc-orange transition-colors">
            + Adicionar mais matérias
          </button>
        </div>

        {/* Right: Configuration Panel */}
        <div className="w-full lg:w-96 bg-white lg:border-l border-light-gray p-4 md:p-6 flex flex-col">
          {/* Summary */}
          <div className="bg-off-white rounded-xl p-4 mb-4 md:mb-6">
            <h3 className="font-semibold text-dark-gray mb-2">Resumo da Seleção</h3>
            <p className="text-sm text-medium-gray">
              <span className="font-bold text-dark-gray">{articles.length}</span> matérias |{' '}
              <span className="font-bold text-dark-gray">{getTotalSelectedParagraphs()}</span>{' '}
              parágrafos selecionados
            </p>
            <p className="text-xs text-medium-gray mt-1">
              ~{getTotalSelectedParagraphs() * 50} palavras estimadas
            </p>
          </div>

          {/* Tone Selection */}
          <div className="mb-4">
            <label className="block text-sm font-semibold text-dark-gray mb-2">
              Tom <span className="text-error">*</span>
            </label>
            <p className="text-xs text-medium-gray mb-2">Escolha o estilo de escrita do conteúdo</p>
            <div className="space-y-2">
              {mockTones.map((tone) => (
                <button
                  key={tone.id}
                  onClick={() => onSelectTone(tone)}
                  className={`w-full p-3 rounded-lg border-2 text-left transition-all ${
                    selectedTone?.id === tone.id
                      ? 'border-tmc-orange bg-tmc-orange/5'
                      : 'border-light-gray hover:border-tmc-orange/50'
                  }`}
                >
                  <p className="font-medium text-dark-gray">{tone.name}</p>
                  <p className="text-xs text-medium-gray">{tone.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Persona Selection */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-dark-gray mb-2">
              Persona do Redator <span className="text-error">*</span>
            </label>
            <p className="text-xs text-medium-gray mb-2">Defina quem será a voz do texto</p>
            <div className="space-y-2">
              {mockPersonas.map((persona) => (
                <button
                  key={persona.id}
                  onClick={() => onSelectPersona(persona)}
                  className={`w-full p-3 rounded-lg border-2 text-left transition-all ${
                    selectedPersona?.id === persona.id
                      ? 'border-tmc-dark-green bg-tmc-dark-green/5'
                      : 'border-light-gray hover:border-tmc-dark-green/50'
                  }`}
                >
                  <p className="font-medium text-dark-gray">{persona.name}</p>
                  <p className="text-xs text-medium-gray">{persona.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-auto space-y-3">
            <button
              onClick={onCancel}
              className="w-full py-3 border border-light-gray rounded-lg text-medium-gray hover:bg-off-white transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={onGenerate}
              disabled={!selectedTone || !selectedPersona}
              className="w-full py-3 bg-tmc-orange text-white rounded-lg font-semibold hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Sparkles size={20} />
              Gerar conteúdo
            </button>
            {(!selectedTone || !selectedPersona) && (
              <p className="text-xs text-medium-gray text-center mt-2">
                Selecione um tom e uma persona para continuar
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

StepOne.propTypes = {
  articles: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    title: PropTypes.string.isRequired,
    source: PropTypes.string.isRequired,
    favicon: PropTypes.string.isRequired,
    content: PropTypes.string.isRequired
  })).isRequired,
  expandedArticle: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onExpandArticle: PropTypes.func.isRequired,
  selectedParagraphs: PropTypes.object.isRequired,
  onToggleParagraph: PropTypes.func.isRequired,
  selectedTone: PropTypes.object,
  onSelectTone: PropTypes.func.isRequired,
  selectedPersona: PropTypes.object,
  onSelectPersona: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  onGenerate: PropTypes.func.isRequired
};

export default StepOne;
