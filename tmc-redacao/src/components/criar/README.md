# Componentes de Criação de Matéria

Este diretório contém os componentes reutilizáveis do novo fluxo unificado de criação de matéria.

## TooltipEducativo

Componente de tooltip educativo para orientar o usuário durante o fluxo de criação de matéria. Exibe ajuda contextual sobre campos e funcionalidades.

### Características

- **Posicionamento Inteligente**: Calcula automaticamente a melhor posição para não sair da tela
- **Responsivo**: Em mobile, sempre aparece embaixo do elemento
- **Acessível**: Totalmente navegável por teclado, compatível com WCAG 2.1
- **Animado**: Fade-in suave de 200ms
- **Flexível**: Aceita conteúdo JSX (parágrafos, listas, código, etc.)

### Props

| Prop | Tipo | Padrão | Descrição |
|------|------|--------|-----------|
| `title` | `string` | **obrigatório** | Título do tooltip |
| `icon` | `string` | - | Emoji ou texto para exibir ao lado do título |
| `children` | `node` | **obrigatório** | Conteúdo do tooltip (pode ser JSX) |
| `position` | `'right' \| 'left' \| 'top' \| 'bottom' \| 'auto'` | `'right'` | Posição preferencial do tooltip. `'auto'` calcula automaticamente |
| `className` | `string` | `''` | Classes CSS adicionais para o container |

### Uso Básico

```jsx
import TooltipEducativo from '@/components/criar/TooltipEducativo';

function MeuFormulario() {
  return (
    <div className="flex items-center gap-2">
      <label>Orientação do Lide</label>
      <TooltipEducativo
        title="Orientação sobre o Lide"
        icon="📝"
        position="right"
      >
        <p>O lide é o primeiro parágrafo da matéria...</p>
        <ul>
          <li>"Focar no impacto econômico"</li>
          <li>"Destacar a reação do mercado"</li>
        </ul>
      </TooltipEducativo>
    </div>
  );
}
```

### Exemplos Avançados

#### Com conteúdo rico

```jsx
<TooltipEducativo
  title="Declarações de Fontes"
  icon="💬"
  position="auto"
>
  <p>
    Citações diretas de especialistas, autoridades ou envolvidos dão
    credibilidade e humanizam a matéria.
  </p>
  <p><strong>Formato sugerido:</strong></p>
  <code>Nome, cargo/função: 'Declaração entre aspas simples'</code>
  <p><strong>Exemplo:</strong></p>
  <p>
    "João Silva, economista da FGV: 'As medidas terão efeito positivo
    em até 6 meses'"
  </p>
</TooltipEducativo>
```

#### Posicionamento automático

```jsx
<TooltipEducativo
  title="Contexto Adicional"
  icon="ℹ️"
  position="auto" // Calcula a melhor posição automaticamente
>
  <p>Informações de background que a IA deve considerar...</p>
</TooltipEducativo>
```

### Acessibilidade

O componente foi desenvolvido seguindo as diretrizes WCAG 2.1:

- **2.1.1 - Keyboard**: Totalmente navegável por teclado
  - `Tab` para navegar até o botão
  - `Enter` ou `Space` para abrir/fechar
  - `Escape` para fechar

- **2.1.2 - No Keyboard Trap**: O foco retorna ao botão após fechar

- **4.1.2 - Name, Role, Value**:
  - Aria labels descritivos
  - Role `dialog` para o tooltip
  - `aria-expanded` e `aria-haspopup` no botão

- **2.4.3 - Focus Order**: Foco é gerenciado corretamente

- **Área de toque**: Botão tem área mínima de 44x44px (WCAG 2.5.5)

### Comportamento

1. **Abrir**: Clicar no ícone de ajuda (?)
2. **Fechar**:
   - Clicar no X
   - Clicar fora do tooltip
   - Pressionar `Escape`
3. **Posicionamento**:
   - Desktop: Conforme prop `position` ou calculado se `auto`
   - Mobile (<768px): Sempre embaixo do elemento
4. **Animação**: Fade-in de 200ms ao abrir

### Estilo e Design

- **Largura**: 320px (80 em rem), máximo 90vw em mobile
- **Fundo**: Branco com borda cinza clara
- **Sombra**: `shadow-xl` do Tailwind
- **Tipografia**:
  - Título: Maiúsculas, negrito, cinza escuro
  - Conteúdo: Texto regular, cinza médio
  - Listas: Estilo disc, espaçamento adequado
- **Z-index**: 50 (para aparecer sobre outros elementos)

### Integração com Design System

O componente utiliza as cores do design system TMC:

- `tmc-orange`: Cor de destaque no hover
- `dark-gray`: Texto principal
- `medium-gray`: Texto secundário e ícones
- `light-gray`: Bordas
- `off-white`: Fundo do botão no hover

### Casos de Uso (conforme planejamento)

Conforme especificado em `Planning/UI-UX-REWORK-CRIAR-MATERIA.md`, o componente é usado para:

1. **Data de Publicação** - Explicar importância do contexto temporal
2. **Orientação do Lide** - Ensinar sobre o primeiro parágrafo
3. **Declarações de Fontes** - Orientar formato de citações
4. **Contexto Adicional** - Explicar informações de background
5. **Créditos** - Esclarecer quando é obrigatório
6. **Persona** - Definir tipos de "voz" do texto
7. **Tom** - Explicar impacto na escolha de palavras
8. **Instruções para IA** - Dar exemplos de comandos úteis
9. **Materiais Complementares** - Orientar sobre fontes extras

### Testes

Para testar o componente, use o arquivo de exemplo:

```bash
# Importar o exemplo na sua página de teste
import TooltipEducativoExamples from '@/components/criar/TooltipEducativo.example';
```

### Notas de Implementação

- Usa `lucide-react` para ícones (`HelpCircle`, `X`)
- Animação CSS inline (não requer configuração adicional)
- Estilos prose embutidos para formatação de conteúdo
- Detecta viewport mobile com `window.innerWidth < 768`
- Calcula posição usando `getBoundingClientRect()`

### Roadmap Futuro

- [ ] Adicionar opção de "não mostrar novamente" (localStorage)
- [ ] Suporte a temas (claro/escuro)
- [ ] Animações de entrada/saída mais elaboradas
- [ ] Suporte a ícones personalizados (não só emoji)
- [ ] Lazy loading do conteúdo para tooltips grandes
