import { useState, useRef, useEffect } from 'react';
import { Check, ChevronDown, ChevronUp, Edit2, X, Save } from 'lucide-react';
import PropTypes from 'prop-types';

/**
 * ContentBlock Component
 *
 * Representa um bloco de conteúdo na página de Texto-Base.
 * Permite seleção, expansão e edição inline do conteúdo.
 */
const ContentBlock = ({
  id,
  title,
  timestamp,
  content,
  selected = false,
  expanded = false,
  editing = false,
  onSelect,
  onExpand,
  onEdit,
  onStartEdit,
  onCancelEdit
}) => {
  const [editContent, setEditContent] = useState(content);
  const textareaRef = useRef(null);
  const PREVIEW_LENGTH = 150;

  // Auto-resize textarea
  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
      textareaRef.current.focus();
    }
  }, [editing, editContent]);

  // Reset edit content when editing starts
  useEffect(() => {
    if (editing) {
      setEditContent(content);
    }
  }, [editing, content]);

  const handleSave = () => {
    if (onEdit) {
      onEdit(editContent);
    }
  };

  const handleCancel = () => {
    setEditContent(content);
    if (onCancelEdit) {
      onCancelEdit();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      handleCancel();
    } else if (e.key === 'Enter' && e.ctrlKey) {
      handleSave();
    }
  };

  const previewContent = content.length > PREVIEW_LENGTH && !expanded
    ? content.substring(0, PREVIEW_LENGTH) + '...'
    : content;

  return (
    <div
      className={`
        rounded-xl border transition-all duration-200 overflow-hidden
        ${selected
          ? 'border-l-4 border-l-tmc-orange border-t border-r border-b border-light-gray bg-orange-50/30'
          : 'border border-light-gray bg-white hover:shadow-sm'
        }
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-light-gray/50">
        <div className="flex items-center gap-3">
          {/* Custom Checkbox */}
          <button
            type="button"
            onClick={onSelect}
            className={`
              w-5 h-5 rounded border-2 flex items-center justify-center transition-all duration-200
              ${selected
                ? 'bg-tmc-orange border-tmc-orange'
                : 'border-medium-gray hover:border-tmc-orange'
              }
            `}
            aria-label={selected ? `Desselecionar ${title}` : `Selecionar ${title}`}
            aria-checked={selected}
            role="checkbox"
          >
            {selected && <Check size={12} className="text-white" strokeWidth={3} />}
          </button>

          {/* Title */}
          <h4 className="font-semibold text-dark-gray">{title}</h4>
        </div>

        {/* Timestamp */}
        {timestamp && (
          <span className="text-xs text-medium-gray bg-off-white px-2 py-1 rounded font-mono">
            {timestamp}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {editing ? (
          <div className="space-y-3">
            <textarea
              ref={textareaRef}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full p-3 border border-light-gray rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange text-sm text-dark-gray leading-relaxed"
              placeholder="Digite o conteúdo do bloco..."
              rows={4}
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-medium-gray">
                Ctrl+Enter para salvar • Esc para cancelar
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-medium-gray hover:text-dark-gray border border-light-gray rounded-lg hover:bg-off-white transition-colors"
                >
                  <X size={14} />
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-white bg-tmc-orange rounded-lg hover:bg-tmc-orange/90 transition-colors"
                >
                  <Save size={14} />
                  Salvar
                </button>
              </div>
            </div>
          </div>
        ) : (
          <p className={`text-sm text-dark-gray leading-relaxed ${!expanded && content.length > PREVIEW_LENGTH ? 'line-clamp-3' : ''}`}>
            {expanded ? content : previewContent}
          </p>
        )}
      </div>

      {/* Footer Actions */}
      {!editing && (
        <div className="flex items-center justify-end gap-2 px-4 pb-4">
          <button
            type="button"
            onClick={onStartEdit}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-medium-gray hover:text-tmc-orange border border-light-gray rounded-lg hover:border-tmc-orange/50 transition-colors"
          >
            <Edit2 size={14} />
            Editar
          </button>
          {content.length > PREVIEW_LENGTH && (
            <button
              type="button"
              onClick={onExpand}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-medium-gray hover:text-tmc-orange border border-light-gray rounded-lg hover:border-tmc-orange/50 transition-colors"
            >
              {expanded ? (
                <>
                  <ChevronUp size={14} />
                  Colapsar
                </>
              ) : (
                <>
                  <ChevronDown size={14} />
                  Expandir
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

ContentBlock.propTypes = {
  id: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
  timestamp: PropTypes.string,
  content: PropTypes.string.isRequired,
  selected: PropTypes.bool,
  expanded: PropTypes.bool,
  editing: PropTypes.bool,
  onSelect: PropTypes.func,
  onExpand: PropTypes.func,
  onEdit: PropTypes.func,
  onStartEdit: PropTypes.func,
  onCancelEdit: PropTypes.func
};

export default ContentBlock;
