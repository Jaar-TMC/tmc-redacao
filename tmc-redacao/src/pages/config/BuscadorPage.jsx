import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Plus, Edit2, Trash2, X, Check, ExternalLink, Newspaper } from 'lucide-react';
import { mockSources, formatRelativeTime } from '../../data/mockData';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import StatusMessage from '../../components/ui/StatusMessage';
import Skeleton from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';

/**
 * BuscadorPage - News source configuration page
 * Manages RSS feed sources for automated news collection
 *
 * Features:
 * - Add/edit/delete news sources
 * - Configure collection frequency
 * - Toggle sources active/inactive
 * - Accessibility-focused with ARIA labels and keyboard navigation
 * - Focus trap for modal dialogs
 * - Screen reader announcements for state changes
 *
 * WCAG 2.1 Compliance:
 * - No Keyboard Trap (2.1.2): Modal can be closed with Escape key, focus trap implemented
 * - Sensory Characteristics (1.3.3): Toggle switches include text labels "Ativo"/"Inativo"
 * - Timing Adjustable (2.2.1): Frequency controls allow users to adjust collection timing
 * - Headings and Labels (2.4.6): All form inputs have descriptive labels
 */
const BuscadorPage = () => {
  const [sources, setSources] = useState(mockSources);
  const [showModal, setShowModal] = useState(false);
  const [editingSource, setEditingSource] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    category: 'Notícias Gerais',
    frequency: '1h',
    onlyFeatured: false
  });
  const [deleteConfirm, setDeleteConfirm] = useState({ isOpen: false, source: null });
  const [statusMessage, setStatusMessage] = useState({ isVisible: false, type: 'success', message: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const modalRef = useRef(null);
  const previousFocusRef = useRef(null);

  const frequencies = useMemo(() => [
    { value: '15min', label: 'A cada 15 minutos' },
    { value: '30min', label: 'A cada 30 minutos' },
    { value: '1h', label: 'A cada 1 hora' },
    { value: '2h', label: 'A cada 2 horas' },
    { value: '6h', label: 'A cada 6 horas' }
  ], []);

  const categories = useMemo(() => [
    'Notícias Gerais',
    'Política',
    'Economia',
    'Esportes',
    'Tecnologia',
    'Entretenimento'
  ], []);

  const activeSources = useMemo(() => sources.filter(s => s.active).length, [sources]);
  const totalArticles = 156;

  // Focus trap for modal
  useEffect(() => {
    if (showModal && modalRef.current) {
      previousFocusRef.current = document.activeElement;

      const focusableElements = modalRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      firstElement?.focus();

      const handleTabKey = (e) => {
        if (e.key !== 'Tab') return;

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      };

      const handleEscKey = (e) => {
        if (e.key === 'Escape') {
          handleCloseModal();
        }
      };

      document.addEventListener('keydown', handleTabKey);
      document.addEventListener('keydown', handleEscKey);

      return () => {
        document.removeEventListener('keydown', handleTabKey);
        document.removeEventListener('keydown', handleEscKey);
      };
    }
  }, [showModal]);

  const announceToScreenReader = useCallback((message) => {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    document.body.appendChild(announcement);
    setTimeout(() => document.body.removeChild(announcement), 1000);
  }, []);

  const handleToggleActive = useCallback((id, sourceName) => {
    const source = sources.find(s => s.id === id);
    const newStatus = !source.active;
    setSources(sources.map(s => s.id === id ? { ...s, active: newStatus } : s));

    // Announce to screen readers
    const message = `${sourceName} ${newStatus ? 'ativada' : 'desativada'}`;
    announceToScreenReader(message);
  }, [sources, announceToScreenReader]);

  const handleDeleteClick = useCallback((source) => {
    setDeleteConfirm({ isOpen: true, source });
  }, []);

  const handleDeleteConfirm = useCallback(() => {
    if (deleteConfirm.source) {
      setSources(sources.filter(s => s.id !== deleteConfirm.source.id));
      setStatusMessage({
        isVisible: true,
        type: 'success',
        message: `Fonte "${deleteConfirm.source.name}" excluída com sucesso`
      });
      setDeleteConfirm({ isOpen: false, source: null });
    }
  }, [deleteConfirm.source, sources]);

  const handleOpenModal = useCallback((source = null) => {
    if (source) {
      setEditingSource(source);
      setFormData({
        name: source.name,
        url: source.url,
        category: 'Notícias Gerais',
        frequency: source.frequency,
        onlyFeatured: false
      });
    } else {
      setEditingSource(null);
      setFormData({
        name: '',
        url: '',
        category: 'Notícias Gerais',
        frequency: '1h',
        onlyFeatured: false
      });
    }
    setShowModal(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setShowModal(false);
    // Return focus to previously focused element
    if (previousFocusRef.current) {
      previousFocusRef.current.focus();
    }
  }, []);

  const handleSubmit = useCallback((e) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Simulate async operation
    setTimeout(() => {
      if (editingSource) {
        setSources(sources.map(s =>
          s.id === editingSource.id
            ? { ...s, name: formData.name, url: formData.url, frequency: formData.frequency }
            : s
        ));
        setStatusMessage({
          isVisible: true,
          type: 'success',
          message: `Fonte "${formData.name}" atualizada com sucesso`
        });
      } else {
        const newSource = {
          id: Date.now(),
          name: formData.name,
          url: formData.url,
          favicon: `https://www.google.com/s2/favicons?domain=${formData.url}&sz=32`,
          active: true,
          frequency: formData.frequency,
          lastFetch: new Date()
        };
        setSources([...sources, newSource]);
        setStatusMessage({
          isVisible: true,
          type: 'success',
          message: `Fonte "${formData.name}" adicionada com sucesso`
        });
      }
      setIsSubmitting(false);
      handleCloseModal();
    }, 500);
  }, [editingSource, formData, sources, handleCloseModal]);

  return (
    <div>
      {/* Status Message */}
      {statusMessage.isVisible && (
        <div className="mb-4">
          <StatusMessage
            type={statusMessage.type}
            message={statusMessage.message}
            isVisible={statusMessage.isVisible}
            onDismiss={() => setStatusMessage({ ...statusMessage, isVisible: false })}
          />
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-dark-gray">Buscador de notícias</h1>
          <p className="text-medium-gray mt-1">
            Configure as fontes de onde deseja coletar matérias
          </p>
        </div>
        <button
          type="button"
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2 bg-tmc-orange text-white px-4 py-2.5 rounded-lg font-semibold hover:bg-tmc-orange/90 transition-colors min-h-[44px]"
          aria-label="Adicionar nova fonte de notícias"
        >
          <Plus size={20} aria-hidden="true" />
          Adicionar nova fonte
        </button>
      </div>

      {/* Desktop Table */}
      <div className="hidden md:block bg-white rounded-xl border border-light-gray overflow-hidden">
        <table className="w-full" role="table" aria-label="Lista de fontes de notícias">
          <thead className="bg-off-white border-b border-light-gray">
            <tr>
              <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                Status
              </th>
              <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                Fonte
              </th>
              <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                URL
              </th>
              <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                Frequência
              </th>
              <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                Última Coleta
              </th>
              <th scope="col" className="text-right px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">
                Ações
              </th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.id} className="border-b border-light-gray last:border-0 hover:bg-off-white/50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleToggleActive(source.id, source.name)}
                      className={`w-12 h-6 rounded-full transition-colors relative ${
                        source.active ? 'bg-success' : 'bg-light-gray'
                      }`}
                      role="switch"
                      aria-checked={source.active}
                      aria-label={`${source.name}: ${source.active ? 'Ativa' : 'Inativa'}`}
                    >
                      <span className="sr-only">
                        {source.active ? 'Desativar' : 'Ativar'} {source.name}
                      </span>
                      <span
                        className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                          source.active ? 'left-7' : 'left-1'
                        }`}
                        aria-hidden="true"
                      />
                    </button>
                    <span className={`text-sm font-medium ${source.active ? 'text-success' : 'text-medium-gray'}`}>
                      {source.active ? 'Ativo' : 'Inativo'}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <img src={source.favicon} alt="" className="w-6 h-6 rounded" aria-hidden="true" />
                    <span className="font-medium text-dark-gray">{source.name}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <a
                    href={`https://${source.url}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-tmc-orange hover:underline flex items-center gap-1"
                    aria-label={`Abrir ${source.url} em nova aba`}
                  >
                    {source.url}
                    <ExternalLink size={14} aria-hidden="true" />
                  </a>
                </td>
                <td className="px-6 py-4">
                  <label htmlFor={`frequency-${source.id}`} className="sr-only">
                    Frequência de coleta para {source.name}
                  </label>
                  <select
                    id={`frequency-${source.id}`}
                    value={source.frequency}
                    onChange={(e) => setSources(sources.map(s =>
                      s.id === source.id ? { ...s, frequency: e.target.value } : s
                    ))}
                    className="text-sm bg-off-white border border-light-gray rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-tmc-orange/50"
                    aria-label={`Alterar frequência de coleta para ${source.name}`}
                  >
                    {frequencies.map((f) => (
                      <option key={f.value} value={f.value}>{f.label}</option>
                    ))}
                  </select>
                </td>
                <td className="px-6 py-4 text-medium-gray text-sm">
                  <span aria-label={`Última coleta: ${formatRelativeTime(source.lastFetch)}`}>
                    {formatRelativeTime(source.lastFetch)}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => handleOpenModal(source)}
                      className="p-2 hover:bg-light-gray rounded-lg transition-colors min-h-[44px] min-w-[44px]"
                      aria-label={`Editar ${source.name}`}
                      title="Editar"
                    >
                      <Edit2 size={16} className="text-medium-gray" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteClick(source)}
                      className="p-2 hover:bg-error/10 rounded-lg transition-colors min-h-[44px] min-w-[44px]"
                      aria-label={`Excluir ${source.name}`}
                      title="Excluir"
                    >
                      <Trash2 size={16} className="text-error" aria-hidden="true" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Cards */}
      <div className="md:hidden space-y-4">
        {sources.map((source) => (
          <div key={source.id} className="bg-white rounded-xl border border-light-gray p-4">
            {/* Header with toggle and actions */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <img src={source.favicon} alt="" className="w-8 h-8 rounded" aria-hidden="true" />
                <div>
                  <h3 className="font-medium text-dark-gray">{source.name}</h3>
                  <p className="text-xs text-medium-gray">{formatRelativeTime(source.lastFetch)}</p>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <button
                  type="button"
                  onClick={() => handleToggleActive(source.id, source.name)}
                  className={`w-12 h-6 rounded-full transition-colors relative ${
                    source.active ? 'bg-success' : 'bg-light-gray'
                  }`}
                  role="switch"
                  aria-checked={source.active}
                  aria-label={`${source.name}: ${source.active ? 'Ativa' : 'Inativa'}`}
                >
                  <span className="sr-only">
                    {source.active ? 'Desativar' : 'Ativar'} {source.name}
                  </span>
                  <span
                    className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                      source.active ? 'left-7' : 'left-1'
                    }`}
                    aria-hidden="true"
                  />
                </button>
                <span className={`text-xs font-medium ${source.active ? 'text-success' : 'text-medium-gray'}`}>
                  {source.active ? 'Ativo' : 'Inativo'}
                </span>
              </div>
            </div>

            {/* URL */}
            <a
              href={`https://${source.url}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-tmc-orange hover:underline flex items-center gap-1 text-sm mb-3"
              aria-label={`Abrir ${source.url} em nova aba`}
            >
              <span className="truncate">{source.url}</span>
              <ExternalLink size={14} className="flex-shrink-0" aria-hidden="true" />
            </a>

            {/* Frequency */}
            <div className="mb-3">
              <label htmlFor={`frequency-mobile-${source.id}`} className="block text-xs text-medium-gray mb-1">
                Frequência
              </label>
              <select
                id={`frequency-mobile-${source.id}`}
                value={source.frequency}
                onChange={(e) => setSources(sources.map(s =>
                  s.id === source.id ? { ...s, frequency: e.target.value } : s
                ))}
                className="w-full text-sm bg-off-white border border-light-gray rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-tmc-orange/50"
              >
                {frequencies.map((f) => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-3 border-t border-light-gray">
              <button
                type="button"
                onClick={() => handleOpenModal(source)}
                className="flex-1 flex items-center justify-center gap-2 py-2 hover:bg-off-white rounded-lg transition-colors text-sm font-medium text-dark-gray min-h-[44px]"
                aria-label={`Editar ${source.name}`}
              >
                <Edit2 size={16} aria-hidden="true" />
                <span>Editar</span>
              </button>
              <button
                type="button"
                onClick={() => handleDeleteClick(source)}
                className="flex-1 flex items-center justify-center gap-2 py-2 hover:bg-error/10 rounded-lg transition-colors text-sm font-medium text-error min-h-[44px]"
                aria-label={`Excluir ${source.name}`}
              >
                <Trash2 size={16} aria-hidden="true" />
                <span>Excluir</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Stats Footer */}
      <div className="mt-4 text-center text-sm text-medium-gray" role="status" aria-live="polite">
        <span className="font-semibold text-dark-gray">{activeSources}</span> fontes ativas |{' '}
        <span className="font-semibold text-dark-gray">{totalArticles}</span> matérias coletadas hoje
      </div>

      {/* Modal */}
      {showModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          <div ref={modalRef} className="bg-white rounded-xl w-full max-w-md p-6 m-4">
            <div className="flex items-center justify-between mb-6">
              <h2 id="modal-title" className="text-xl font-bold text-dark-gray">
                {editingSource ? 'Editar fonte' : 'Adicionar nova fonte'}
              </h2>
              <button
                type="button"
                onClick={handleCloseModal}
                className="p-2 hover:bg-off-white rounded-lg transition-colors"
                aria-label="Fechar modal"
              >
                <X size={20} className="text-medium-gray" aria-hidden="true" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="source-name" className="block text-sm font-medium text-dark-gray mb-1">
                  Nome da fonte <span className="text-error" aria-label="obrigatório">*</span>
                </label>
                <p id="source-name-help" className="text-xs text-medium-gray mb-2">Como você quer identificar esta fonte</p>
                <div className="relative">
                  <input
                    id="source-name"
                    name="organization"
                    type="text"
                    required
                    maxLength={50}
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-2.5 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                    placeholder="Ex: G1, Folha, ESPN..."
                    aria-required="true"
                    aria-describedby="source-name-help"
                    autoComplete="organization"
                  />
                  <span className="absolute right-3 bottom-2.5 text-xs text-medium-gray" aria-live="polite">
                    {formData.name.length}/50
                  </span>
                </div>
              </div>

              <div>
                <label htmlFor="source-url" className="block text-sm font-medium text-dark-gray mb-1">
                  URL do feed RSS (Really Simple Syndication) <span className="text-error" aria-label="obrigatório">*</span>
                </label>
                <p id="url-description" className="text-xs text-medium-gray mb-2">Cole o link do feed RSS da fonte</p>
                <input
                  id="source-url"
                  name="source-url"
                  type="url"
                  required
                  maxLength={500}
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  className="w-full px-4 py-2.5 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                  placeholder="Ex: https://g1.globo.com/rss/g1"
                  aria-required="true"
                  aria-describedby="url-description url-help"
                  autoComplete="url"
                />
                <p id="url-help" className="text-xs text-medium-gray mt-1">
                  Use o formato: site.com/rss ou site.com/feed
                </p>
              </div>

              <div>
                <label htmlFor="source-category" className="block text-sm font-medium text-dark-gray mb-1">
                  Categoria
                </label>
                <select
                  id="source-category"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-4 py-2.5 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                >
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="source-frequency" className="block text-sm font-medium text-dark-gray mb-1">
                  Frequência de coleta
                </label>
                <p className="text-xs text-medium-gray mb-2">Com que frequência devemos buscar novas matérias</p>
                <select
                  id="source-frequency"
                  value={formData.frequency}
                  onChange={(e) => setFormData({ ...formData, frequency: e.target.value })}
                  className="w-full px-4 py-2.5 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                >
                  {frequencies.map((f) => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                  ))}
                </select>
              </div>

              <label htmlFor="only-featured" className="flex items-center gap-3 cursor-pointer">
                <input
                  id="only-featured"
                  type="checkbox"
                  checked={formData.onlyFeatured}
                  onChange={(e) => setFormData({ ...formData, onlyFeatured: e.target.checked })}
                  className="w-4 h-4 text-tmc-orange border-light-gray rounded focus:ring-tmc-orange/50"
                />
                <span className="text-sm text-dark-gray">
                  Coletar apenas matérias em destaque
                </span>
              </label>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="flex-1 py-2.5 border border-light-gray rounded-lg text-medium-gray hover:bg-off-white transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-2.5 bg-tmc-orange text-white rounded-lg font-semibold hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]"
                >
                  {isSubmitting ? 'Salvando...' : (editingSource ? 'Salvar alterações' : 'Adicionar fonte')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm({ isOpen: false, source: null })}
        onConfirm={handleDeleteConfirm}
        title="Confirmar exclusão"
        message={`Você está prestes a excluir a fonte "${deleteConfirm.source?.name}". Todas as matérias coletadas desta fonte serão perdidas. Esta ação não pode ser desfeita.`}
        confirmText="Excluir permanentemente"
        cancelText="Cancelar"
        variant="danger"
      />
    </div>
  );
};

export default BuscadorPage;
