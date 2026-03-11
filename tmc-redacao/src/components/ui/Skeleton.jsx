import { memo } from 'react';

const Skeleton = memo(({ className = '', variant = 'default' }) => {
  const baseClasses = 'bg-light-gray animate-pulse rounded';

  const variants = {
    default: 'h-4 w-full',
    text: 'h-4 w-full',
    title: 'h-6 w-3/4',
    avatar: 'h-12 w-12 rounded-full',
    card: 'h-48 w-full',
    button: 'h-10 w-24',
    circle: 'h-8 w-8 rounded-full'
  };

  const variantClass = variants[variant] || variants.default;

  return (
    <div
      className={`${baseClasses} ${variantClass} ${className}`}
      role="status"
      aria-label="Carregando conteúdo"
    >
      <span className="sr-only">Carregando...</span>
    </div>
  );
});

Skeleton.displayName = 'Skeleton';

export default Skeleton;
