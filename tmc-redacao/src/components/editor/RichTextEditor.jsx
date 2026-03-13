import { useEffect, useImperativeHandle, forwardRef } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Image from '@tiptap/extension-image';
import Underline from '@tiptap/extension-underline';
import Placeholder from '@tiptap/extension-placeholder';
import { FactCheckHighlightPlugin } from './FactCheckHighlightPlugin';
import PropTypes from 'prop-types';

/**
 * RichTextEditor - TipTap-based rich text editor component
 *
 * Provides WYSIWYG editing with formatting support for:
 * - Bold, Italic, Underline
 * - Bullet and Numbered lists
 * - Hyperlinks and Images
 * - Undo/Redo history
 */
const RichTextEditor = forwardRef(({
  content,
  onChange,
  placeholder = 'Comece a escrever...',
  spellCheck = false,
  editable = true,
  className = ''
}, ref) => {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Configure built-in extensions
        heading: {
          levels: [1, 2, 3]
        },
        bulletList: {
          keepMarks: true,
          keepAttributes: false,
        },
        orderedList: {
          keepMarks: true,
          keepAttributes: false,
        },
      }),
      Underline,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-tmc-orange underline hover:text-tmc-orange/80 cursor-pointer',
          target: '_blank',
          rel: 'noopener noreferrer',
        },
      }),
      Image.configure({
        inline: false,
        allowBase64: true,
        HTMLAttributes: {
          class: 'max-w-full h-auto rounded-lg my-4',
        },
      }),
      Placeholder.configure({
        placeholder,
        emptyEditorClass: 'is-editor-empty',
      }),
      FactCheckHighlightPlugin,
    ],
    content: content || '',
    editable,
    onUpdate: ({ editor }) => {
      if (onChange) {
        onChange(editor.getHTML());
      }
    },
    editorProps: {
      attributes: {
        class: `prose prose-sm max-w-none focus:outline-none min-h-[300px] p-4 ${className}`,
        spellcheck: spellCheck ? 'true' : 'false',
      },
    },
  });

  // Expose editor instance to parent via ref
  useImperativeHandle(ref, () => ({
    editor,
    // Get plain text content
    getText: () => editor?.getText() || '',
    // Get HTML content
    getHTML: () => editor?.getHTML() || '',
    // Focus the editor
    focus: () => editor?.chain().focus().run(),
    // Clear content
    clear: () => editor?.chain().clearContent().run(),
    // Set content programmatically
    setContent: (newContent) => {
      if (editor && newContent !== editor.getHTML()) {
        editor.commands.setContent(newContent, false);
      }
    },
    // Undo/Redo
    undo: () => editor?.chain().focus().undo().run(),
    redo: () => editor?.chain().focus().redo().run(),
    canUndo: () => editor?.can().undo() || false,
    canRedo: () => editor?.can().redo() || false,
  }), [editor]);

  // Update content when prop changes (for external updates like AI edits)
  useEffect(() => {
    if (editor && content !== undefined && content !== editor.getHTML()) {
      // Use setTimeout to avoid React state update during render
      const timeoutId = setTimeout(() => {
        editor.commands.setContent(content, false);
      }, 0);
      return () => clearTimeout(timeoutId);
    }
  }, [content, editor]);

  // Update spellcheck when prop changes
  useEffect(() => {
    if (editor) {
      editor.setOptions({
        editorProps: {
          attributes: {
            ...editor.options.editorProps?.attributes,
            spellcheck: spellCheck ? 'true' : 'false',
          },
        },
      });
    }
  }, [spellCheck, editor]);

  // Update editable state
  useEffect(() => {
    if (editor) {
      editor.setEditable(editable);
    }
  }, [editable, editor]);

  if (!editor) {
    return (
      <div className="min-h-[300px] p-4 animate-pulse bg-off-white rounded-lg">
        <div className="h-4 bg-light-gray rounded w-3/4 mb-2"></div>
        <div className="h-4 bg-light-gray rounded w-1/2"></div>
      </div>
    );
  }

  return (
    <div className="rich-text-editor">
      <EditorContent editor={editor} />
    </div>
  );
});

RichTextEditor.displayName = 'RichTextEditor';

RichTextEditor.propTypes = {
  content: PropTypes.string,
  onChange: PropTypes.func,
  placeholder: PropTypes.string,
  spellCheck: PropTypes.bool,
  editable: PropTypes.bool,
  className: PropTypes.string,
};

export default RichTextEditor;
