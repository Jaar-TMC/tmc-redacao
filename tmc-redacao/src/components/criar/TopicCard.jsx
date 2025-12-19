import { useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import { Check, Edit2, Save, X, ChevronDown, ChevronUp } from 'lucide-react';

/**
 * TopicCard - Card de topico selecionavel e editavel
 *
 * Usado nas variantes de Link e Feed para mostrar topicos extraidos.
 */

// Tipos de topicos com cores
const topicTypes = {
  fato: { label: 'FATO PRINCIPAL', color: 'bg-blue-100 text-blue-700' },
  contexto: { label: 'CONTEXTO', color: 'bg-purple-100 text-purple-700' },
  causa: { label: 'CAUSA', color: 'bg-yellow-100 text-yellow-700' },
  consequencia: { label: 'CONSEQUÊNCIA', color: 'bg-orange-100 text-orange-700' },
  acao: { label: 'AÇÃO/REAÇÃO', color: 'bg-green-100 text-green-700' },
  declaracao: { label: 'DECLARAÇÃO', color: 'bg-pink-100 text-pink-700' },
  dado: { label: 'DADO', color: 'bg-cyan-100 text-cyan-700' },
  intro: { label: 'INTRODUÇÃO', color: 'bg-indigo-100 text-indigo-700' }
};

const TopicCard = ({
  id,
  type = 'fato',
  text,
  source,
  selected = false,
  onToggle,
  onEdit,
  expandable = false
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(text);

  const typeConfig = topicTypes[type] || topicTypes.fato;

  const handleToggle = useCallback((e) => {
    e.stopPropagation();
    onToggle(id);
  }, [id, onToggle]);

  const handleStartEdit = useCallback((e) => {
    e.stopPropagation();
    setIsEditing(true);
    setEditText(text);
  }, [text]);

  const handleSaveEdit = useCallback((e) => {
    e.stopPropagation();
    if (editText.trim() && editText !== text) {
      onEdit(id, editText.trim());
    }
    setIsEditing(false);
  }, [id, editText, text, onEdit]);

  const handleCancelEdit = useCallback((e) => {
    e.stopPropagation();
    setEditText(text);
    setIsEditing(false);
  }, [text]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSaveEdit(e);
    }
    if (e.key === 'Escape') {
      handleCancelEdit(e);
    }
  }, [handleSaveEdit, handleCancelEdit]);

  const toggleExpand = useCallback((e) => {
    e.stopPropagation();
    setIsExpanded(prev => !prev);
  }, []);

  // Truncar texto para preview
  const getPreviewText = () => {
    const maxChars = 120;
    if (text.length <= maxChars || isExpanded) return text;
    return text.substring(0, maxChars) + '...';
  };

  return (
    <div
      className={`
        relative bg-white rounded-lg border p-4
        transition-all duration-200 cursor-pointer
        ${selected
          ? 'border-tmc-orange bg-orange-50'
          : 'border-light-gray hover:border-tmc-orange/50 hover:shadow-sm'
        }
      `}
      onClick={handleToggle}
    >
      {/* Header com checkbox e tipo */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-3">
          {/* Checkbox */}
          <div
            role="checkbox"
            aria-checked={selected}
            tabIndex={0}
            onClick={handleToggle}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleToggle(e);
              }
            }}
            className={`
              w-5 h-5 rounded border-2 flex items-center justify-center
              transition-colors flex-shrink-0
              ${selected
                ? 'bg-tmc-orange border-tmc-orange'
                : 'border-medium-gray bg-white hover:border-tmc-orange'
              }
            `}
          >
            {selected && <Check className="w-3 h-3 text-white" />}
          </div>

          {/* Tipo do topico */}
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${typeConfig.color}`}>
            {typeConfig.label}
          </span>
        </div>

        {/* Acoes */}
        <div className="flex items-center gap-1">
          {!isEditing && onEdit && (
            <button
              onClick={handleStartEdit}
              className="p-1 text-medium-gray hover:text-tmc-orange transition-colors rounded hover:bg-tmc-orange/10"
              title="Editar"
            >
              <Edit2 size={14} />
            </button>
          )}
          {expandable && text.length > 120 && !isEditing && (
            <button
              onClick={toggleExpand}
              className="p-1 text-medium-gray hover:text-tmc-orange transition-colors rounded hover:bg-tmc-orange/10"
              title={isExpanded ? 'Colapsar' : 'Expandir'}
            >
              {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          )}
        </div>
      </div>

      {/* Conteudo */}
      {isEditing ? (
        <div className="ml-8" onClick={(e) => e.stopPropagation()}>
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full p-2 text-sm border border-light-gray rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
            rows={3}
            autoFocus
          />
          <div className="flex items-center gap-2 mt-2">
            <button
              onClick={handleSaveEdit}
              className="flex items-center gap-1 px-3 py-1 text-xs bg-tmc-orange text-white rounded hover:bg-tmc-orange/90 transition-colors"
            >
              <Save size={12} />
              Salvar
            </button>
            <button
              onClick={handleCancelEdit}
              className="flex items-center gap-1 px-3 py-1 text-xs text-medium-gray hover:text-dark-gray transition-colors"
            >
              <X size={12} />
              Cancelar
            </button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-dark-gray leading-relaxed ml-8">
          {getPreviewText()}
        </p>
      )}

      {/* Fonte */}
      {source && !isEditing && (
        <p className="text-xs text-medium-gray mt-2 ml-8">
          Fonte: {source}
        </p>
      )}
    </div>
  );
};

TopicCard.propTypes = {
  id: PropTypes.string.isRequired,
  type: PropTypes.oneOf(['fato', 'contexto', 'causa', 'consequencia', 'acao', 'declaracao', 'dado', 'intro']),
  text: PropTypes.string.isRequired,
  source: PropTypes.string,
  selected: PropTypes.bool,
  onToggle: PropTypes.func.isRequired,
  onEdit: PropTypes.func,
  expandable: PropTypes.bool
};

export default TopicCard;
