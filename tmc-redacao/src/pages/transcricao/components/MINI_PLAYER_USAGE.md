# MiniPlayer - Guia de Uso

## Visão Geral

O componente `MiniPlayer` é um player de vídeo fixo que aparece automaticamente quando o player principal do YouTube sai da viewport. Ele permite que o usuário continue assistindo o vídeo enquanto rola a página para ver a transcrição.

## Características

- Aparece/desaparece automaticamente usando IntersectionObserver
- Posição configurável (bottom-right, bottom-left, top-right, top-left)
- Controles básicos: play/pause, expandir/minimizar, fechar
- Tamanho compacto (~320px) com opção de expandir
- Animação suave de entrada/saída
- Atalhos de teclado (Espaço, Esc)
- Sincronização de tempo com player principal (opcional)
- Z-index alto (50) para ficar acima de outros elementos
- Integração completa com YouTube IFrame API

## Instalação

O componente já está exportado em `src/pages/transcricao/components/index.js`:

```javascript
export { default as MiniPlayer } from './MiniPlayer';
```

## Props

| Prop | Tipo | Obrigatório | Default | Descrição |
|------|------|-------------|---------|-----------|
| `videoId` | string | Sim | - | ID do vídeo do YouTube |
| `isMainPlayerVisible` | boolean | Sim | - | Se o player principal está visível na viewport |
| `currentTime` | number | Não | 0 | Tempo atual do vídeo em segundos |
| `onTimeUpdate` | function | Não | - | Callback chamado quando o tempo é atualizado (recebe tempo em segundos) |
| `position` | string | Não | 'bottom-right' | Posição do mini player: 'bottom-right', 'bottom-left', 'top-right', 'top-left' |

## Exemplo de Uso Básico

```jsx
import { useState, useRef, useEffect } from 'react';
import { MiniPlayer } from './components';

function TranscricaoPage() {
  const [videoData, setVideoData] = useState({ videoId: 'dQw4w9WgXcQ' });
  const [isMainPlayerVisible, setIsMainPlayerVisible] = useState(true);
  const mainPlayerRef = useRef(null);

  // Observar visibilidade do player principal
  useEffect(() => {
    if (!mainPlayerRef.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsMainPlayerVisible(entry.isIntersecting);
      },
      { threshold: 0.5 } // 50% visível
    );

    observer.observe(mainPlayerRef.current);

    return () => observer.disconnect();
  }, []);

  return (
    <div>
      {/* Player Principal */}
      <div ref={mainPlayerRef} className="aspect-video">
        <iframe
          src={`https://www.youtube.com/embed/${videoData.videoId}`}
          className="w-full h-full"
          allowFullScreen
        />
      </div>

      {/* Transcrição (conteúdo longo) */}
      <div className="mt-6">
        {/* Transcrição aqui */}
      </div>

      {/* Mini Player */}
      <MiniPlayer
        videoId={videoData.videoId}
        isMainPlayerVisible={isMainPlayerVisible}
      />
    </div>
  );
}
```

## Exemplo Completo com Sincronização

```jsx
import { useState, useRef, useEffect } from 'react';
import { MiniPlayer } from './components';

function TranscricaoPage() {
  const [videoData, setVideoData] = useState({ videoId: 'dQw4w9WgXcQ' });
  const [isMainPlayerVisible, setIsMainPlayerVisible] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const mainPlayerRef = useRef(null);
  const mainYouTubePlayerRef = useRef(null);

  // Observar visibilidade do player principal
  useEffect(() => {
    if (!mainPlayerRef.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsMainPlayerVisible(entry.isIntersecting);
      },
      { threshold: 0.5 }
    );

    observer.observe(mainPlayerRef.current);

    return () => observer.disconnect();
  }, []);

  // Inicializar YouTube Player principal
  useEffect(() => {
    if (!window.YT || !mainPlayerRef.current) return;

    mainYouTubePlayerRef.current = new window.YT.Player('main-player', {
      videoId: videoData.videoId,
      events: {
        onStateChange: (event) => {
          if (event.data === window.YT.PlayerState.PLAYING) {
            const interval = setInterval(() => {
              if (mainYouTubePlayerRef.current) {
                const time = mainYouTubePlayerRef.current.getCurrentTime();
                setCurrentTime(time);
              }
            }, 1000);
            return () => clearInterval(interval);
          }
        }
      }
    });
  }, [videoData.videoId]);

  // Callback quando mini player atualiza o tempo
  const handleMiniPlayerTimeUpdate = (time) => {
    setCurrentTime(time);
    // Opcionalmente, sincronizar com player principal
    if (mainYouTubePlayerRef.current && isMainPlayerVisible) {
      mainYouTubePlayerRef.current.seekTo(time, true);
    }
  };

  return (
    <div>
      {/* Player Principal */}
      <div ref={mainPlayerRef} className="aspect-video">
        <div id="main-player" />
      </div>

      {/* Transcrição */}
      <div className="mt-6">
        {/* Transcrição aqui */}
      </div>

      {/* Mini Player com sincronização */}
      <MiniPlayer
        videoId={videoData.videoId}
        isMainPlayerVisible={isMainPlayerVisible}
        currentTime={currentTime}
        onTimeUpdate={handleMiniPlayerTimeUpdate}
        position="bottom-right"
      />
    </div>
  );
}
```

## Posicionamento

O componente oferece 4 posições predefinidas:

```jsx
// Canto inferior direito (padrão)
<MiniPlayer position="bottom-right" {...props} />

// Canto inferior esquerdo
<MiniPlayer position="bottom-left" {...props} />

// Canto superior direito
<MiniPlayer position="top-right" {...props} />

// Canto superior esquerdo
<MiniPlayer position="top-left" {...props} />
```

## Atalhos de Teclado

O MiniPlayer suporta os seguintes atalhos quando está visível:

- **Espaço**: Play/Pause
- **Esc**: Minimizar (se estiver expandido)

## Estados do Componente

O MiniPlayer gerencia internamente vários estados:

- **isVisible**: Controlado por `isMainPlayerVisible`
- **isExpanded**: Alterna entre tamanho compacto (320px) e expandido (90vw, max 768px)
- **isPlaying**: Sincronizado com estado do player do YouTube
- **isClosed**: Usuário fechou manualmente (reseta quando player principal volta)

## Comportamento

1. **Aparição Automática**: Quando o player principal sai de vista (isMainPlayerVisible = false)
2. **Delay de Animação**: 100ms para transição suave
3. **Fechamento Manual**: Usuário pode fechar clicando no X
4. **Reset ao Voltar**: Quando player principal volta a ficar visível, mini player reseta

## Estilização

O componente usa as classes Tailwind do projeto TMC:

- Background: `bg-white`
- Border: `border-2 border-light-gray`
- Header: `bg-dark-green text-white`
- Shadow: `shadow-2xl`
- Z-index: `z-50`

## Acessibilidade

- Role: `complementary`
- Aria-label em todos os botões
- Títulos com atalhos de teclado
- Suporte a navegação por teclado
- Estados visuais claros (hover, focus)

## Notas de Implementação

1. **YouTube IFrame API**: O componente carrega automaticamente a API do YouTube se não estiver disponível
2. **Cleanup**: Destroi o player do YouTube quando desmontado
3. **Performance**: Usa useCallback para callbacks memorizados
4. **Responsividade**: Tamanho expandido ajusta-se ao viewport (90vw)

## Integração com TranscricaoPage

Para integrar na página de transcrição existente:

```jsx
// No TranscricaoPage.jsx
import { MiniPlayer } from './components';

// Adicionar estados
const [isMainPlayerVisible, setIsMainPlayerVisible] = useState(true);
const mainPlayerRef = useRef(null);

// Adicionar observer
useEffect(() => {
  if (!mainPlayerRef.current || currentStep !== 3) return;

  const observer = new IntersectionObserver(
    ([entry]) => setIsMainPlayerVisible(entry.isIntersecting),
    { threshold: 0.5 }
  );

  observer.observe(mainPlayerRef.current);
  return () => observer.disconnect();
}, [currentStep]);

// No JSX, adicionar ref ao player principal
<div ref={mainPlayerRef} className="bg-black rounded-xl overflow-hidden mb-4 aspect-video">
  {/* iframe aqui */}
</div>

// Adicionar MiniPlayer antes do </main>
{currentStep === 3 && videoData && (
  <MiniPlayer
    videoId={videoData.videoId}
    isMainPlayerVisible={isMainPlayerVisible}
  />
)}
```

## Troubleshooting

### MiniPlayer não aparece
- Verificar se `isMainPlayerVisible` está sendo atualizado corretamente
- Verificar se `videoId` é válido
- Verificar console para erros do YouTube API

### Player não carrega vídeo
- Verificar se o vídeo existe e é público
- Verificar network tab para erros de CORS
- Verificar se YouTube API foi carregada

### Sincronização não funciona
- Verificar se `onTimeUpdate` está sendo chamado
- Verificar se `currentTime` está sendo passado corretamente
- Verificar se player principal tem acesso ao método `getCurrentTime()`

## Melhorias Futuras

Possíveis melhorias para versões futuras:

- [ ] Controle de volume no mini player
- [ ] Barra de progresso customizada
- [ ] Drag & drop para reposicionar
- [ ] Persistir posição e estado no localStorage
- [ ] Picture-in-Picture nativo do navegador
- [ ] Modo "sempre visível" (pin)
- [ ] Thumbnails na timeline
