import { useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
import { FileText, X, ExternalLink, Newspaper } from 'lucide-react';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function truncate(text, max = 300) {
  if (!text || text.length <= max) return text;
  return text.slice(0, max) + '...';
}

function hasSourceData(fonteData) {
  if (!fonteData) return false;
  if (Array.isArray(fonteData)) return fonteData.length > 0;
  return Object.keys(fonteData).length > 0;
}

// ---------------------------------------------------------------------------
// Source renderers by fonteTipo
// ---------------------------------------------------------------------------

function FeedSourceCards({ articles }) {
  return (
    <div className="flex flex-col gap-3">
      {articles.map((article, idx) => (
        <div
          key={article.id || idx}
          className="bg-off-white rounded-lg p-4"
        >
          {article.title && (
            <h4 className="text-sm font-semibold text-dark-gray mb-1">
              {article.title}
            </h4>
          )}
          {(article.source_name || article.source || article.fonte) && (
            <span className="inline-block rounded-full bg-tmc-orange/10 text-tmc-orange text-xs font-medium px-2 py-0.5 mb-2">
              {article.source_name || article.source || article.fonte}
            </span>
          )}
          {article.content && (
            <p className="text-sm text-medium-gray leading-relaxed">
              {truncate(article.content)}
            </p>
          )}
          {(article.link || article.url) && (
            <a
              href={article.link || article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-2 text-xs text-tmc-orange hover:underline"
            >
              <ExternalLink className="h-3 w-3" />
              Ver original
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

FeedSourceCards.propTypes = {
  articles: PropTypes.array.isRequired,
};

function SourceSection({ fonteData, fonteTipo }) {
  if (!hasSourceData(fonteData)) return null;

  if (fonteTipo === 'feed' || fonteTipo === 'tema') {
    const articles = Array.isArray(fonteData) ? fonteData : [fonteData];
    return <FeedSourceCards articles={articles} />;
  }

  if (fonteTipo === 'video' || fonteTipo === 'transcription') {
    const data = Array.isArray(fonteData) ? fonteData[0] : fonteData;
    return (
      <div className="bg-off-white rounded-lg p-4">
        {data?.title && (
          <h4 className="text-sm font-semibold text-dark-gray mb-1">{data.title}</h4>
        )}
        {(data?.url || data?.link) && (
          <a
            href={data.url || data.link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-tmc-orange hover:underline"
          >
            <ExternalLink className="h-3 w-3" />
            Ver vídeo
          </a>
        )}
      </div>
    );
  }

  if (fonteTipo === 'link') {
    const url = typeof fonteData === 'string' ? fonteData : fonteData?.url || fonteData?.link;
    return (
      <div className="bg-off-white rounded-lg p-4">
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-tmc-orange hover:underline break-all"
          >
            <ExternalLink className="h-3.5 w-3.5 shrink-0" />
            {url}
          </a>
        )}
      </div>
    );
  }

  if (fonteTipo === 'prompt') {
    return (
      <div className="bg-off-white rounded-lg p-4 text-sm text-medium-gray">
        Gerado a partir de prompt de pesquisa
      </div>
    );
  }

  if (fonteTipo === 'zero') {
    return (
      <div className="bg-off-white rounded-lg p-4 text-sm text-medium-gray">
        Texto inserido manualmente
      </div>
    );
  }

  return null;
}

SourceSection.propTypes = {
  fonteData: PropTypes.oneOfType([PropTypes.array, PropTypes.object, PropTypes.string]),
  fonteTipo: PropTypes.string,
};

// ---------------------------------------------------------------------------
// BaseTextModal
// ---------------------------------------------------------------------------

export default function BaseTextModal({ isOpen, onClose, blocos = [], textoCompleto, fonteData, fonteTipo }) {
  // ESC key + body scroll lock (matches ArticleViewModal pattern)
  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKey);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleKey);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  const handleBackdropClick = useCallback((e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  }, [onClose]);

  if (!isOpen) return null;

  const hasSource = hasSourceData(fonteData);
  const hasBaseText = blocos.length > 0 || textoCompleto;
  const isEmpty = !hasSource && !hasBaseText;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="base-text-modal-title"
    >
      <div
        className="relative flex flex-col bg-white rounded-2xl shadow-2xl max-w-3xl w-full mx-4 max-h-[85vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-[#1A4D2E] to-[#2D5A3D] px-6 py-4 text-white shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="absolute top-3 right-3 rounded-full p-1.5 text-white/70 hover:text-white hover:bg-white/15 transition-colors"
            aria-label="Fechar"
          >
            <X className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-white/80" />
            <h2 id="base-text-modal-title" className="text-base font-semibold tracking-tight">
              Texto Base
            </h2>
          </div>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 p-6">
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="h-12 w-12 text-light-gray mb-3" />
              <h3 className="text-base font-semibold text-dark-gray mb-1">
                Nenhum texto base disponível
              </h3>
              <p className="text-sm text-medium-gray">
                O texto base não está disponível para matérias editadas.
              </p>
            </div>
          ) : (
            <>
              {hasSource && (
                <div>
                  <h3 className="flex items-center gap-1.5 text-sm font-semibold text-dark-gray mb-3">
                    <Newspaper className="h-4 w-4" />
                    Matérias Originais
                  </h3>
                  <SourceSection fonteData={fonteData} fonteTipo={fonteTipo} />
                </div>
              )}

              {hasSource && hasBaseText && (
                <hr className="border-light-gray my-6" />
              )}

              {hasBaseText && (
                <div>
                  <h3 className="flex items-center gap-1.5 text-sm font-semibold text-dark-gray mb-3">
                    <FileText className="h-4 w-4" />
                    Texto Base Utilizado
                  </h3>
                  {blocos.length > 0 ? (
                    <div className="flex flex-col gap-3">
                      {blocos.map((bloco, idx) => (
                        <div key={bloco.id || idx} className="bg-off-white rounded-lg p-4">
                          {(bloco.source || bloco.title) && (
                            <p className="text-xs font-medium text-medium-gray mb-1">
                              {bloco.title || bloco.source}
                            </p>
                          )}
                          <p className="text-sm text-dark-gray whitespace-pre-wrap">
                            {bloco.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-off-white rounded-lg p-4">
                      <p className="whitespace-pre-wrap text-sm text-dark-gray">
                        {textoCompleto}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-light-gray p-4 flex justify-end shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="bg-off-white hover:bg-light-gray text-dark-gray px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}

BaseTextModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  blocos: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    content: PropTypes.string,
    source: PropTypes.string,
    title: PropTypes.string,
  })),
  textoCompleto: PropTypes.string,
  fonteData: PropTypes.oneOfType([PropTypes.array, PropTypes.object]),
  fonteTipo: PropTypes.string,
};
