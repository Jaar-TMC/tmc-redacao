const EmptyState = ({
  icon: Icon,
  title,
  description,
  action,
  actionLabel,
  className = ''
}) => {
  return (
    <div className={`flex flex-col items-center justify-center text-center py-12 px-4 ${className}`} role="status" aria-live="polite">
      {Icon && (
        <div className="w-16 h-16 bg-off-white rounded-full flex items-center justify-center mb-4" aria-hidden="true">
          <Icon size={32} className="text-light-gray" aria-hidden="true" />
        </div>
      )}

      <h3 className="font-semibold text-dark-gray mb-2 text-lg">
        {title}
      </h3>

      {description && (
        <p className="text-sm text-medium-gray mb-6 max-w-md">
          {description}
        </p>
      )}

      {action && actionLabel && (
        <button
          type="button"
          onClick={action}
          className="bg-tmc-orange hover:bg-tmc-orange/90 text-white px-6 py-2.5 rounded-lg font-semibold transition-colors min-h-[44px]"
          aria-label={actionLabel}
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};

export default EmptyState;
