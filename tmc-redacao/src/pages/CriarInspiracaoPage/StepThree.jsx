import PropTypes from 'prop-types';
import { ArrowLeft, RefreshCw, BarChart3, Link2, Lightbulb, FileText } from 'lucide-react';

/**
 * Step Three component - Result review and editing
 * @param {Object} props
 * @param {Object} props.generatedContent - Generated content object
 * @param {Array} props.articles - Source articles used for generation
 * @param {Function} props.onRegenerate - Handler for regenerating content
 * @param {Function} props.onUseDraft - Handler for using content as draft
 * @param {Function} props.onReset - Handler for resetting to step one
 */
const StepThree = ({
  generatedContent,
  articles,
  onRegenerate,
  onUseDraft,
  onReset
}) => {
  if (!generatedContent) {
    return null;
  }

  const suggestions = [
    'Adicione mais contexto no parágrafo 3',
    'Considere incluir dados estatísticos',
    'Título pode ser mais chamativo'
  ];

  const keywords = ['economia', 'governo', 'medidas', 'investimentos', 'PIB'];

  return (
    <div className="min-h-screen pt-16 bg-off-white">
      {/* Header */}
      <div className="bg-white border-b border-light-gray sticky top-16 z-40">
        <div className="flex items-center justify-between px-4 md:px-6 py-3">
          <button
            onClick={onReset}
            className="flex items-center gap-2 text-medium-gray hover:text-dark-gray transition-colors"
            aria-label="Voltar e refazer"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium hidden sm:inline">Refazer</span>
          </button>

          <h1 className="text-base md:text-lg font-bold text-tmc-dark-green">Revise o Resultado (Passo 3 de 3)</h1>

          <div className="flex items-center gap-2 md:gap-3">
            <button
              onClick={onRegenerate}
              className="hidden md:flex items-center gap-2 px-4 py-2 text-sm font-medium text-medium-gray hover:text-dark-gray border border-light-gray rounded-lg hover:bg-off-white transition-colors"
              title="Regenerar conteúdo"
            >
              <RefreshCw size={16} />
              Regenerar
            </button>
            <button
              onClick={onUseDraft}
              className="px-3 md:px-4 py-2 text-sm font-semibold text-white bg-tmc-orange rounded-lg hover:bg-tmc-orange/90 transition-colors"
            >
              <span className="hidden sm:inline">Usar como rascunho</span>
              <span className="sm:hidden">Usar</span>
            </button>
          </div>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row h-auto lg:h-[calc(100vh-8rem)]">
        {/* Left: Generated Content Preview */}
        <div className="flex-1 p-4 md:p-6 overflow-y-auto">
          <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-sm border border-light-gray p-4 md:p-8">
            <input
              type="text"
              value={generatedContent.title || ''}
              className="w-full text-2xl font-bold text-dark-gray mb-6 focus:outline-none border-b border-transparent hover:border-light-gray focus:border-tmc-orange pb-2 transition-colors"
              readOnly
            />

            <div className="prose prose-lg max-w-none">
              {generatedContent.content.split('\n\n').map((paragraph, index) => {
                const paragraphId = `generated-paragraph-${index}`;
                return (
                  <p key={paragraphId} className="text-dark-gray leading-relaxed mb-4">
                    {paragraph}
                  </p>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Analysis Panel */}
        <div className="w-full lg:w-96 bg-white lg:border-l border-light-gray p-4 md:p-6 overflow-y-auto">
          {/* Metrics */}
          <div className="bg-off-white rounded-xl p-4 mb-6">
            <h3 className="font-semibold text-dark-gray mb-4 flex items-center gap-2">
              <BarChart3 size={18} className="text-tmc-orange" />
              Métricas
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-medium-gray">Palavras</p>
                <p className="text-xl font-bold text-dark-gray">
                  {generatedContent.wordCount}
                </p>
              </div>
              <div>
                <p className="text-xs text-medium-gray">Tempo de leitura</p>
                <p className="text-xl font-bold text-dark-gray">
                  {generatedContent.readTime}
                </p>
              </div>
              <div>
                <p className="text-xs text-medium-gray">Originalidade</p>
                <p className="text-xl font-bold text-success">
                  {generatedContent.originalityScore}%
                </p>
              </div>
              <div>
                <p className="text-xs text-medium-gray">Score SEO</p>
                <p className="text-xl font-bold text-tmc-orange">
                  {generatedContent.seoScore}/100
                </p>
              </div>
            </div>
          </div>

          {/* Sources */}
          <div className="mb-6">
            <h3 className="font-semibold text-dark-gray mb-3 flex items-center gap-2">
              <Link2 size={18} className="text-tmc-orange" />
              Fontes Utilizadas
            </h3>
            <div className="space-y-2">
              {articles.map((article) => (
                <div
                  key={article.id}
                  className="flex items-center gap-3 p-3 bg-off-white rounded-lg"
                >
                  <img
                    src={article.favicon}
                    alt={article.source}
                    className="w-5 h-5 rounded"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-dark-gray truncate">
                      {article.source}
                    </p>
                    <p className="text-xs text-medium-gray">
                      {Math.floor(100 / articles.length)}% do conteúdo
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Suggestions */}
          <div className="mb-6">
            <h3 className="font-semibold text-dark-gray mb-3 flex items-center gap-2">
              <Lightbulb size={18} className="text-tmc-orange" />
              Sugestões de Melhoria
            </h3>
            <div className="space-y-2">
              {suggestions.map((suggestion, index) => {
                const suggestionId = `suggestion-${index}`;
                return (
                  <div
                    key={suggestionId}
                    className="flex items-start gap-3 p-3 bg-off-white rounded-lg"
                  >
                    <FileText size={16} className="text-medium-gray mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm text-dark-gray">{suggestion}</p>
                      <button className="text-xs text-tmc-orange hover:underline mt-1">
                        Aplicar
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* SEO Keywords */}
          <div>
            <h3 className="font-semibold text-dark-gray mb-3">Palavras-chave SEO</h3>
            <div className="flex flex-wrap gap-2">
              {keywords.map((keyword) => (
                <span
                  key={keyword}
                  className="px-3 py-1 bg-off-white text-medium-gray text-sm rounded-full"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

StepThree.propTypes = {
  generatedContent: PropTypes.shape({
    title: PropTypes.string.isRequired,
    content: PropTypes.string.isRequired,
    wordCount: PropTypes.number.isRequired,
    readTime: PropTypes.string.isRequired,
    originalityScore: PropTypes.number.isRequired,
    seoScore: PropTypes.number.isRequired
  }),
  articles: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    source: PropTypes.string.isRequired,
    favicon: PropTypes.string.isRequired
  })).isRequired,
  onRegenerate: PropTypes.func.isRequired,
  onUseDraft: PropTypes.func.isRequired,
  onReset: PropTypes.func.isRequired
};

export default StepThree;
