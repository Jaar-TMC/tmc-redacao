import { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import { ChevronDown, ChevronRight, Star, MessageSquareQuote, Sparkles, Check } from 'lucide-react';

/**
 * GroupedStructureTab - AI-grouped view of story elements
 *
 * Shows story elements grouped by type (FATO PRINCIPAL, CONTEXTO, etc.)
 * with version selection from different sources.
 */

// Type labels and colors
const TYPE_CONFIG = {
  fato: { label: 'FATO PRINCIPAL', color: 'bg-blue-500', bgLight: 'bg-blue-50', textColor: 'text-blue-700' },
  contexto: { label: 'CONTEXTO', color: 'bg-purple-500', bgLight: 'bg-purple-50', textColor: 'text-purple-700' },
  detalhe: { label: 'DETALHE', color: 'bg-green-500', bgLight: 'bg-green-50', textColor: 'text-green-700' },
  reacao: { label: 'REAÇÃO', color: 'bg-orange-500', bgLight: 'bg-orange-50', textColor: 'text-orange-700' },
  declaracao: { label: 'DECLARAÇÃO', color: 'bg-pink-500', bgLight: 'bg-pink-50', textColor: 'text-pink-700' },
  dados: { label: 'DADOS/NÚMEROS', color: 'bg-cyan-500', bgLight: 'bg-cyan-50', textColor: 'text-cyan-700' },
  historico: { label: 'HISTÓRICO', color: 'bg-amber-500', bgLight: 'bg-amber-50', textColor: 'text-amber-700' },
  impacto: { label: 'IMPACTO', color: 'bg-red-500', bgLight: 'bg-red-50', textColor: 'text-red-700' },
};

const getTypeConfig = (type) => TYPE_CONFIG[type] || TYPE_CONFIG.fato;

/**
 * StoryElementGroup - A single grouped element with version selection
 */
const StoryElementGroup = ({
  group,
  isIncluded,
  selectedVersionId,
  onToggleInclude,
  onVersionSelect,
  articles
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const typeConfig = getTypeConfig(group.type);

  // Get source info for each version
  const getSourceInfo = (version) => {
    const article = articles.find(a => String(a.id) === String(version.articleId));
    return {
      name: version.source || article?.source || 'Fonte',
      favicon: article?.favicon
    };
  };

  return (
    <div className={`border rounded-lg overflow-hidden transition-all ${
      isIncluded ? 'border-tmc-orange/30 bg-white' : 'border-light-gray bg-gray-50 opacity-60'
    }`}>
      {/* Header */}
      <div className="flex items-center gap-3 p-3 bg-off-white border-b border-light-gray">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 hover:bg-white rounded transition-colors"
        >
          {isExpanded ? (
            <ChevronDown size={16} className="text-medium-gray" />
          ) : (
            <ChevronRight size={16} className="text-medium-gray" />
          )}
        </button>

        <label className="flex items-center gap-2 cursor-pointer flex-1">
          <input
            type="checkbox"
            checked={isIncluded}
            onChange={() => onToggleInclude(group.id)}
            className="w-4 h-4 text-tmc-orange rounded border-light-gray focus:ring-tmc-orange/50"
          />
          <span className={`px-2 py-0.5 text-xs font-semibold rounded ${typeConfig.bgLight} ${typeConfig.textColor}`}>
            {typeConfig.label}
          </span>
          <span className="text-sm text-medium-gray">
            ({group.versions?.length || 0} versões)
          </span>
        </label>

        {group.aiSuggestion && (
          <div className="flex items-center gap-1 text-xs text-tmc-orange">
            <Sparkles size={12} />
            <span className="hidden sm:inline">IA recomenda</span>
          </div>
        )}
      </div>

      {/* Content - Versions */}
      {isExpanded && (
        <div className="p-3 space-y-2">
          {group.versions?.map((version) => {
            const sourceInfo = getSourceInfo(version);
            const isSelected = selectedVersionId === version.id;
            const isRecommended = version.isRecommended;

            return (
              <label
                key={version.id}
                className={`flex gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                  isSelected
                    ? 'border-tmc-orange bg-orange-50'
                    : 'border-light-gray bg-white hover:border-tmc-orange/50'
                }`}
              >
                <input
                  type="radio"
                  name={`group-${group.id}`}
                  checked={isSelected}
                  onChange={() => onVersionSelect(group.id, version.id)}
                  disabled={!isIncluded}
                  className="mt-1 text-tmc-orange focus:ring-tmc-orange/50"
                />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {sourceInfo.favicon && (
                      <img
                        src={sourceInfo.favicon}
                        alt=""
                        className="w-4 h-4 rounded"
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                    )}
                    <span className="text-sm font-medium text-dark-gray">
                      {sourceInfo.name}
                    </span>
                    {isRecommended && (
                      <span className="flex items-center gap-1 px-1.5 py-0.5 text-xs bg-tmc-orange/10 text-tmc-orange rounded">
                        <Sparkles size={10} />
                        Recomendado
                      </span>
                    )}
                    {isSelected && (
                      <Check size={14} className="text-tmc-orange ml-auto" />
                    )}
                  </div>

                  <p className="text-sm text-medium-gray line-clamp-3">
                    {version.content}
                  </p>

                  <div className="flex items-center gap-3 mt-2 text-xs text-medium-gray">
                    <span>{version.wordCount || 0} palavras</span>
                  </div>
                </div>
              </label>
            );
          })}

          {/* AI Suggestion reason */}
          {group.aiSuggestion?.reason && (
            <div className="flex items-start gap-2 p-2 bg-tmc-orange/5 rounded-lg text-xs text-tmc-orange">
              <Sparkles size={12} className="mt-0.5 flex-shrink-0" />
              <span>{group.aiSuggestion.reason}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

StoryElementGroup.propTypes = {
  group: PropTypes.shape({
    id: PropTypes.string.isRequired,
    type: PropTypes.string,
    label: PropTypes.string,
    versions: PropTypes.array,
    aiSuggestion: PropTypes.object
  }).isRequired,
  isIncluded: PropTypes.bool.isRequired,
  selectedVersionId: PropTypes.string,
  onToggleInclude: PropTypes.func.isRequired,
  onVersionSelect: PropTypes.func.isRequired,
  articles: PropTypes.array.isRequired
};

/**
 * ExclusiveContentCard - Content that only appears in one source
 */
const ExclusiveContentCard = ({
  exclusive,
  isIncluded,
  onToggle,
  articles
}) => {
  const article = articles.find(a => String(a.id) === String(exclusive.articleId));
  const typeConfig = getTypeConfig(exclusive.type);

  return (
    <label className={`flex gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
      isIncluded
        ? 'border-amber-300 bg-amber-50'
        : 'border-light-gray bg-white hover:border-amber-200'
    }`}>
      <input
        type="checkbox"
        checked={isIncluded}
        onChange={() => onToggle(exclusive.id)}
        className="mt-1 w-4 h-4 text-amber-500 rounded border-light-gray focus:ring-amber-500/50"
      />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <Star size={14} className="text-amber-500" />
          <span className="text-xs font-semibold text-amber-700">EXCLUSIVO</span>
          <span className={`px-1.5 py-0.5 text-xs rounded ${typeConfig.bgLight} ${typeConfig.textColor}`}>
            {typeConfig.label}
          </span>
        </div>

        <p className="text-sm text-dark-gray mb-2">
          {exclusive.content}
        </p>

        <div className="flex items-center gap-2 text-xs text-medium-gray">
          {article?.favicon && (
            <img
              src={article.favicon}
              alt=""
              className="w-3 h-3 rounded"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
          )}
          <span>{exclusive.source || article?.source}</span>
          <span>•</span>
          <span>{exclusive.wordCount || 0} palavras</span>
        </div>
      </div>
    </label>
  );
};

ExclusiveContentCard.propTypes = {
  exclusive: PropTypes.shape({
    id: PropTypes.string.isRequired,
    type: PropTypes.string,
    content: PropTypes.string,
    source: PropTypes.string,
    articleId: PropTypes.string,
    wordCount: PropTypes.number
  }).isRequired,
  isIncluded: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  articles: PropTypes.array.isRequired
};

/**
 * QuoteCard - A quote with speaker attribution
 */
const QuoteCard = ({
  quote,
  isIncluded,
  onToggle,
  articles
}) => {
  const article = articles.find(a => String(a.id) === String(quote.articleId));

  return (
    <label className={`flex gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
      isIncluded
        ? 'border-pink-300 bg-pink-50'
        : 'border-light-gray bg-white hover:border-pink-200'
    }`}>
      <input
        type="checkbox"
        checked={isIncluded}
        onChange={() => onToggle(quote.id)}
        className="mt-1 w-4 h-4 text-pink-500 rounded border-light-gray focus:ring-pink-500/50"
      />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-2">
          <MessageSquareQuote size={14} className="text-pink-500" />
          <span className="text-xs font-semibold text-pink-700">CITAÇÃO</span>
        </div>

        <blockquote className="text-sm text-dark-gray italic border-l-2 border-pink-300 pl-3 mb-2">
          "{quote.text}"
        </blockquote>

        <div className="flex items-center gap-2 text-xs">
          <span className="font-medium text-dark-gray">{quote.speaker}</span>
          {quote.role && (
            <>
              <span className="text-medium-gray">•</span>
              <span className="text-medium-gray">{quote.role}</span>
            </>
          )}
        </div>

        <div className="flex items-center gap-2 mt-1 text-xs text-medium-gray">
          {article?.favicon && (
            <img
              src={article.favicon}
              alt=""
              className="w-3 h-3 rounded"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
          )}
          <span>{quote.source || article?.source}</span>
        </div>
      </div>
    </label>
  );
};

QuoteCard.propTypes = {
  quote: PropTypes.shape({
    id: PropTypes.string.isRequired,
    text: PropTypes.string,
    speaker: PropTypes.string,
    role: PropTypes.string,
    source: PropTypes.string,
    articleId: PropTypes.string
  }).isRequired,
  isIncluded: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  articles: PropTypes.array.isRequired
};

/**
 * GroupedStructureTab - Main component
 */
const GroupedStructureTab = ({
  groups,
  exclusives,
  quotes,
  selectedVersions,
  includedGroups,
  includedExclusives,
  includedQuotes,
  onVersionSelect,
  onToggleGroup,
  onToggleExclusive,
  onToggleQuote,
  articles
}) => {
  // Source summary
  const sourceSummary = useMemo(() => {
    const sources = {};
    articles.forEach(article => {
      const name = article.source || 'Fonte';
      if (!sources[name]) {
        sources[name] = { name, count: 0, favicon: article.favicon };
      }
    });

    // Count topics per source from groups
    groups.forEach(group => {
      group.versions?.forEach(version => {
        const sourceName = version.source || 'Fonte';
        if (sources[sourceName]) {
          sources[sourceName].count++;
        }
      });
    });

    return Object.values(sources);
  }, [articles, groups]);

  const hasContent = groups.length > 0 || exclusives.length > 0 || quotes.length > 0;

  if (!hasContent) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 bg-off-white rounded-full flex items-center justify-center mx-auto mb-4">
          <Sparkles size={28} className="text-medium-gray" />
        </div>
        <p className="text-medium-gray">
          Nenhum elemento identificado pela IA.
        </p>
      </div>
    );
  }

  return (
    <div className="flex gap-4">
      {/* Left sidebar - Sources */}
      <div className="w-48 flex-shrink-0 hidden lg:block">
        <div className="sticky top-4 space-y-3">
          <h4 className="text-sm font-semibold text-dark-gray mb-2">
            FONTES ({articles.length})
          </h4>

          {sourceSummary.map((source, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 p-2 bg-off-white rounded-lg"
            >
              {source.favicon && (
                <img
                  src={source.favicon}
                  alt=""
                  className="w-5 h-5 rounded"
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
              )}
              <div className="min-w-0">
                <p className="text-sm font-medium text-dark-gray truncate">
                  {source.name}
                </p>
                <p className="text-xs text-medium-gray">
                  {source.count} tópicos
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0 space-y-4">
        {/* Story Element Groups */}
        {groups.length > 0 && (
          <section>
            <h4 className="text-sm font-semibold text-dark-gray mb-3 flex items-center gap-2">
              <span className="w-2 h-2 bg-blue-500 rounded-full" />
              ESTRUTURA DA MATÉRIA
            </h4>

            <div className="space-y-3">
              {groups.map((group) => (
                <StoryElementGroup
                  key={group.id}
                  group={group}
                  isIncluded={includedGroups.has(group.id)}
                  selectedVersionId={selectedVersions[group.id]}
                  onToggleInclude={onToggleGroup}
                  onVersionSelect={onVersionSelect}
                  articles={articles}
                />
              ))}
            </div>
          </section>
        )}

        {/* Exclusive Content */}
        {exclusives.length > 0 && (
          <section>
            <h4 className="text-sm font-semibold text-dark-gray mb-3 flex items-center gap-2">
              <Star size={14} className="text-amber-500" />
              CONTEÚDO EXCLUSIVO
            </h4>

            <div className="space-y-2">
              {exclusives.map((exclusive) => (
                <ExclusiveContentCard
                  key={exclusive.id}
                  exclusive={exclusive}
                  isIncluded={includedExclusives.has(exclusive.id)}
                  onToggle={onToggleExclusive}
                  articles={articles}
                />
              ))}
            </div>
          </section>
        )}

        {/* Quotes */}
        {quotes.length > 0 && (
          <section>
            <h4 className="text-sm font-semibold text-dark-gray mb-3 flex items-center gap-2">
              <MessageSquareQuote size={14} className="text-pink-500" />
              DECLARAÇÕES
            </h4>

            <div className="space-y-2">
              {quotes.map((quote) => (
                <QuoteCard
                  key={quote.id}
                  quote={quote}
                  isIncluded={includedQuotes.has(quote.id)}
                  onToggle={onToggleQuote}
                  articles={articles}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
};

GroupedStructureTab.propTypes = {
  groups: PropTypes.array.isRequired,
  exclusives: PropTypes.array.isRequired,
  quotes: PropTypes.array.isRequired,
  selectedVersions: PropTypes.object.isRequired,
  includedGroups: PropTypes.instanceOf(Set).isRequired,
  includedExclusives: PropTypes.instanceOf(Set).isRequired,
  includedQuotes: PropTypes.instanceOf(Set).isRequired,
  onVersionSelect: PropTypes.func.isRequired,
  onToggleGroup: PropTypes.func.isRequired,
  onToggleExclusive: PropTypes.func.isRequired,
  onToggleQuote: PropTypes.func.isRequired,
  articles: PropTypes.array.isRequired
};

export default GroupedStructureTab;
