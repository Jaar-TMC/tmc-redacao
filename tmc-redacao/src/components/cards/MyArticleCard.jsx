import { Eye, Edit, Trash2, BarChart3, Calendar, Tag, User } from 'lucide-react';
import { useState } from 'react';
import StatusBadge from '../ui/StatusBadge';
import { formatRelativeTime } from '../../data/mockData';
import PropTypes from 'prop-types';

const categoryColors = {
  'Política': '#3B82F6',
  'Economia': '#10B981',
  'Esportes': '#E87722',
  'Tecnologia': '#8B5CF6',
  'Entretenimento': '#EC4899',
  'Saúde': '#E53935',
  'Ciência': '#06B6D4',
  'Educação': '#F59E0B'
};

/**
 * MyArticleCard Component
 *
 * Card para exibir matérias do usuário na página "Minhas Matérias"
 * Segue especificações do documento de planejamento UI/UX
 *
 * WCAG 2.1 Compliance:
 * - All interactive elements have proper ARIA labels
 * - Color is not the only means of conveying information
 * - Keyboard accessible with visible focus states
 * - Proper semantic HTML structure
 */
const MyArticleCard = ({ article, onView, onEdit, onDelete, onMetrics, showAuthor = false }) => {
  const [isHovered, setIsHovered] = useState(false);
  const isDraft = article.status === 'draft';

  const formatViews = (views) => {
    if (views >= 1000) {
      return `${(views / 1000).toFixed(1)}k`;
    }
    return views.toString();
  };

  return (
    <article
      className={`bg-white rounded-xl border transition-all duration-200 ${
        isHovered
          ? 'border-tmc-orange shadow-lg transform -translate-y-0.5'
          : 'border-light-gray'
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      aria-labelledby={`article-title-${article.id}`}
      aria-describedby={`article-preview-${article.id}`}
    >
      <div className="p-6">
        {/* Status Badge */}
        <div className="flex justify-between items-start mb-4">
          <StatusBadge status={isDraft ? 'draft' : 'published'} size="md" />
        </div>

        {/* Title */}
        <h3
          id={`article-title-${article.id}`}
          className="font-bold text-dark-gray text-lg leading-snug mb-3 line-clamp-2 hover:text-tmc-orange transition-colors cursor-pointer"
          onClick={() => onView(article.id)}
        >
          {article.title}
        </h3>

        {/* Preview */}
        <p
          id={`article-preview-${article.id}`}
          className="text-sm text-medium-gray leading-relaxed mb-4 line-clamp-2"
        >
          {article.preview}
        </p>

        {/* Metadata */}
        <div className="flex flex-wrap gap-4 mb-4 pb-4 border-b border-light-gray text-sm text-medium-gray">
          <div className="flex items-center gap-1.5" aria-label={`Criado em ${formatRelativeTime(article.createdAt)}`}>
            <Calendar style={{ width: '16px', height: '16px' }} aria-hidden="true" />
            <span>{formatRelativeTime(article.createdAt)}</span>
          </div>

          <div
            className="flex items-center gap-1.5"
            aria-label={`Categoria: ${article.category}`}
          >
            <Tag style={{ width: '16px', height: '16px', color: categoryColors[article.category] || '#999999' }} aria-hidden="true" />
            <span style={{ color: categoryColors[article.category] || '#999999', fontWeight: 500 }}>
              {article.category}
            </span>
          </div>

          {showAuthor && article.author && (
            <div className="flex items-center gap-1.5" aria-label={`Autor: ${article.author.name}`}>
              <User style={{ width: '16px', height: '16px' }} aria-hidden="true" />
              <span>{article.author.name}</span>
            </div>
          )}

          {!isDraft && article.views !== undefined && (
            <div className="flex items-center gap-1.5" aria-label={`${formatViews(article.views)} visualizações`}>
              <Eye style={{ width: '16px', height: '16px' }} aria-hidden="true" />
              <span>{formatViews(article.views)} visualizações</span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2" role="group" aria-label="Ações da matéria">
          {/* Ver */}
          <button
            onClick={() => onView(article.id)}
            className="flex items-center gap-2 px-4 py-2 bg-tmc-orange text-white rounded-lg text-sm font-medium hover:bg-tmc-orange/90 transition-colors focus:outline-none focus:ring-2 focus:ring-tmc-orange focus:ring-offset-2"
            aria-label={`Visualizar matéria: ${article.title}`}
          >
            <Eye style={{ width: '16px', height: '16px' }} aria-hidden="true" />
            <span>Ver</span>
          </button>

          {/* Editar */}
          <button
            onClick={() => onEdit(article.id)}
            className="flex items-center gap-2 px-4 py-2 bg-tmc-orange text-white rounded-lg text-sm font-medium hover:bg-tmc-orange/90 transition-colors focus:outline-none focus:ring-2 focus:ring-tmc-orange focus:ring-offset-2"
            aria-label={`Editar matéria: ${article.title}`}
          >
            <Edit style={{ width: '16px', height: '16px' }} aria-hidden="true" />
            <span>Editar</span>
          </button>

          {/* Excluir (apenas rascunhos) ou Métricas (publicadas) */}
          {isDraft ? (
            <button
              onClick={() => onDelete(article.id)}
              className="flex items-center gap-2 px-4 py-2 bg-white text-error-red border border-error-red rounded-lg text-sm font-medium hover:bg-red-50 transition-colors focus:outline-none focus:ring-2 focus:ring-error-red focus:ring-offset-2"
              aria-label={`Excluir matéria: ${article.title}`}
            >
              <Trash2 style={{ width: '16px', height: '16px' }} aria-hidden="true" />
              <span>Excluir</span>
            </button>
          ) : (
            <button
              onClick={() => onMetrics(article.id)}
              className="flex items-center gap-2 px-4 py-2 bg-off-white text-medium-gray border border-light-gray rounded-lg text-sm font-medium hover:bg-light-gray transition-colors focus:outline-none focus:ring-2 focus:ring-tmc-orange focus:ring-offset-2"
              aria-label={`Ver métricas da matéria: ${article.title}`}
            >
              <BarChart3 style={{ width: '16px', height: '16px' }} aria-hidden="true" />
              <span>Métricas</span>
            </button>
          )}
        </div>
      </div>
    </article>
  );
};

MyArticleCard.propTypes = {
  article: PropTypes.shape({
    id: PropTypes.number.isRequired,
    title: PropTypes.string.isRequired,
    preview: PropTypes.string.isRequired,
    status: PropTypes.oneOf(['draft', 'published']).isRequired,
    category: PropTypes.string.isRequired,
    author: PropTypes.shape({
      id: PropTypes.string,
      name: PropTypes.string,
      avatar: PropTypes.string
    }),
    createdAt: PropTypes.instanceOf(Date).isRequired,
    updatedAt: PropTypes.instanceOf(Date).isRequired,
    publishedAt: PropTypes.instanceOf(Date),
    views: PropTypes.number,
    tags: PropTypes.arrayOf(PropTypes.string)
  }).isRequired,
  onView: PropTypes.func.isRequired,
  onEdit: PropTypes.func.isRequired,
  onDelete: PropTypes.func,
  onMetrics: PropTypes.func,
  showAuthor: PropTypes.bool
};

export default MyArticleCard;
