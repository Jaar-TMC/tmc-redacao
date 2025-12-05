import { useCallback, useMemo, useState } from 'react';
import { ExternalLink, Check } from 'lucide-react';
import { formatRelativeTime } from '../../data/mockData';
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
  'Política': 'bg-blue-500',
  'Economia': 'bg-emerald-500',
  'Esportes': 'bg-orange-500',
  'Tecnologia': 'bg-purple-500',
  'Entretenimento': 'bg-pink-500',
  'Saúde': 'bg-red-500',
  'Ciência': 'bg-cyan-500',
  'Educação': 'bg-yellow-500'
};

const ArticleCard = ({ article, isSelected, onSelect }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const categoryColor = useMemo(
    () => categoryColors[article.category] || 'bg-gray-500',
    [article.category]
  );

  const shouldShowExpand = article.preview.length > 150;

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
      className={`bg-white rounded-xl border transition-all cursor-pointer group ${
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

        {/* Category Tag */}
        <div className="absolute top-3 right-3 z-10">
          <span className={`${categoryColor} text-white text-xs font-semibold px-2 py-1 rounded-md`} aria-label={`Categoria: ${article.category}`}>
            {article.category}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 pt-12">
        {/* Title */}
        <h3 className="font-bold text-dark-gray text-base leading-snug line-clamp-2 mb-3 group-hover:text-tmc-dark-green transition-colors">
          {article.title}
        </h3>

        {/* Preview */}
        <div className="mb-4">
          <p className={`text-sm text-medium-gray ${!isExpanded && shouldShowExpand ? 'line-clamp-3' : ''}`}>
            {article.preview}
          </p>
          {shouldShowExpand && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsExpanded(!isExpanded);
              }}
              className="text-xs text-tmc-orange hover:underline mt-1 font-medium"
            >
              {isExpanded ? 'Ver menos' : 'Ver mais'}
            </button>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-light-gray">
          <div className="flex items-center gap-4">
            <img
              src={article.favicon}
              alt=""
              className="w-4 h-4 rounded"
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

        {/* Tags */}
        <div className="flex flex-wrap gap-1 mt-3">
          {article.tags.map((tag) => (
            <span
              key={tag}
              className="text-xs bg-off-white text-medium-gray px-2 py-0.5 rounded"
            >
              #{tag}
            </span>
          ))}
        </div>
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
    tags: PropTypes.arrayOf(PropTypes.string).isRequired,
  }).isRequired,
  isSelected: PropTypes.bool.isRequired,
  onSelect: PropTypes.func.isRequired,
};

export default ArticleCard;
