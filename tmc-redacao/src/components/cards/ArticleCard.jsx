import { memo, useCallback, useMemo } from 'react';
import { ExternalLink, Check } from 'lucide-react';
import { formatRelativeTime } from '../../data/mockData';
import ScoreTooltip from '../ui/ScoreTooltip';
import PropTypes from 'prop-types';

/**
 * ArticleCard Component
 *
 * WCAG 2.1 Compliance:
 * - Sensory Characteristics (1.3.3): Visual indicators (colors, checkboxes) are supplemented with text labels
 * - Link Purpose in Context (2.4.4): All links have descriptive aria-labels providing full context
 * - Focus Order (2.4.3): Tab order follows logical reading order
 */
const categoryColors = {
  'Política': 'bg-tmc-dark-green',
  'Economia': 'bg-tmc-orange',
  'Esportes': 'bg-alert-orange',
  'Tecnologia': 'bg-tmc-light-green',
  'Entretenimento': 'bg-[#8B6E4E]',
  'Saúde': 'bg-[#2C6E8A]',
  'Ciência': 'bg-[#4A7C6F]',
  'Educação': 'bg-warning',
  'Internacional': 'bg-[#5B6A8A]',
  'Seguranca': 'bg-[#6B5B4E]',
};

const EMPTY_SET = new Set();

const ArticleCard = ({ article, isSelected, onSelect, selectedTags = EMPTY_SET, onTagSelect }) => {
  const categoryColor = useMemo(
    () => categoryColors[article.category] || 'bg-gray-500',
    [article.category]
  );

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(article);
    }
  }, [onSelect, article]);

  const handleClick = useCallback(() => {
    onSelect(article);
  }, [onSelect, article]);

  return (
    <div
      className={`bg-white rounded-xl border transition-all cursor-pointer group h-[280px] flex flex-col ${
        isSelected
          ? 'border-tmc-orange'
          : 'border-light-gray hover:border-tmc-orange/50'
      }`}
      onClick={handleClick}
      onKeyDown={handleKeyPress}
      tabIndex={0}
      role="article"
      aria-label={`${article.title} - ${article.source} - ${article.category}`}
      aria-selected={isSelected}
    >
      {/* Selection Checkbox */}
      <div className="relative">
        <div
          className={`absolute top-3 left-3 w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all z-10 ${
            isSelected
              ? 'bg-tmc-orange border-tmc-orange'
              : 'bg-white border-light-gray group-hover:border-tmc-orange'
          }`}
          role="checkbox"
          aria-checked={isSelected}
          aria-label={isSelected ? 'Matéria selecionada' : 'Matéria não selecionada'}
        >
          {isSelected && <Check className="text-white" style={{ width: '14px', height: '14px' }} aria-hidden="true" />}
        </div>

        {/* Score Badge + Category Tag */}
        <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5">
          {article.score != null ? (
            <ScoreTooltip article={article}>
              <span
                className={`text-white text-xs font-bold px-2 py-1 rounded-md ${
                  article.scoreClassification === 'A'
                    ? 'bg-success'
                    : article.scoreClassification === 'B'
                    ? 'bg-warning'
                    : 'bg-medium-gray'
                }`}
                aria-label={`Score: ${article.score} - Classificação ${article.scoreClassification}`}
              >
                {article.score}
              </span>
            </ScoreTooltip>
          ) : (
            <span
              className="text-white/70 text-xs font-bold px-2 py-1 rounded-md bg-medium-gray/60"
              aria-label="Score não disponível"
              title="Score ainda não calculado"
            >
              —
            </span>
          )}
          <span className={`${categoryColor} text-white text-xs font-semibold px-2 py-1 rounded-md`} aria-label={`Categoria: ${article.category}`}>
            {article.category}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 pt-12 flex flex-col flex-1 min-h-0">
        {/* Title - altura fixa para 2 linhas */}
        <h3 className="font-bold text-dark-gray text-base leading-snug line-clamp-2 mb-3 group-hover:text-tmc-dark-green transition-colors h-[2.75rem]">
          {article.title}
        </h3>

        {/* Preview - altura fixa para 3 linhas */}
        <div className="mb-4 flex-1">
          <p className="text-sm text-medium-gray line-clamp-3">
            {article.preview}
          </p>
        </div>

        {/* Footer - sempre no bottom */}
        <div className="flex items-center justify-between pt-3 border-t border-light-gray mt-auto">
          <div className="flex items-center gap-4">
            <img
              src={article.favicon}
              alt=""
              className="w-4 h-4 rounded"
              loading="lazy"
              aria-hidden="true"
            />
            <span className="text-xs font-medium text-dark-gray">{article.source}</span>
            <span className="text-xs text-medium-gray" aria-hidden="true">•</span>
            <span className="text-xs text-medium-gray">
              <span className="sr-only">Publicado </span>
              {formatRelativeTime(article.publishedAt)}
            </span>
          </div>

          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 hover:bg-off-white rounded-lg transition-colors"
            onClick={(e) => e.stopPropagation()}
            aria-label={`Ler matéria completa: ${article.title}`}
            title="Ler matéria completa"
          >
            <ExternalLink className="text-medium-gray hover:text-tmc-orange" style={{ width: '18px', height: '18px' }} aria-hidden="true" />
          </a>
        </div>

        {/* Tags - Selectable - linha única com overflow */}
        {article.tags && article.tags.length > 0 && (
          <div className="flex gap-1.5 mt-3 overflow-hidden">
            {article.tags.slice(0, 4).map((tag) => {
              const isTagSelected = selectedTags.has(tag);
              return (
                <button
                  key={tag}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onTagSelect) {
                      onTagSelect(tag);
                    }
                  }}
                  className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 transition-all whitespace-nowrap ${
                    isTagSelected
                      ? 'bg-tmc-orange text-white'
                      : 'bg-off-white text-medium-gray hover:bg-tmc-orange/10 hover:text-tmc-orange'
                  }`}
                  aria-pressed={isTagSelected}
                  aria-label={isTagSelected ? `Remover tag ${tag}` : `Adicionar tag ${tag}`}
                >
                  {isTagSelected && <Check size={10} strokeWidth={3} />}
                  #{tag}
                </button>
              );
            })}
            {article.tags.length > 4 && (
              <span className="text-xs text-medium-gray py-1">+{article.tags.length - 4}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

ArticleCard.propTypes = {
  article: PropTypes.shape({
    id: PropTypes.number.isRequired,
    title: PropTypes.string.isRequired,
    preview: PropTypes.string.isRequired,
    category: PropTypes.string.isRequired,
    source: PropTypes.string.isRequired,
    url: PropTypes.string.isRequired,
    favicon: PropTypes.string.isRequired,
    publishedAt: PropTypes.instanceOf(Date).isRequired,
    tags: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  isSelected: PropTypes.bool.isRequired,
  onSelect: PropTypes.func.isRequired,
  selectedTags: PropTypes.instanceOf(Set),
  onTagSelect: PropTypes.func,
};

export default memo(ArticleCard, (prevProps, nextProps) =>
  prevProps.article.id === nextProps.article.id &&
  prevProps.isSelected === nextProps.isSelected &&
  prevProps.selectedTags === nextProps.selectedTags
);
