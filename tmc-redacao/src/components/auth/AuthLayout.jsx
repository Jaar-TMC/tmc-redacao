import { useState, useEffect, useCallback, useRef } from 'react';
import PropTypes from 'prop-types';
import { FileText, Zap, ShieldCheck } from 'lucide-react';
import LogoTMC from '../../assets/logo-tmc.svg?react';

const HEADLINES = [
  {
    title: 'Governo anuncia pacote de medidas econômicas para o segundo semestre',
    body: 'O ministro da Fazenda apresentou nesta terça-feira um conjunto de propostas que visa estimular o crescimento e reduzir a pressão inflacionária sobre as famílias brasileiras.',
  },
  {
    title: 'Seleção Brasileira convoca 26 jogadores para as Eliminatórias',
    body: 'O técnico divulgou a lista com novidades no ataque e o retorno de dois veteranos da defesa. A preparação começa na próxima segunda-feira no CT da CBF.',
  },
  {
    title: 'Pesquisa revela mudança no hábito de consumo digital dos brasileiros',
    body: 'Estudo do IBGE aponta que 78% da população acessa notícias prioritariamente pelo celular, consolidando a migração do impresso para o digital.',
  },
  {
    title: 'Câmara aprova projeto que amplia acesso à internet em áreas rurais',
    body: 'A proposta segue agora para o Senado e prevê investimentos de R$ 3,2 bilhões em infraestrutura de conectividade nos próximos cinco anos.',
  },
];

const STATS = [
  { icon: FileText, text: 'Matérias geradas em segundos' },
  { icon: Zap, text: 'Integração com feeds em tempo real' },
  { icon: ShieldCheck, text: 'Verificação factual automatizada' },
];

function TypingEditor() {
  const [headlineIndex, setHeadlineIndex] = useState(0);
  const [displayTitle, setDisplayTitle] = useState('');
  const [displayBody, setDisplayBody] = useState('');
  const [phase, setPhase] = useState('typing-title'); // typing-title | typing-body | paused | fading
  const [opacity, setOpacity] = useState(1);
  const timeoutRef = useRef(null);

  const headline = HEADLINES[headlineIndex];

  const clear = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
  };

  // Realistic variable typing speed
  const getDelay = useCallback(() => 28 + Math.random() * 44, []);

  useEffect(() => {
    clear();

    if (phase === 'typing-title') {
      if (displayTitle.length < headline.title.length) {
        timeoutRef.current = setTimeout(() => {
          setDisplayTitle(headline.title.slice(0, displayTitle.length + 1));
        }, getDelay());
      } else {
        timeoutRef.current = setTimeout(() => setPhase('typing-body'), 300);
      }
    }

    if (phase === 'typing-body') {
      if (displayBody.length < headline.body.length) {
        timeoutRef.current = setTimeout(() => {
          setDisplayBody(headline.body.slice(0, displayBody.length + 1));
        }, getDelay());
      } else {
        timeoutRef.current = setTimeout(() => setPhase('paused'), 2200);
      }
    }

    if (phase === 'paused') {
      setPhase('fading');
    }

    if (phase === 'fading') {
      setOpacity(0);
      timeoutRef.current = setTimeout(() => {
        setDisplayTitle('');
        setDisplayBody('');
        setHeadlineIndex((prev) => (prev + 1) % HEADLINES.length);
        setOpacity(1);
        setPhase('typing-title');
      }, 700);
    }

    return clear;
  }, [phase, displayTitle, displayBody, headline, getDelay]);

  // Skeleton lines for visual weight
  const skeletonLines = [100, 85, 92, 60];

  return (
    <div
      className="w-full max-w-md transition-opacity duration-700 ease-in-out"
      style={{ opacity }}
    >
      {/* Editor chrome */}
      <div className="rounded-xl overflow-hidden bg-white/[0.07] backdrop-blur-sm border border-white/10 shadow-2xl">
        {/* Title bar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10">
          <div className="w-3 h-3 rounded-full bg-red-400/60" />
          <div className="w-3 h-3 rounded-full bg-yellow-400/60" />
          <div className="w-3 h-3 rounded-full bg-green-400/60" />
          <span className="ml-2 text-xs text-white/30 font-mono">editor — nova matéria</span>
        </div>

        {/* Content area */}
        <div className="p-5 min-h-[200px]">
          {/* Title */}
          <div className="mb-4">
            <p className="text-white font-bold text-lg leading-snug min-h-[3.5rem]">
              {displayTitle}
              {phase === 'typing-title' && (
                <span className="inline-block w-[2px] h-5 bg-tmc-orange ml-0.5 align-middle animate-pulse" />
              )}
            </p>
          </div>

          {/* Separator */}
          <div className="w-12 h-0.5 bg-tmc-orange/50 mb-4 rounded-full" />

          {/* Body text or skeleton */}
          {displayBody ? (
            <p className="text-white/60 text-sm leading-relaxed">
              {displayBody}
              {phase === 'typing-body' && (
                <span className="inline-block w-[2px] h-4 bg-tmc-orange ml-0.5 align-middle animate-pulse" />
              )}
            </p>
          ) : (
            phase === 'typing-title' && (
              <div className="space-y-2.5">
                {skeletonLines.map((width, i) => (
                  <div
                    key={i}
                    className="h-3 rounded-full bg-white/[0.06]"
                    style={{ width: `${width}%` }}
                  />
                ))}
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}

function AuthLayout({ children }) {
  return (
    <div className="min-h-screen flex">
      {/* Left: Branding (hidden on mobile) */}
      <div className="hidden lg:flex lg:w-1/2 bg-tmc-dark-green flex-col items-center justify-center p-12 text-white relative overflow-hidden">
        {/* Subtle background pattern */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, white 1px, transparent 0)`,
            backgroundSize: '32px 32px',
          }}
        />

        <div className="relative z-10 flex flex-col items-center max-w-lg">
          <LogoTMC className="h-32 w-auto mb-6" aria-label="TMC" />
          <h1 className="text-2xl font-bold text-center mb-2">
            Ferramenta de Redação Jornalística
          </h1>
          <p className="text-white/50 text-sm mb-10">
            Inteligência artificial a serviço da informação
          </p>

          {/* Typing editor animation */}
          <TypingEditor />

          {/* Stats */}
          <div className="mt-10 flex flex-col gap-3 w-full max-w-md">
            {STATS.map((stat, i) => {
              const Icon = stat.icon;
              return (
                <div
                  key={i}
                  className="flex items-center gap-3 text-white/40 animate-[fadeSlideUp_0.6s_ease-out_forwards] opacity-0"
                  style={{ animationDelay: `${1.2 + i * 0.2}s` }}
                >
                  <Icon size={16} className="text-tmc-orange/60 flex-shrink-0" aria-hidden="true" />
                  <span className="text-sm">{stat.text}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Right: Form area */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 bg-white">
        {/* Mobile logo */}
        <div className="w-full max-w-md">
          <div className="lg:hidden flex flex-col items-center mb-8">
            <LogoTMC className="h-20 w-auto mb-2" aria-label="TMC" />
            <p className="text-sm text-medium-gray">Ferramenta de Redação</p>
          </div>
          {children}
        </div>
      </div>

      {/* Keyframe for stats fade-in */}
      <style>{`
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

AuthLayout.propTypes = { children: PropTypes.node.isRequired };

export default AuthLayout;
