# Guia de Integração - TooltipEducativo

Este guia mostra como integrar o componente `TooltipEducativo` nas páginas do fluxo de criação de matéria.

---

## 1. ConfigurarPage.jsx (ETAPA 3)

Esta é a página principal onde o TooltipEducativo será mais usado.

### Estrutura Básica

```jsx
import { TooltipEducativo } from '@/components/criar';

function ConfigurarPage() {
  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Coluna 1: Configurações da Matéria */}
        <div className="space-y-6">
          <section className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-lg font-bold mb-4">Informações do Texto-Base</h2>

            {/* Campo: Data de Publicação */}
            <ConfigField
              label="Data de Publicação"
              icon="📅"
              tooltipTitle="Data de Publicação"
              tooltipContent={
                <>
                  <p>
                    Quando o conteúdo original foi publicado ou quando o evento
                    aconteceu. Isso ajuda a IA a contextualizar temporalmente e
                    usar verbos no tempo correto.
                  </p>
                  <p>
                    <strong>Exemplo:</strong> Se o texto-base é de ontem, a IA
                    saberá que deve usar "anunciou ontem" em vez de "anuncia hoje".
                  </p>
                </>
              }
            >
              <input
                type="date"
                className="w-full p-3 border border-light-gray rounded-lg"
              />
            </ConfigField>

            {/* Campo: Orientação do Lide */}
            <ConfigField
              label="Orientação do Lide"
              icon="📝"
              tooltipTitle="Orientação sobre o Lide"
              tooltipContent={
                <>
                  <p>
                    O lide é o primeiro parágrafo da matéria - deve responder às
                    perguntas: <strong>O quê? Quem? Quando? Onde? Por quê? Como?</strong>
                  </p>
                  <p>Indique qual ângulo você quer destacar:</p>
                  <ul>
                    <li>"Focar no impacto econômico para o cidadão"</li>
                    <li>"Destacar a reação do mercado financeiro"</li>
                    <li>"Priorizar as declarações do ministro"</li>
                  </ul>
                </>
              }
            >
              <textarea
                className="w-full p-3 border border-light-gray rounded-lg"
                placeholder="Ex: Focar no impacto econômico..."
                rows={3}
              />
            </ConfigField>

            {/* Campo: Citações de Fontes */}
            <ConfigField
              label="Citações de Fontes"
              icon="💬"
              tooltipTitle="Declarações de Fontes"
              tooltipContent={
                <>
                  <p>
                    Citações diretas de especialistas, autoridades ou envolvidos
                    dão credibilidade e humanizam a matéria.
                  </p>
                  <p><strong>Formato sugerido:</strong></p>
                  <code>Nome, cargo/função: 'Declaração entre aspas simples'</code>
                  <p><strong>Exemplo:</strong></p>
                  <p>
                    "João Silva, economista da FGV: 'As medidas terão efeito
                    positivo em até 6 meses'"
                  </p>
                </>
              }
            >
              <textarea
                className="w-full p-3 border border-light-gray rounded-lg"
                placeholder="Adicione citações diretas..."
                rows={4}
              />
            </ConfigField>

            {/* Campo: Contexto Adicional */}
            <ConfigField
              label="Contexto Adicional"
              icon="ℹ️"
              tooltipTitle="Contexto Adicional"
              tooltipContent={
                <>
                  <p>
                    Informações de background que a IA deve considerar mas que
                    não estão no texto-base:
                  </p>
                  <ul>
                    <li>
                      <strong>Histórico do tema:</strong> "Essa é a terceira tentativa..."
                    </li>
                    <li>
                      <strong>Nuances políticas:</strong> "O partido X é contra..."
                    </li>
                    <li>
                      <strong>Dados complementares:</strong> "Segundo o IBGE..."
                    </li>
                    <li>
                      <strong>Conexões com outros fatos:</strong> "Isso se relaciona com..."
                    </li>
                  </ul>
                </>
              }
            >
              <textarea
                className="w-full p-3 border border-light-gray rounded-lg"
                placeholder="Adicione contexto que não está no texto-base..."
                rows={4}
              />
            </ConfigField>
          </section>

          <section className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-lg font-bold mb-4">Configuração de Escrita</h2>

            {/* Campo: Créditos */}
            <ConfigField
              label="Créditos a Instituições"
              icon="🏛️"
              tooltipTitle="Créditos a Instituições"
              tooltipContent={
                <>
                  <p>Alguns conteúdos exigem atribuição obrigatória:</p>
                  <ul>
                    <li>Material de agências (Agência Brasil, Reuters, AFP)</li>
                    <li>Conteúdo de assessorias de imprensa</li>
                    <li>Dados de institutos de pesquisa</li>
                  </ul>
                  <p>Se marcado, a atribuição aparecerá no final da matéria.</p>
                </>
              }
            >
              <div className="space-y-2">
                <label className="flex items-center gap-2">
                  <input type="radio" name="creditos" value="nao" defaultChecked />
                  <span>Não precisa</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="radio" name="creditos" value="sim" />
                  <span>Sim</span>
                  <select className="ml-2 p-2 border rounded">
                    <option>Agência Brasil</option>
                    <option>Reuters</option>
                    <option>AFP</option>
                  </select>
                </label>
              </div>
            </ConfigField>

            {/* Campo: Persona */}
            <ConfigField
              label="Persona"
              icon="👤"
              tooltipTitle="Persona da Matéria"
              tooltipContent={
                <>
                  <p>Define a "voz" e abordagem do texto:</p>
                  <ul>
                    <li>
                      <strong>Jornalista Imparcial:</strong> Objetivo, factual, sem opinião
                    </li>
                    <li>
                      <strong>Especialista:</strong> Análise técnica aprofundada
                    </li>
                    <li>
                      <strong>Colunista:</strong> Pode incluir opinião fundamentada
                    </li>
                    <li>
                      <strong>Influencer:</strong> Linguagem próxima e engajadora
                    </li>
                  </ul>
                  <p>
                    Para hard news, prefira "Jornalista Imparcial". Para análises,
                    "Especialista" ou "Colunista".
                  </p>
                </>
              }
            >
              <div className="space-y-2">
                <label className="flex items-center gap-2">
                  <input type="radio" name="persona" value="jornalista" defaultChecked />
                  <span>Jornalista Imparcial</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="radio" name="persona" value="especialista" />
                  <span>Especialista</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="radio" name="persona" value="colunista" />
                  <span>Colunista</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="radio" name="persona" value="influencer" />
                  <span>Influencer</span>
                </label>
              </div>
            </ConfigField>

            {/* Campo: Tom */}
            <ConfigField
              label="Tom"
              icon="🎭"
              tooltipTitle="Tom da Escrita"
              tooltipContent={
                <>
                  <p>O tom afeta a escolha de palavras e construção das frases:</p>
                  <ul>
                    <li><strong>Formal:</strong> Linguagem séria, vocabulário culto</li>
                    <li><strong>Informal:</strong> Mais leve, próximo do leitor</li>
                    <li><strong>Técnico:</strong> Termos especializados, para público expert</li>
                    <li><strong>Persuasivo:</strong> Argumentativo, para editoriais</li>
                    <li><strong>Neutro:</strong> Equilibrado, sem emoção</li>
                  </ul>
                  <p>
                    Para notícias do dia, <strong>"Formal"</strong> ou{' '}
                    <strong>"Neutro"</strong> funcionam melhor.
                  </p>
                </>
              }
            >
              <select className="w-full p-3 border border-light-gray rounded-lg">
                <option>Formal</option>
                <option>Informal</option>
                <option>Técnico</option>
                <option>Persuasivo</option>
                <option>Neutro</option>
              </select>
            </ConfigField>

            {/* Campo: Instruções para IA */}
            <ConfigField
              label="Instruções para IA"
              icon="✍️"
              tooltipTitle="Instruções Adicionais"
              tooltipContent={
                <>
                  <p>Comandos específicos para a IA seguir:</p>
                  <p><strong>Exemplos úteis:</strong></p>
                  <ul>
                    <li>"Evitar termos muito técnicos"</li>
                    <li>"Explicar siglas na primeira menção"</li>
                    <li>"Manter parágrafos curtos (3-4 linhas)"</li>
                    <li>"Incluir dados numéricos quando disponíveis"</li>
                    <li>"Não usar adjetivos valorativos"</li>
                  </ul>
                </>
              }
            >
              <textarea
                className="w-full p-3 border border-light-gray rounded-lg"
                placeholder="Ex: Evitar termos muito técnicos..."
                rows={3}
              />
            </ConfigField>
          </section>
        </div>

        {/* Coluna 2: Materiais Complementares */}
        <div className="space-y-6">
          <section className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-lg font-bold mb-4">Materiais Complementares</h2>
            <p className="text-sm text-medium-gray mb-4">
              Adicione fontes extras para enriquecer a matéria
            </p>

            {/* Material: Link da Web */}
            <MaterialSection
              icon="🔗"
              title="Link da Web"
              tooltipTitle="Link Complementar (WEB)"
              tooltipContent={
                <>
                  <p>
                    Adicione links de páginas que complementam a matéria. O
                    conteúdo será extraído automaticamente.
                  </p>
                  <p><strong>Útil para:</strong></p>
                  <ul>
                    <li>Matérias relacionadas de outros veículos</li>
                    <li>Páginas oficiais com dados adicionais</li>
                    <li>Comunicados de imprensa</li>
                  </ul>
                  <p>Você poderá revisar e selecionar o que usar.</p>
                </>
              }
            />

            {/* Material: Vídeo YouTube */}
            <MaterialSection
              icon="▶️"
              title="Vídeo YouTube"
              tooltipTitle="Vídeo do YouTube"
              tooltipContent={
                <>
                  <p>
                    Adicione um vídeo complementar ao texto-base. A transcrição
                    será extraída automaticamente.
                  </p>
                  <p><strong>Útil para:</strong></p>
                  <ul>
                    <li>Entrevistas relacionadas ao tema</li>
                    <li>Coletivas de imprensa</li>
                    <li>Pronunciamentos oficiais</li>
                  </ul>
                  <p>Você poderá revisar e selecionar trechos específicos.</p>
                </>
              }
            />

            {/* Material: Arquivo PDF */}
            <MaterialSection
              icon="📎"
              title="Arquivo PDF"
              tooltipTitle="Arquivo PDF"
              tooltipContent={
                <>
                  <p>
                    Anexe documentos PDF como fonte adicional. O texto será
                    extraído para referência.
                  </p>
                  <p><strong>Útil para:</strong></p>
                  <ul>
                    <li>Relatórios oficiais e estudos</li>
                    <li>Documentos de governo</li>
                    <li>Papers e pesquisas acadêmicas</li>
                    <li>Notas técnicas e comunicados</li>
                  </ul>
                  <p>Máximo: 50 páginas ou 10MB por arquivo.</p>
                </>
              }
            />
          </section>
        </div>
      </div>
    </div>
  );
}
```

---

## 2. Componente ConfigField (Helper)

Crie um componente helper para encapsular a lógica comum de campo + tooltip:

```jsx
// src/components/criar/ConfigField.jsx
import { TooltipEducativo } from './';

function ConfigField({
  label,
  icon,
  tooltipTitle,
  tooltipContent,
  required = false,
  children
}) {
  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-2">
        <label className="text-sm font-semibold text-dark-gray">
          {label}
          {required && <span className="text-error ml-1">*</span>}
        </label>
        <TooltipEducativo
          title={tooltipTitle}
          icon={icon}
          position="auto"
        >
          {tooltipContent}
        </TooltipEducativo>
      </div>
      {children}
    </div>
  );
}

export default ConfigField;
```

---

## 3. Componente MaterialSection (Helper)

Para a seção de materiais complementares:

```jsx
// src/components/criar/MaterialSection.jsx
import { TooltipEducativo } from './';

function MaterialSection({ icon, title, tooltipTitle, tooltipContent }) {
  return (
    <div className="mb-6 p-4 border border-light-gray rounded-lg">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{icon}</span>
          <h3 className="font-semibold text-dark-gray">{title}</h3>
          <TooltipEducativo
            title={tooltipTitle}
            icon={icon}
            position="auto"
          >
            {tooltipContent}
          </TooltipEducativo>
        </div>
      </div>
      <button className="w-full p-3 border-2 border-dashed border-light-gray rounded-lg text-medium-gray hover:border-tmc-orange hover:text-tmc-orange transition-colors">
        + Adicionar {title.toLowerCase()}
      </button>
    </div>
  );
}

export default MaterialSection;
```

---

## 4. Exportar Helpers

Atualize o `index.js`:

```javascript
export { default as TooltipEducativo } from './TooltipEducativo';
export { default as ConfigField } from './ConfigField';
export { default as MaterialSection } from './MaterialSection';
```

---

## 5. Uso Completo na Página

```jsx
// src/pages/criar/ConfigurarPage.jsx
import { useState } from 'react';
import { ConfigField, MaterialSection } from '@/components/criar';

function ConfigurarPage() {
  const [formData, setFormData] = useState({
    dataPublicacao: '',
    orientacaoLide: '',
    citacoes: '',
    contexto: '',
    creditos: 'nao',
    agencia: '',
    persona: 'jornalista',
    tom: 'formal',
    instrucoes: ''
  });

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Configurar Matéria</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Coluna 1: Configurações */}
        <div className="space-y-6">
          {/* ... campos usando ConfigField ... */}
        </div>

        {/* Coluna 2: Materiais */}
        <div className="space-y-6">
          {/* ... seções usando MaterialSection ... */}
        </div>
      </div>

      {/* Botões de ação */}
      <div className="flex justify-between mt-8">
        <button className="px-6 py-3 border border-light-gray rounded-lg">
          ← Voltar
        </button>
        <button className="px-6 py-3 bg-tmc-orange text-white rounded-lg">
          Revisar e Gerar →
        </button>
      </div>
    </div>
  );
}

export default ConfigurarPage;
```

---

## 6. Responsividade

O TooltipEducativo já é responsivo por padrão:

```javascript
// Mobile detection (< 768px)
const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;

// Em mobile, sempre usa position='bottom'
const finalPosition = isMobile ? 'bottom' : currentPosition;
```

Para melhorar ainda mais:

```jsx
// Ajustar layout em mobile
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
  {/* Em mobile: 1 coluna */}
  {/* Em desktop: 2 colunas */}
</div>
```

---

## 7. Testes de Integração

```jsx
// ConfigurarPage.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import ConfigurarPage from './ConfigurarPage';

test('deve exibir tooltip ao clicar em ajuda', async () => {
  render(<ConfigurarPage />);

  const helpButton = screen.getByLabelText('Ajuda: Data de Publicação');
  fireEvent.click(helpButton);

  expect(screen.getByText(/Quando o conteúdo original/i)).toBeInTheDocument();
});
```

---

## 8. Checklist de Integração

- [ ] Importar `TooltipEducativo` em ConfigurarPage
- [ ] Criar componente `ConfigField`
- [ ] Criar componente `MaterialSection`
- [ ] Adicionar tooltip em todos os campos (11 total)
- [ ] Testar em mobile (<768px)
- [ ] Testar navegação por teclado
- [ ] Verificar acessibilidade (screen reader)
- [ ] Validar design com o planejamento
- [ ] Executar testes automatizados
- [ ] Deploy em staging para testes

---

## Conclusão

Com esses componentes helper (`ConfigField` e `MaterialSection`), a integração do `TooltipEducativo` fica limpa e reutilizável em toda a aplicação. Cada campo de configuração terá sua ajuda contextual, melhorando significativamente a experiência do usuário.
