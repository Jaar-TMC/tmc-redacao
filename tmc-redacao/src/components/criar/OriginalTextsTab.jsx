import { useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import { ExternalLink, Edit3, RotateCcw, Check, Lightbulb } from 'lucide-react';

/**
 * SourceTextEditor - Editable text block for a single source
 */
const SourceTextEditor = ({
  article,
  editedText,
  originalText,
  onTextChange
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [localText, setLocalText] = useState(editedText);

  const hasChanges = editedText !== originalText;

  const handleSave = useCallback(() => {
    onTextChange(article.id, localText);
    setIsEditing(false);
  }, [article.id, localText, onTextChange]);

  const handleCancel = useCallback(() => {
    setLocalText(editedText);
    setIsEditing(false);
  }, [editedText]);

  const handleReset = useCallback(() => {
    setLocalText(originalText);
    onTextChange(article.id, originalText);
    setIsEditing(false);
  }, [article.id, originalText, onTextChange]);

  const wordCount = localText?.split(/\s+/).filter(Boolean).length || 0;

  return (
    <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-off-white border-b border-light-gray">
        <div className="flex items-center gap-3">
          {article.favicon && (
            <img
              src={article.favicon}
              alt=""
              className="w-6 h-6 rounded"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
          )}
          <div>
            <h4 className="font-semibold text-dark-gray">
              {article.source || 'Fonte'}
            </h4>
            <p className="text-xs text-medium-gray line-clamp-1">
              {article.title}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {hasChanges && (
            <span className="text-xs text-tmc-orange bg-tmc-orange/10 px-2 py-1 rounded">
              Editado
            </span>
          )}
          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-sm text-medium-gray hover:text-tmc-orange transition-colors"
            >
              <ExternalLink size={14} />
              <span className="hidden sm:inline">Ver original</span>
            </a>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {isEditing ? (
          <div className="space-y-3">
            <textarea
              value={localText}
              onChange={(e) => setLocalText(e.target.value)}
              className="w-full h-64 p-3 border border-light-gray rounded-lg text-sm text-dark-gray leading-relaxed resize-y focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
              placeholder="Edite o texto para manter apenas o que interessa..."
            />

            <div className="flex items-center justify-between">
              <span className="text-xs text-medium-gray">
                {wordCount} palavras
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleCancel}
                  className="px-3 py-1.5 text-sm text-medium-gray hover:text-dark-gray transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSave}
                  className="flex items-center gap-1 px-3 py-1.5 bg-tmc-orange text-white text-sm rounded-lg hover:bg-tmc-orange/90 transition-colors"
                >
                  <Check size={14} />
                  Salvar
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div>
            <p className="text-sm text-dark-gray leading-relaxed whitespace-pre-wrap">
              {editedText || 'Sem conteúdo disponível'}
            </p>

            <div className="flex items-center justify-between mt-4 pt-4 border-t border-light-gray">
              <span className="text-xs text-medium-gray">
                {wordCount} palavras
              </span>

              <div className="flex items-center gap-2">
                {hasChanges && (
                  <button
                    onClick={handleReset}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-medium-gray hover:text-dark-gray transition-colors"
                    title="Restaurar texto original"
                  >
                    <RotateCcw size={14} />
                    <span className="hidden sm:inline">Restaurar</span>
                  </button>
                )}
                <button
                  onClick={() => {
                    setLocalText(editedText);
                    setIsEditing(true);
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 border border-light-gray text-sm text-medium-gray rounded-lg hover:border-tmc-orange hover:text-tmc-orange transition-colors"
                >
                  <Edit3 size={14} />
                  Editar para manter apenas o que interessa
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

SourceTextEditor.propTypes = {
  article: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    title: PropTypes.string,
    source: PropTypes.string,
    favicon: PropTypes.string,
    url: PropTypes.string
  }).isRequired,
  editedText: PropTypes.string,
  originalText: PropTypes.string,
  onTextChange: PropTypes.func.isRequired
};

/**
 * OriginalTextsTab - Shows all original texts side-by-side with edit capability
 */
const OriginalTextsTab = ({
  articles,
  editedTexts,
  onTextEdit
}) => {
  // Calculate total word count
  const totalWordCount = Object.values(editedTexts).reduce((sum, item) => {
    const words = item?.edited?.split(/\s+/).filter(Boolean).length || 0;
    return sum + words;
  }, 0);

  const editedCount = Object.values(editedTexts).filter(
    item => item?.edited !== item?.original
  ).length;

  return (
    <div className="space-y-4">
      {/* Tip banner */}
      <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
        <Lightbulb size={20} className="text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm">
          <p className="font-medium text-amber-800 mb-1">
            Dica: Edite os textos para refinar
          </p>
          <p className="text-amber-700">
            Remova partes que não deseja incluir na sua matéria. As edições serão usadas na geração.
            Você pode editar cada texto individualmente e restaurar o original a qualquer momento.
          </p>
        </div>
      </div>

      {/* Source texts */}
      <div className="space-y-4">
        {articles.map((article) => {
          const textData = editedTexts[article.id] || {
            original: article.content || article.preview || '',
            edited: article.content || article.preview || ''
          };

          return (
            <SourceTextEditor
              key={article.id}
              article={article}
              editedText={textData.edited}
              originalText={textData.original}
              onTextChange={onTextEdit}
            />
          );
        })}
      </div>

      {/* Summary */}
      <div className="flex items-center justify-between p-4 bg-off-white rounded-lg text-sm">
        <div className="flex items-center gap-4 text-medium-gray">
          <span>
            <strong className="text-dark-gray">{articles.length}</strong> fontes
          </span>
          <span>•</span>
          <span>
            <strong className="text-dark-gray">~{totalWordCount}</strong> palavras no total
          </span>
          {editedCount > 0 && (
            <>
              <span>•</span>
              <span className="text-tmc-orange">
                <strong>{editedCount}</strong> {editedCount === 1 ? 'texto editado' : 'textos editados'}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

OriginalTextsTab.propTypes = {
  articles: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      title: PropTypes.string,
      content: PropTypes.string,
      preview: PropTypes.string,
      source: PropTypes.string,
      favicon: PropTypes.string,
      url: PropTypes.string
    })
  ).isRequired,
  editedTexts: PropTypes.object.isRequired,
  onTextEdit: PropTypes.func.isRequired
};

export default OriginalTextsTab;
