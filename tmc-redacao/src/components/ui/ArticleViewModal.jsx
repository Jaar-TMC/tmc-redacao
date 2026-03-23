import { useEffect, useCallback, memo } from 'react';
import PropTypes from 'prop-types';
import DOMPurify from 'dompurify';
import { X, Calendar, Tag, User, Clock, Edit3, ExternalLink } from 'lucide-react';
import { markdownToHtml } from '../../utils/markdownRenderer';

/**
 * StatusBadge - Displays article publication status
 * Extracted outside of ArticleViewModal to avoid component re-creation on every render.
 */
const StatusBadge = ({ status }) => {
  const isPublished = status === 'published';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
      isPublished
        ? 'bg-green-100 text-green-700'
        : 'bg-orange-100 text-orange-700'
    }`}>
      {isPublished ? 'Publicado' : 'Rascunho'}
    </span>
  );
};

StatusBadge.propTypes = {
  status: PropTypes.oneOf(['draft', 'published'])
};

/**
 * ArticleViewModal - Modal para visualizar matéria formatada
 *
 * Displays a full formatted view of an article with:
 * - Title and linha fina
 * - Formatted content (markdown rendered)
 * - Metadata (date, category, tags, author)
 * - Action buttons (edit, close)
 */
const ArticleViewModal = ({ article, isOpen, onClose, onEdit }) => {
  // Handle ESC key to close
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEsc);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEsc);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  const handleBackdropClick = useCallback((e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  }, [onClose]);

  if (!isOpen || !article) return null;

  // Format dates
  const formatDate = (date) => {
    if (!date) return null;
    const d = date instanceof Date ? date : new Date(date);
    return d.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Render content as HTML from markdown (sanitized via DOMPurify)
  const renderContent = () => {
    if (!article.content) return null;
    const html = markdownToHtml(article.content);
    return { __html: DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'strong', 'em', 'b', 'i', 'u', 'ul', 'ol', 'li', 'blockquote', 'br', 'img', 'hr', 'span', 'div', 'sup', 'sub'],
      ALLOWED_ATTR: ['href', 'target', 'rel', 'src', 'alt', 'class', 'id']
    }) };
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-8"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="article-view-title"
    >
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header - fixed at top */}
        <div className="flex items-center justify-between p-4 border-b border-light-gray bg-white rounded-t-xl shrink-0">
          <div className="flex items-center gap-3">
            <StatusBadge status={article.status} />
            {article.category && (
              <span className="text-sm text-medium-gray">{article.category}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {onEdit && (
              <button
                onClick={() => onEdit(article.id)}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-tmc-orange hover:bg-orange-50 rounded-lg transition-colors"
              >
                <Edit3 size={16} />
                <span>Editar</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 text-medium-gray hover:text-dark-gray hover:bg-off-white rounded-lg transition-colors"
              aria-label="Fechar visualização"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Content - scrollable */}
        <div className="p-6 md:p-8 overflow-y-auto flex-1 min-h-0">
          {/* Title */}
          <h1
            id="article-view-title"
            className="text-2xl md:text-3xl font-bold text-dark-gray mb-3"
          >
            {article.title}
          </h1>

          {/* Linha Fina */}
          {article.linhaFina && (
            <p className="text-lg text-medium-gray mb-6 leading-relaxed">
              {article.linhaFina}
            </p>
          )}

          {/* Metadata row */}
          <div className="flex flex-wrap items-center gap-4 text-sm text-medium-gray mb-6 pb-6 border-b border-light-gray">
            {article.author && (
              <div className="flex items-center gap-1.5">
                <User size={14} />
                <span>{article.author.name || 'Autor'}</span>
              </div>
            )}
            {article.createdAt && (
              <div className="flex items-center gap-1.5">
                <Calendar size={14} />
                <span>{formatDate(article.createdAt)}</span>
              </div>
            )}
            {article.updatedAt && article.updatedAt !== article.createdAt && (
              <div className="flex items-center gap-1.5">
                <Clock size={14} />
                <span>Atualizado: {formatDate(article.updatedAt)}</span>
              </div>
            )}
          </div>

          {/* Article Content */}
          <article
            className="prose prose-lg max-w-none prose-headings:text-dark-gray prose-p:text-medium-gray prose-a:text-tmc-orange prose-strong:text-dark-gray"
            dangerouslySetInnerHTML={renderContent()}
          />

          {/* Tags */}
          {article.tags && article.tags.length > 0 && (
            <div className="mt-8 pt-6 border-t border-light-gray">
              <div className="flex items-center gap-2 flex-wrap">
                <Tag size={16} className="text-medium-gray" />
                {article.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-3 py-1 bg-off-white text-medium-gray text-sm rounded-full"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Source articles info */}
          {article.sourceArticleIds && article.sourceArticleIds.length > 0 && (
            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
              <div className="flex items-center gap-2 text-sm text-blue-700">
                <ExternalLink size={14} />
                <span>
                  Esta matéria foi criada a partir de {article.sourceArticleIds.length} fonte(s) de referência.
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Footer - fixed at bottom */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-light-gray bg-off-white rounded-b-xl shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-medium-gray hover:text-dark-gray transition-colors"
          >
            Fechar
          </button>
          {onEdit && (
            <button
              onClick={() => onEdit(article.id)}
              className="px-4 py-2 text-sm font-semibold text-white bg-tmc-orange rounded-lg hover:bg-tmc-orange/90 transition-colors"
            >
              Editar Matéria
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

ArticleViewModal.propTypes = {
  article: PropTypes.shape({
    id: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    linhaFina: PropTypes.string,
    content: PropTypes.string,
    status: PropTypes.oneOf(['draft', 'published']),
    category: PropTypes.string,
    tags: PropTypes.arrayOf(PropTypes.string),
    author: PropTypes.shape({
      id: PropTypes.string,
      name: PropTypes.string,
      avatar: PropTypes.string
    }),
    createdAt: PropTypes.oneOfType([PropTypes.string, PropTypes.instanceOf(Date)]),
    updatedAt: PropTypes.oneOfType([PropTypes.string, PropTypes.instanceOf(Date)]),
    publishedAt: PropTypes.oneOfType([PropTypes.string, PropTypes.instanceOf(Date)]),
    sourceArticleIds: PropTypes.arrayOf(PropTypes.string)
  }),
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onEdit: PropTypes.func
};

export default memo(ArticleViewModal);
