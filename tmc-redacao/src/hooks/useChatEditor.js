/**
 * useChatEditor Hook
 *
 * Bridges the chat assistant with article editing functionality.
 * Handles sending edit instructions to the AI API and managing chat messages.
 *
 * @example
 * const {
 *   messages,
 *   sendMessage,
 *   isProcessing,
 *   clearMessages
 * } = useChatEditor({
 *   articleState: { title, linhaFina, content, tags },
 *   onEdit: (newContent, summary, messageId) => pushVersion(newContent, 'ai', summary, messageId),
 *   categoria: 'geral',
 *   tom: 'conversacional'
 * });
 */

import { useState, useCallback } from 'react';
import { editArticle } from '../services/api';

/**
 * Generate a unique ID for messages
 * @returns {string} UUID-like identifier
 */
function generateMessageId() {
  return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Chat editor hook for AI-powered article editing
 *
 * @param {Object} options - Hook options
 * @param {Object} options.articleState - Current article state
 * @param {string} options.articleState.title - Current title
 * @param {string} options.articleState.linhaFina - Current subtitle
 * @param {string} options.articleState.content - Current body content
 * @param {string[]} options.articleState.tags - Current tags
 * @param {Function} options.onEdit - Callback when edit is applied: (newContent, summary, messageId) => void
 * @param {string} [options.categoria='geral'] - Editorial category
 * @param {string} [options.tom='conversacional'] - Writing tone
 * @param {Object[]} [options.initialMessages=[]] - Initial chat messages
 * @returns {Object} Chat state and controls
 */
export function useChatEditor({
  articleState,
  onEdit,
  categoria = 'geral',
  tom = 'conversacional',
  initialMessages = []
}) {
  const [messages, setMessages] = useState(initialMessages);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Add a message to the chat
   * @param {string} type - Message type: 'user' | 'ai' | 'system' | 'error'
   * @param {string} content - Message content
   * @param {Object} [metadata={}] - Optional metadata
   * @returns {string} Message ID
   */
  const addMessage = useCallback((type, content, metadata = {}) => {
    const messageId = generateMessageId();
    const newMessage = {
      id: messageId,
      type,
      content,
      timestamp: Date.now(),
      ...metadata
    };

    setMessages((prev) => [...prev, newMessage]);
    return messageId;
  }, []);

  /**
   * Send an edit instruction to the AI
   * @param {string} instruction - User's edit instruction
   * @param {string} [editScope='full'] - Scope of edit
   * @returns {Promise<Object|null>} Edit result or null if failed
   */
  const sendMessage = useCallback(async (instruction, editScope = 'full') => {
    if (!instruction.trim() || isProcessing) return null;

    setError(null);

    // Add user message
    const userMessageId = addMessage('user', instruction);

    // Add loading message
    const loadingMessageId = addMessage('ai', 'Analisando e editando o artigo...', {
      isLoading: true
    });

    setIsProcessing(true);

    try {
      // Call the edit API
      const result = await editArticle({
        currentArticle: {
          title: articleState.title || '',
          linhaFina: articleState.linhaFina || '',
          content: articleState.content || '',
          tags: articleState.tags || []
        },
        instruction,
        editScope,
        categoria,
        tom
      });

      // Remove loading message
      setMessages((prev) => prev.filter((m) => m.id !== loadingMessageId));

      // Add pending approval message with changes summary
      // Changes are NOT applied until user approves
      const aiMessageId = addMessage('ai', result.changes_summary || 'Proposta de edição:', {
        editResult: {
          titulo: result.titulo,
          linha_fina: result.linha_fina,
          conteudo: result.conteudo,
          tags: result.tags
        },
        isPendingApproval: true,
        originalInstruction: instruction
      });

      setIsProcessing(false);
      return result;

    } catch (err) {
      console.error('Error editing article:', err);

      // Remove loading message
      setMessages((prev) => prev.filter((m) => m.id !== loadingMessageId));

      // Add error message
      addMessage('error', `Erro ao editar: ${err.message || 'Erro desconhecido'}`, {
        isError: true
      });

      setError(err.message || 'Erro ao processar edição');
      setIsProcessing(false);
      return null;
    }
  }, [articleState, categoria, tom, isProcessing, addMessage, onEdit]);

  /**
   * Send a general question (not an edit) to the assistant
   * This can be used for non-editing interactions
   * @param {string} question - User's question
   */
  const sendQuestion = useCallback(async (question) => {
    if (!question.trim() || isProcessing) return;

    // Add user message
    addMessage('user', question);

    // For MVP, respond with a helpful message suggesting edit instructions
    setTimeout(() => {
      addMessage('ai',
        'Posso ajudar você a editar o artigo. Tente me pedir algo como:\n\n' +
        '• "Melhore o SEO do título"\n' +
        '• "Torne o texto mais formal"\n' +
        '• "Resuma o conteúdo"\n' +
        '• "Adicione mais contexto sobre o tema"\n' +
        '• "Corrija erros gramaticais"'
      );
    }, 500);
  }, [isProcessing, addMessage]);

  /**
   * Approve a pending edit and apply changes
   * @param {string} messageId - ID of the message with pending edit
   */
  const approveEdit = useCallback((messageId) => {
    setMessages((prev) => prev.map((msg) => {
      if (msg.id === messageId && msg.isPendingApproval) {
        // Call onEdit with the stored editResult
        if (onEdit && msg.editResult) {
          onEdit(
            {
              title: msg.editResult.titulo,
              linhaFina: msg.editResult.linha_fina,
              body: msg.editResult.conteudo,
              tags: msg.editResult.tags
            },
            `AI: ${msg.content || msg.originalInstruction?.slice(0, 50)}`,
            messageId
          );
        }
        // Update message state
        return {
          ...msg,
          isPendingApproval: false,
          isApproved: true,
          isEdit: true
        };
      }
      return msg;
    }));
  }, [onEdit]);

  /**
   * Reject a pending edit and discard changes
   * @param {string} messageId - ID of the message with pending edit
   */
  const rejectEdit = useCallback((messageId) => {
    setMessages((prev) => prev.map((msg) => {
      if (msg.id === messageId && msg.isPendingApproval) {
        return {
          ...msg,
          isPendingApproval: false,
          isRejected: true,
          content: msg.content + '\n\n(Alterações rejeitadas pelo usuário)'
        };
      }
      return msg;
    }));
  }, []);

  /**
   * Request a modification to a pending edit
   * @param {string} messageId - ID of the message with pending edit
   * @param {string} modificationRequest - User's modification request
   * @returns {Promise<Object|null>} Edit result or null if failed
   */
  const requestModification = useCallback(async (messageId, modificationRequest) => {
    if (!modificationRequest.trim() || isProcessing) return null;

    // Find the pending message with the edit result
    const pendingMessage = messages.find(m => m.id === messageId && m.isPendingApproval);
    if (!pendingMessage || !pendingMessage.editResult) return null;

    // Mark the old pending message as modified (no longer pending)
    setMessages((prev) => prev.map((msg) => {
      if (msg.id === messageId) {
        return {
          ...msg,
          isPendingApproval: false,
          isModified: true,
          content: msg.content + '\n\n(Solicitada modificação)'
        };
      }
      return msg;
    }));

    // Add user's modification request as a new message
    addMessage('user', `Ajuste: ${modificationRequest}`);

    // Add loading message
    const loadingMessageId = addMessage('ai', 'Ajustando a proposta...', { isLoading: true });
    setIsProcessing(true);

    try {
      // Call API with the proposed content + modification instruction
      const result = await editArticle({
        currentArticle: {
          title: pendingMessage.editResult.titulo || '',
          linhaFina: pendingMessage.editResult.linha_fina || '',
          content: pendingMessage.editResult.conteudo || '',
          tags: pendingMessage.editResult.tags || []
        },
        instruction: modificationRequest,
        editScope: 'full',
        categoria,
        tom
      });

      // Remove loading, add new pending message
      setMessages((prev) => prev.filter((m) => m.id !== loadingMessageId));

      addMessage('ai', result.changes_summary || 'Proposta ajustada:', {
        editResult: {
          titulo: result.titulo,
          linha_fina: result.linha_fina,
          conteudo: result.conteudo,
          tags: result.tags
        },
        isPendingApproval: true,
        originalInstruction: modificationRequest
      });

      setIsProcessing(false);
      return result;
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== loadingMessageId));
      addMessage('error', `Erro ao ajustar: ${err.message || 'Erro desconhecido'}`, { isError: true });
      setIsProcessing(false);
      return null;
    }
  }, [messages, isProcessing, addMessage, categoria, tom]);

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  /**
   * Set initial/welcome messages
   * @param {Object[]} welcomeMessages - Array of messages to set
   */
  const setWelcomeMessages = useCallback((welcomeMessages) => {
    setMessages(welcomeMessages.map((msg, index) => ({
      id: generateMessageId(),
      timestamp: Date.now() + index,
      ...msg
    })));
  }, []);

  /**
   * Revert to a previous version by clicking on a chat message
   * @param {string} messageId - ID of the message/version to revert to
   */
  const revertToMessage = useCallback((messageId) => {
    // This will be handled by the parent component using the version history
    // Just add a system message indicating the revert
    addMessage('system', 'Versão restaurada. Você pode continuar editando a partir daqui.');
  }, [addMessage]);

  return {
    // Chat state
    messages,
    isProcessing,
    error,

    // Chat actions
    sendMessage,
    sendQuestion,
    addMessage,
    clearMessages,
    setWelcomeMessages,
    revertToMessage,

    // Approval workflow actions
    approveEdit,
    rejectEdit,
    requestModification
  };
}

export default useChatEditor;
