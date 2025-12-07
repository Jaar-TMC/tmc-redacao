import { FileText, Search, Filter, PenLine } from 'lucide-react';

const EmptyState = ({
  icon: Icon,
  title,
  description,
  primaryAction,
  primaryActionLabel,
  secondaryAction,
  secondaryActionLabel,
  className = ''
}) => {
  return (
    <div className={`flex flex-col items-center justify-center text-center py-16 px-4 bg-white rounded-xl border border-light-gray ${className}`} role="status" aria-live="polite">
      {Icon && (
        <div className="w-20 h-20 bg-off-white rounded-full flex items-center justify-center mb-6" aria-hidden="true">
          <Icon size={40} className="text-medium-gray" aria-hidden="true" />
        </div>
      )}

      <h3 className="font-bold text-dark-gray mb-3 text-xl">
        {title}
      </h3>

      {description && (
        <p className="text-sm text-medium-gray mb-8 max-w-md leading-relaxed">
          {description}
        </p>
      )}

      <div className="flex flex-col sm:flex-row gap-3">
        {primaryAction && primaryActionLabel && (
          <button
            type="button"
            onClick={primaryAction}
            className="flex items-center justify-center gap-2 bg-tmc-orange hover:bg-tmc-orange/90 text-white px-6 py-2.5 rounded-lg font-semibold transition-colors min-h-[44px] focus:outline-none focus:ring-2 focus:ring-tmc-orange focus:ring-offset-2"
            aria-label={primaryActionLabel}
          >
            <PenLine size={18} aria-hidden="true" />
            {primaryActionLabel}
          </button>
        )}

        {secondaryAction && secondaryActionLabel && (
          <button
            type="button"
            onClick={secondaryAction}
            className="px-6 py-2.5 rounded-lg font-semibold text-medium-gray hover:text-dark-gray hover:bg-off-white transition-colors min-h-[44px] focus:outline-none focus:ring-2 focus:ring-tmc-orange focus:ring-offset-2"
            aria-label={secondaryActionLabel}
          >
            {secondaryActionLabel}
          </button>
        )}
      </div>
    </div>
  );
};

// Preset Empty States
export const EmptyStatePresets = {
  // Quando o usuário não tem nenhuma matéria
  NoArticles: ({ onCreateArticle }) => (
    <EmptyState
      icon={FileText}
      title="Nenhuma matéria criada"
      description="Você ainda não criou nenhuma matéria. Comece criando sua primeira matéria para vê-la aqui."
      primaryAction={onCreateArticle}
      primaryActionLabel="Criar Matéria"
    />
  ),

  // Quando a busca não retorna resultados
  NoResults: ({ onClearFilters }) => (
    <EmptyState
      icon={Search}
      title="Nenhum resultado encontrado"
      description="Não encontramos matérias correspondentes à sua busca. Tente usar termos diferentes ou ajuste os filtros."
      secondaryAction={onClearFilters}
      secondaryActionLabel="Limpar Busca"
    />
  ),

  // Quando os filtros não retornam resultados
  FilteredEmpty: ({ onClearFilters, onCreateArticle }) => (
    <EmptyState
      icon={Filter}
      title="Nenhuma matéria encontrada"
      description="Os filtros aplicados não retornaram resultados. Tente ajustar os filtros ou criar uma nova matéria."
      primaryAction={onCreateArticle}
      primaryActionLabel="Criar Matéria"
      secondaryAction={onClearFilters}
      secondaryActionLabel="Limpar Filtros"
    />
  )
};

export default EmptyState;
