import { useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import {
  Bold,
  Italic,
  Underline,
  List,
  ListOrdered,
  Link2,
  Image,
  Undo,
  Redo,
  Heading1,
  Heading2,
  Quote,
  Code,
  Minus,
  X
} from 'lucide-react';
import Tooltip from '../ui/Tooltip';

// Formatting button helper - defined outside component to avoid re-creation on each render
const ToolbarButton = ({ onClick, isActive, disabled, tooltip, shortcut, children, ariaLabel }) => (
  <Tooltip content={tooltip} shortcut={shortcut}>
    <button
      onClick={onClick}
      disabled={disabled}
      className={`p-2 rounded transition-colors ${
        isActive
          ? 'bg-tmc-orange/20 text-tmc-orange'
          : disabled
          ? 'text-light-gray cursor-not-allowed'
          : 'hover:bg-off-white text-medium-gray'
      }`}
      aria-label={ariaLabel || tooltip}
      aria-pressed={isActive}
    >
      {children}
    </button>
  </Tooltip>
);

ToolbarButton.propTypes = {
  onClick: PropTypes.func,
  isActive: PropTypes.bool,
  disabled: PropTypes.bool,
  tooltip: PropTypes.string,
  shortcut: PropTypes.string,
  children: PropTypes.node,
  ariaLabel: PropTypes.string,
};

/**
 * EditorToolbar - Formatting toolbar for TipTap editor
 *
 * Provides buttons for text formatting that interact with the editor instance.
 */
const EditorToolbar = ({
  editor,
  onUndo,
  onRedo,
  canUndo = false,
  canRedo = false,
  versionCount = 1,
  currentIndex = 0,
  showVersionDropdown,
  onToggleVersionDropdown,
  VersionDropdownComponent
}) => {
  const [linkModalOpen, setLinkModalOpen] = useState(false);
  const [imageModalOpen, setImageModalOpen] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [imageUrl, setImageUrl] = useState('');

  // Link modal handlers - must be defined before early return to maintain hook order
  const handleAddLink = useCallback(() => {
    if (linkUrl && editor) {
      // Ensure URL has protocol
      const url = linkUrl.startsWith('http') ? linkUrl : `https://${linkUrl}`;
      editor.chain().focus().setLink({ href: url }).run();
      setLinkUrl('');
      setLinkModalOpen(false);
    }
  }, [editor, linkUrl]);

  const handleRemoveLink = useCallback(() => {
    if (editor) {
      editor.chain().focus().unsetLink().run();
      setLinkModalOpen(false);
    }
  }, [editor]);

  // Image modal handlers
  const handleAddImage = useCallback(() => {
    if (imageUrl && editor) {
      editor.chain().focus().setImage({ src: imageUrl }).run();
      setImageUrl('');
      setImageModalOpen(false);
    }
  }, [editor, imageUrl]);

  // Check if editor is ready - return empty toolbar placeholder
  if (!editor) {
    return (
      <div className="flex items-center gap-1 flex-wrap h-10">
        <div className="animate-pulse flex gap-1">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="w-8 h-8 bg-light-gray/50 rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {/* Text Formatting */}
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBold().run()}
        isActive={editor.isActive('bold')}
        tooltip="Negrito"
        shortcut="Ctrl+B"
        ariaLabel="Negrito"
      >
        <Bold size={18} />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleItalic().run()}
        isActive={editor.isActive('italic')}
        tooltip="Itálico"
        shortcut="Ctrl+I"
        ariaLabel="Itálico"
      >
        <Italic size={18} />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        isActive={editor.isActive('underline')}
        tooltip="Sublinhado"
        shortcut="Ctrl+U"
        ariaLabel="Sublinhado"
      >
        <Underline size={18} />
      </ToolbarButton>

      <div className="w-px h-6 bg-light-gray mx-2" />

      {/* Headings */}
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        isActive={editor.isActive('heading', { level: 2 })}
        tooltip="Subtítulo"
        ariaLabel="Subtítulo"
      >
        <Heading2 size={18} />
      </ToolbarButton>

      {/* Lists */}
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        isActive={editor.isActive('bulletList')}
        tooltip="Lista com marcadores"
        ariaLabel="Lista com marcadores"
      >
        <List size={18} />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        isActive={editor.isActive('orderedList')}
        tooltip="Lista numerada"
        ariaLabel="Lista numerada"
      >
        <ListOrdered size={18} />
      </ToolbarButton>

      <div className="w-px h-6 bg-light-gray mx-2" />

      {/* Block Elements */}
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
        isActive={editor.isActive('blockquote')}
        tooltip="Citação"
        ariaLabel="Citação"
      >
        <Quote size={18} />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().setHorizontalRule().run()}
        tooltip="Linha horizontal"
        ariaLabel="Linha horizontal"
      >
        <Minus size={18} />
      </ToolbarButton>

      <div className="w-px h-6 bg-light-gray mx-2" />

      {/* Links and Images */}
      <ToolbarButton
        onClick={() => {
          // Get current link if any
          const previousUrl = editor.getAttributes('link').href || '';
          setLinkUrl(previousUrl);
          setLinkModalOpen(true);
        }}
        isActive={editor.isActive('link')}
        tooltip="Inserir link"
        shortcut="Ctrl+K"
        ariaLabel="Inserir link"
      >
        <Link2 size={18} />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => setImageModalOpen(true)}
        tooltip="Inserir imagem"
        ariaLabel="Inserir imagem"
      >
        <Image size={18} />
      </ToolbarButton>

      <div className="w-px h-6 bg-light-gray mx-2" />

      {/* Undo/Redo */}
      <ToolbarButton
        onClick={onUndo}
        disabled={!canUndo}
        tooltip={canUndo ? `Desfazer (${versionCount - 1} versões)` : 'Nada para desfazer'}
        shortcut="Ctrl+Z"
        ariaLabel="Desfazer"
      >
        <Undo size={18} />
      </ToolbarButton>

      <ToolbarButton
        onClick={onRedo}
        disabled={!canRedo}
        tooltip={canRedo ? 'Refazer' : 'Nada para refazer'}
        shortcut="Ctrl+Y"
        ariaLabel="Refazer"
      >
        <Redo size={18} />
      </ToolbarButton>

      {/* Version Dropdown */}
      {versionCount > 1 && VersionDropdownComponent && (
        <div className="relative">
          <Tooltip content="Ver histórico de versões" position="bottom">
            <button
              onClick={onToggleVersionDropdown}
              className="flex items-center gap-1 px-2 py-1.5 text-xs text-medium-gray
                         hover:bg-off-white rounded transition-colors"
            >
              <span className="font-medium">v{currentIndex + 1}</span>
              <span className="text-light-gray">/{versionCount}</span>
            </button>
          </Tooltip>
          {showVersionDropdown && VersionDropdownComponent}
        </div>
      )}

      {/* Link Modal */}
      {linkModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-dark-gray">Inserir Link</h3>
              <button
                onClick={() => setLinkModalOpen(false)}
                className="p-1 hover:bg-off-white rounded"
              >
                <X size={20} className="text-medium-gray" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-dark-gray mb-1">
                  URL do Link
                </label>
                <input
                  type="url"
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  placeholder="https://exemplo.com"
                  className="w-full px-4 py-2 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleAddLink();
                    }
                  }}
                />
              </div>
              <div className="flex gap-2 justify-end">
                {editor.isActive('link') && (
                  <button
                    onClick={handleRemoveLink}
                    className="px-4 py-2 text-sm font-medium text-error border border-error rounded-lg hover:bg-error/5"
                  >
                    Remover Link
                  </button>
                )}
                <button
                  onClick={() => setLinkModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-medium-gray border border-light-gray rounded-lg hover:bg-off-white"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleAddLink}
                  disabled={!linkUrl.trim()}
                  className="px-4 py-2 text-sm font-medium text-white bg-tmc-orange rounded-lg hover:bg-tmc-orange/90 disabled:opacity-50"
                >
                  Adicionar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Image Modal */}
      {imageModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-dark-gray">Inserir Imagem</h3>
              <button
                onClick={() => setImageModalOpen(false)}
                className="p-1 hover:bg-off-white rounded"
              >
                <X size={20} className="text-medium-gray" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-dark-gray mb-1">
                  URL da Imagem
                </label>
                <input
                  type="url"
                  value={imageUrl}
                  onChange={(e) => setImageUrl(e.target.value)}
                  placeholder="https://exemplo.com/imagem.jpg"
                  className="w-full px-4 py-2 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleAddImage();
                    }
                  }}
                />
              </div>
              {imageUrl && (
                <div className="border border-light-gray rounded-lg p-2">
                  <p className="text-xs text-medium-gray mb-2">Pré-visualização:</p>
                  <img
                    src={imageUrl}
                    alt="Preview"
                    className="max-h-32 mx-auto rounded"
                    loading="lazy"
                    decoding="async"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                </div>
              )}
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setImageModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-medium-gray border border-light-gray rounded-lg hover:bg-off-white"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleAddImage}
                  disabled={!imageUrl.trim()}
                  className="px-4 py-2 text-sm font-medium text-white bg-tmc-orange rounded-lg hover:bg-tmc-orange/90 disabled:opacity-50"
                >
                  Adicionar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

EditorToolbar.propTypes = {
  editor: PropTypes.object,
  onUndo: PropTypes.func,
  onRedo: PropTypes.func,
  canUndo: PropTypes.bool,
  canRedo: PropTypes.bool,
  versionCount: PropTypes.number,
  currentIndex: PropTypes.number,
  showVersionDropdown: PropTypes.bool,
  onToggleVersionDropdown: PropTypes.func,
  VersionDropdownComponent: PropTypes.node,
};

export default EditorToolbar;
