---
phase: 03-text-quality
plan: A
type: execute
wave: 1
depends_on: []
files_modified:
  - FeedRSS/tmc-rss-collector/services/llm_service.py
  - FeedRSS/tmc-rss-collector/services/config.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Generated articles contain <15% 4-gram overlap with their source text"
    - "Generated articles contain zero competitor brand names from COMPETITOR_BRANDS list"
    - "The system prompt includes clear anti-copy examples (ANTI_COPIA constant)"
    - "Haiku extracts structured facts from source before Sonnet generation prompt is built"
  artifacts:
    - path: "FeedRSS/tmc-rss-collector/services/llm_service.py"
      provides: "ANTI_COPIA constant, _extract_facts_with_haiku() method, updated get_system_prompt() and _build_category_prompt(), updated build_user_prompt(), check_originality() function"
    - path: "FeedRSS/tmc-rss-collector/services/config.py"
      provides: "competitor_brands field in AppConfig, COMPETITOR_BRANDS env var loading"
  key_links:
    - from: "AppConfig.competitor_brands"
      to: "get_system_prompt() / _build_category_prompt()"
      via: "get_config().competitor_brands injected into system prompt"
      pattern: "competitor_brands"
    - from: "_extract_facts_with_haiku()"
      to: "generate_article()"
      via: "awaited before build_user_prompt() is called; returned extracted_facts passed to prompt"
      pattern: "_extract_facts_with_haiku"
    - from: "ANTI_COPIA constant"
      to: "_build_category_prompt() return value"
      via: "interpolated into f-string at end of category prompt"
      pattern: "ANTI_COPIA"
---

<objective>
Fix the root cause of verbatim text copying in article generation and add competitor brand filtering.

Purpose: Generated articles currently copy source text verbatim because raw `texto_base` is injected directly into the user prompt. Three surgical changes fix this: (1) Haiku extracts only factual claims from source before generation, (2) competitor brand list is injected into system prompt + post-generation scan, (3) ANTI_COPIA few-shot examples teach the model exactly how NOT to copy.

Output: Updated llm_service.py and config.py. No new files created. No existing tests broken.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/03-text-quality/03-CONTEXT.md
@docs/plans/2026-04-01-p0-implementation-plan.md

CRITICAL CONSTRAINTS:
- llm_service.py is ~117KB — NEVER rewrite wholesale. Use Edit tool for surgical changes only.
- config.py is ~9KB — safe to edit normally.
- All prompt text must be in Portuguese (the LLM speaks to Brazilian journalists).
- COMPETITOR_BRANDS must default to empty list when env var not set (no filtering if editorial hasn't configured it).
- The _extract_facts_with_haiku() method lives on the LLMService class and calls self._call_api() with model="claude-haiku-4-5".

<interfaces>
From services/llm_service.py (current state — key signatures):

```python
# Line 143-196: Prompt constants (FIDELIDADE_FACTUAL, FIDELIDADE_CURTA, FIDELIDADE_MEDIA,
#                                   ANTI_FABRICACAO_UNIVERSAL, ANTI_FABRICACAO_PADROES)
# Pattern: SCREAMING_SNAKE_CASE multiline strings

# Line 1387-1419: get_system_prompt() — PUBLIC function (called from generate_article)
def get_system_prompt(
    persona: str = "imparcial",
    tom: str = "formal",
    tipo_materia: str = "destaque",
    categoria: str = None,
    modo_opinativo: bool = False,
    source_len: int = 0,
    has_enrichment: bool = False,
    verified_chars: int = 0
) -> str:

# Line 1508-1609: _build_category_prompt() — called by get_system_prompt when categoria provided
def _build_category_prompt(
    categoria: str, tom: str, tipo_materia: str, modo_opinativo: bool,
    source_len: int = 0, has_enrichment: bool = False, verified_chars: int = 0
) -> str:
    # Returns f-string ending at line 1609 with {EEAT_ENFORCEMENT}{LEGIBILIDADE_ALVO}...

# Line 1680-1769: build_user_prompt() — PUBLIC function
def build_user_prompt(texto_base: str, ...) -> str:
    # Line 1718: prompt_parts.append(f"""<source-text>\n{texto_base}\n</source-text>...""")
    # This is where raw texto_base is injected — extraction must happen BEFORE this function is called

# Line 2189-2268: generate_article() async method on LLMService class
async def generate_article(self, texto_base: str, ...) -> dict:
    system_prompt = get_system_prompt(...)
    user_prompt = build_user_prompt(texto_base=texto_base, ...)
    # Extraction step goes between these two calls

# Line 1954: _call_api() on LLMService
async def _call_api(self, system: str, user_content: str, max_tokens: int = MAX_TOKENS,
                    correlation_id: str = "", model: str = "", task_type: str = "",
                    cache_system: bool = False) -> str:
```

From services/config.py (current state):
```python
# Line 15-97: AppConfig frozen dataclass
# Line 78: cors_allowed_origins: str = "" — pattern for new string fields
# Line 117-247: load_config() function with all env var loading
# Line 254: get_config() singleton accessor
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task A-1: Add COMPETITOR_BRANDS to config.py and ANTI_COPIA constant to llm_service.py</name>
  <files>
    FeedRSS/tmc-rss-collector/services/config.py
    FeedRSS/tmc-rss-collector/services/llm_service.py
  </files>
  <read_first>
    - FeedRSS/tmc-rss-collector/services/config.py (full file — it is 9KB, safe to read entirely)
    - FeedRSS/tmc-rss-collector/services/llm_service.py lines 140-210 (prompt constants section)
    - FeedRSS/tmc-rss-collector/services/llm_service.py lines 1387-1420 (get_system_prompt signature)
    - FeedRSS/tmc-rss-collector/services/llm_service.py lines 1598-1612 (_build_category_prompt return f-string)
  </read_first>
  <action>
    ## Step 1: config.py — Add competitor_brands field

    In the AppConfig dataclass (after line 79, after `cors_allowed_origins`), add:
    ```python
    # Editorial competitor filtering (comma-separated brand names, set by editorial team)
    competitor_brands: str = ""
    ```

    In load_config() (after the `cors_allowed_origins=...` line), add:
    ```python
    competitor_brands=os.environ.get("COMPETITOR_BRANDS", ""),
    ```

    No validation needed — empty string means "no filtering". The config is frozen so accessing `get_config().competitor_brands` returns the string.

    ## Step 2: llm_service.py — Add ANTI_COPIA constant

    After the ANTI_FABRICACAO_PADROES constant (around line 197), insert the ANTI_COPIA constant.
    The constant must follow the same SCREAMING_SNAKE_CASE multiline string pattern as the existing constants.

    Insert this exact block:

    ```python
    ANTI_COPIA = """

    ## ANTI-COPIA (OBRIGATORIO - PRIORIDADE MAXIMA)
    NUNCA copie frases do material-fonte. Use as mesmas INFORMACOES mas com palavras completamente diferentes.
    REGRA ABSOLUTA: Nunca use mais de 3 palavras consecutivas do material-fonte, EXCETO nomes proprios e citacoes entre aspas.

    ### EXEMPLOS OBRIGATORIOS — LEIA ANTES DE ESCREVER:

    INACEITAVEL (copia verbatim):
    Fonte: "O governo federal anunciou nesta quarta-feira um pacote de medidas economicas para conter a inflacao."
    Gerado: "O governo federal anunciou nesta quarta-feira um pacote de medidas economicas para conter a inflacao."

    CORRETO (mesmos fatos, palavras proprias):
    Fonte: "O governo federal anunciou nesta quarta-feira um pacote de medidas economicas para conter a inflacao."
    Gerado: "A administracao Lula divulgou, na tarde de quarta, um conjunto de acoes visando frear o aumento de precos."

    INACEITAVEL (copia com pequena alteracao):
    Fonte: "A empresa registrou prejuizo de R$ 2,3 bilhoes no terceiro trimestre, impactada pela alta do dolar."
    Gerado: "A empresa registrou um prejuizo de R$ 2,3 bilhoes no terceiro trimestre, sendo impactada pela alta do dolar."

    CORRETO (reescrita genuina):
    Fonte: "A empresa registrou prejuizo de R$ 2,3 bilhoes no terceiro trimestre, impactada pela alta do dolar."
    Gerado: "No terceiro trimestre, o resultado da companhia foi negativo em R$ 2,3 bilhoes — reflexo da desvalorizacao cambial sobre os custos."
    """
    ```

    ## Step 3: llm_service.py — Inject ANTI_COPIA + competitor filter into prompts

    ### 3a. Update get_system_prompt() signature (line 1387) to accept competitor_brands:
    Add parameter `competitor_brands: str = ""` to the function signature. This is a module-level function, so also update its return statement in the legacy path (around line 1425-1438) to append ANTI_COPIA and optionally the competitor instruction.

    In the legacy path f-string (the `return f"""..."""` around line 1425), before the closing `"""`, append:
    ```python
    {ANTI_COPIA}
    {_build_competitor_instruction(competitor_brands)}
    ```

    ### 3b. Update _build_category_prompt() (line 1598) f-string return:
    After `{EEAT_ENFORCEMENT}{LEGIBILIDADE_ALVO}`, before the format rules section, inject:
    ```python
    {ANTI_COPIA}
    {_build_competitor_instruction(competitor_brands)}
    ```
    Also add `competitor_brands: str = ""` parameter to _build_category_prompt() signature.
    Propagate from get_system_prompt() to _build_category_prompt() call at line 1419.

    ### 3c. Add helper function _build_competitor_instruction() just above get_system_prompt():
    ```python
    def _build_competitor_instruction(competitor_brands: str) -> str:
        """Build competitor filtering instruction from comma-separated brand list."""
        if not competitor_brands or not competitor_brands.strip():
            return ""
        brands = [b.strip() for b in competitor_brands.split(",") if b.strip()]
        if not brands:
            return ""
        brand_list = ", ".join(brands)
        return f"""
    ## FILTRAGEM DE MARCAS CONCORRENTES (OBRIGATORIO)
    NAO mencione estes veiculos/marcas pelo nome: {brand_list}
    Em vez disso, use formulas neutras: "segundo apuracao", "de acordo com fontes", "conforme reportado", "segundo a imprensa".
    Exemplo INCORRETO: "Segundo o Globo, o presidente..."
    Exemplo CORRETO: "Segundo a imprensa, o presidente..."
    """
    ```

    ### 3d. Update generate_article() to pass competitor_brands from config:
    In generate_article() at line 2237, update the get_system_prompt() call to pass competitor_brands:
    ```python
    from services.config import get_config
    _competitor_brands = get_config().competitor_brands
    system_prompt = get_system_prompt(
        persona=persona,
        tom=tom,
        tipo_materia=tipo_materia,
        categoria=categoria,
        modo_opinativo=modo_opinativo,
        source_len=len(texto_base.strip()),
        has_enrichment=bool(enrichment_context),
        verified_chars=verified_chars,
        competitor_brands=_competitor_brands,
    )
    ```
    (Note: `from services.config import get_config` is likely already imported at the top of llm_service.py — check first, add only if missing.)
  </action>
  <verify>
    <automated>
      cd "FeedRSS/tmc-rss-collector" && python -c "
from services.config import load_config, AppConfig
import dataclasses
fields = {f.name for f in dataclasses.fields(AppConfig)}
assert 'competitor_brands' in fields, 'competitor_brands field missing from AppConfig'
print('config.py: competitor_brands field OK')

import os
os.environ['PRODUCTION_SAFETY_MODE'] = 'false'
os.environ['JWT_SECRET_KEY'] = 'dev-test-key-32-chars-minimum-here'
from services import config as cfg_module
cfg_module._config = None
c = cfg_module.load_config()
assert c.competitor_brands == '', 'default should be empty string'
print('config.py: default competitor_brands OK')

os.environ['COMPETITOR_BRANDS'] = 'Globo, UOL, Folha'
cfg_module._config = None
c2 = cfg_module.load_config()
assert c2.competitor_brands == 'Globo, UOL, Folha', f'got: {c2.competitor_brands}'
print('config.py: COMPETITOR_BRANDS env var loading OK')
"
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "competitor_brands" FeedRSS/tmc-rss-collector/services/config.py` returns at least 2 matches (field declaration + load_config assignment)
    - `grep -n "ANTI_COPIA" FeedRSS/tmc-rss-collector/services/llm_service.py` returns at least 3 matches (constant definition + 2 injection points in prompts)
    - `grep -n "_build_competitor_instruction" FeedRSS/tmc-rss-collector/services/llm_service.py` returns at least 3 matches (function definition + 2 call sites)
    - `grep -n "INACEITAVEL" FeedRSS/tmc-rss-collector/services/llm_service.py` returns exactly 2 matches (the two bad examples)
    - `grep -n "CORRETO" FeedRSS/tmc-rss-collector/services/llm_service.py` returns at least 2 matches (the two good examples) — note CORRETO may also appear elsewhere, 2+ is sufficient
    - Python import test passes without syntax errors: `cd FeedRSS/tmc-rss-collector && python -c "from services.llm_service import get_system_prompt, ANTI_COPIA; print('OK')"`
  </acceptance_criteria>
  <done>
    - AppConfig has competitor_brands: str = "" field
    - COMPETITOR_BRANDS env var loads into competitor_brands in load_config()
    - ANTI_COPIA constant defined after ANTI_FABRICACAO_PADROES in llm_service.py
    - _build_competitor_instruction() helper function exists above get_system_prompt()
    - Both get_system_prompt() and _build_category_prompt() inject ANTI_COPIA and competitor instruction into their returned system prompts
    - generate_article() passes get_config().competitor_brands to get_system_prompt()
  </done>
</task>

<task type="auto">
  <name>Task A-2: Add Haiku fact extraction step and post-generation competitor scan</name>
  <files>
    FeedRSS/tmc-rss-collector/services/llm_service.py
  </files>
  <read_first>
    - FeedRSS/tmc-rss-collector/services/llm_service.py lines 1680-1770 (build_user_prompt function body)
    - FeedRSS/tmc-rss-collector/services/llm_service.py lines 2189-2270 (generate_article method body)
    - FeedRSS/tmc-rss-collector/services/llm_service.py lines 1954-1990 (_call_api signature + Azure/Haiku routing)
  </read_first>
  <action>
    ## Step 1: Add _extract_facts_with_haiku() method to LLMService class

    In the LLMService class (find the class definition — it's the class that contains generate_article and _call_api), add the new async method. Insert it just before generate_article() at line 2189:

    ```python
    async def _extract_facts_with_haiku(
        self,
        texto_base: str,
        correlation_id: str = "",
    ) -> str:
        """
        Extract structured factual claims from source text using Claude Haiku.

        Pre-processes source text into a fact list to prevent verbatim copying
        in the generation step. Cost: ~$0.001/article (Haiku pricing).

        Args:
            texto_base: Raw source text to extract facts from
            correlation_id: For request tracing

        Returns:
            Extracted facts as a formatted string, or empty string on failure
        """
        if not texto_base or len(texto_base.strip()) < 100:
            return ""

        extraction_system = (
            "Voce e um extrator de fatos jornalisticos. "
            "Sua tarefa e listar APENAS fatos verificados de um texto. "
            "Responda SOMENTE com a lista de fatos, sem comentarios adicionais."
        )
        extraction_prompt = (
            f"Extraia APENAS fatos verificados, entidades, numeros, datas e citacoes diretas "
            f"do texto abaixo. NAO inclua frases completas do texto original. "
            f"NAO parafraseie — apenas liste os fatos como itens separados.\n\n"
            f"TEXTO:\n{texto_base[:3000]}\n\n"
            f"Liste 5 afirmacoes factuais neste texto (uma por linha, comecando com -):"
        )
        try:
            result = await self._call_api(
                system=extraction_system,
                user_content=extraction_prompt,
                max_tokens=512,
                correlation_id=correlation_id,
                model="claude-haiku-4-5",
                task_type="fact_extraction",
            )
            return result.strip() if result else ""
        except Exception as e:
            logger.warning(f"[{correlation_id}] Fact extraction with Haiku failed: {e}. Proceeding without extraction.")
            return ""
    ```

    ## Step 2: Add scan_competitor_mentions() module-level function

    After the `_build_competitor_instruction()` helper function (added in Task A-1), add:

    ```python
    def scan_competitor_mentions(text: str, competitor_brands: str) -> list:
        """
        Scan generated article for competitor brand mentions.

        Args:
            text: Generated article text
            competitor_brands: Comma-separated brand name list from COMPETITOR_BRANDS env var

        Returns:
            List of found brand name strings (empty list = clean)
        """
        import re
        if not competitor_brands or not competitor_brands.strip():
            return []
        brands = [b.strip() for b in competitor_brands.split(",") if b.strip()]
        found = []
        for brand in brands:
            # Case-insensitive word-boundary search
            pattern = r'\b' + re.escape(brand) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                found.append(brand)
        return found
    ```

    ## Step 3: Update build_user_prompt() to accept and use extracted_facts

    In build_user_prompt() at line 1680, add `extracted_facts: str = ""` to the function signature.

    After the existing `<source-text>` block injection (line 1718-1725), add a block that injects extracted facts when present:

    ```python
    # Inject extracted facts to guide generation away from verbatim copying (D-01 to D-05)
    if extracted_facts:
        prompt_parts.append(f"""<extracted-facts>
    FATOS VERIFICADOS EXTRAIDOS DO TEXTO-BASE (use estes como base, NAO o texto bruto):
    {extracted_facts}
    </extracted-facts>

    INSTRUCAO CRITICA: Escreva baseado APENAS nos fatos extraidos acima.
    NAO copie frases do material em <source-text>. O texto original e fornecido apenas como referencia contextual.""")
    ```

    ## Step 4: Update generate_article() to orchestrate the extraction step and scan

    In generate_article() at line 2189, after building system_prompt and before calling build_user_prompt():

    ```python
    # Step: Extract facts with Haiku to prevent verbatim copying (D-01 to D-05)
    extracted_facts = await self._extract_facts_with_haiku(
        texto_base=texto_base,
        correlation_id=correlation_id,
    )
    ```

    Then update the build_user_prompt() call to pass extracted_facts:
    ```python
    user_prompt = build_user_prompt(
        texto_base=texto_base,
        orientacao_lide=orientacao_lide,
        citacoes=citacoes,
        contexto=contexto,
        creditos=creditos,
        tags=tags,
        enrichment_context=enrichment_context,
        enrichment_key_facts=enrichment_key_facts,
        verified_chars=verified_chars,
        tipo_materia=tipo_materia,
        source_urls=source_urls,
        extracted_facts=extracted_facts,
    )
    ```

    After the LLM call returns (after line 2264), add competitor scan and audit logging.
    Find where `response_text` is assigned and add after successful JSON parse (look for where `result_dict` or the article dict is assembled):

    ```python
    # Post-generation competitor scan (D-13, D-14)
    _competitor_brands_cfg = get_config().competitor_brands
    if _competitor_brands_cfg:
        _found_competitors = scan_competitor_mentions(
            text=response_text,
            competitor_brands=_competitor_brands_cfg,
        )
        if _found_competitors:
            logger.warning(
                f"[{correlation_id}] Competitor mentions found in generated article: "
                f"{_found_competitors}. Article requires editorial review."
            )
            # Add to result dict for audit trail (generation_api.py will log to audit table)
            result_dict["competitor_mentions"] = _found_competitors
        else:
            result_dict["competitor_mentions"] = []
    ```

    IMPORTANT: Find the exact location where `result_dict` is created/returned in generate_article() before inserting this block. Do not add it in error-handling paths.
  </action>
  <verify>
    <automated>
      cd "FeedRSS/tmc-rss-collector" && python -c "
import ast
with open('services/llm_service.py', 'r', encoding='utf-8') as f:
    source = f.read()

# Check _extract_facts_with_haiku exists
assert '_extract_facts_with_haiku' in source, 'Missing _extract_facts_with_haiku method'
print('_extract_facts_with_haiku: OK')

# Check scan_competitor_mentions exists
assert 'scan_competitor_mentions' in source, 'Missing scan_competitor_mentions function'
print('scan_competitor_mentions: OK')

# Check extracted_facts parameter in build_user_prompt
assert 'extracted_facts' in source, 'Missing extracted_facts in build_user_prompt'
print('extracted_facts parameter: OK')

# Syntax check the whole file
try:
    ast.parse(source)
    print('Syntax check: PASSED')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')
    exit(1)
"
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "_extract_facts_with_haiku" FeedRSS/tmc-rss-collector/services/llm_service.py` returns at least 2 matches (definition + call in generate_article)
    - `grep -n "scan_competitor_mentions" FeedRSS/tmc-rss-collector/services/llm_service.py` returns at least 2 matches (definition + call in generate_article)
    - `grep -n "extracted_facts" FeedRSS/tmc-rss-collector/services/llm_service.py` returns at least 3 matches (parameter def + injection in build_user_prompt + call in generate_article)
    - `grep -n "fact_extraction" FeedRSS/tmc-rss-collector/services/llm_service.py` returns 1 match (task_type="fact_extraction" in _extract_facts_with_haiku)
    - `grep -n "competitor_mentions" FeedRSS/tmc-rss-collector/services/llm_service.py` returns at least 1 match (result_dict["competitor_mentions"])
    - Syntax check passes: `cd FeedRSS/tmc-rss-collector && python -m py_compile services/llm_service.py && echo OK`
    - scan_competitor_mentions unit test: `cd FeedRSS/tmc-rss-collector && python -c "from services.llm_service import scan_competitor_mentions; r = scan_competitor_mentions('Segundo o Globo, ontem', 'Globo, UOL'); assert r == ['Globo'], f'got {r}'; print('scan test OK')"`
  </acceptance_criteria>
  <done>
    - _extract_facts_with_haiku() async method exists on LLMService, calls _call_api with model="claude-haiku-4-5" and task_type="fact_extraction", returns str
    - scan_competitor_mentions() module-level function takes text + competitor_brands, returns list of found brand names
    - build_user_prompt() accepts extracted_facts: str = "" parameter and injects `<extracted-facts>` block when non-empty
    - generate_article() awaits _extract_facts_with_haiku before build_user_prompt and passes extracted_facts
    - generate_article() runs scan_competitor_mentions after generation and logs WARNING + adds competitor_mentions to result_dict
    - File passes Python syntax check (py_compile)
  </done>
</task>

<task type="auto">
  <name>Task A-3: Add check_originality() n-gram function to llm_service.py</name>
  <files>
    FeedRSS/tmc-rss-collector/services/llm_service.py
  </files>
  <read_first>
    - FeedRSS/tmc-rss-collector/services/llm_service.py lines 196-210 (after ANTI_FABRICACAO_PADROES, before any class definition)
    - FeedRSS/tmc-rss-collector/services/llm_service.py: search for `class LLMService` to find class start line
  </read_first>
  <action>
    ## Add check_originality() as a module-level function (NOT a class method)

    This is a pure function — no class needed, no API call. It will be imported by generation_api.py (Plan B).
    Insert AFTER scan_competitor_mentions() (added in Task A-2) and BEFORE the LLMService class definition.

    ```python
    def check_originality(
        generated: str,
        source: str,
        n: int = 4,
        threshold: float = 0.15,
    ) -> dict:
        """
        Compute n-gram overlap between generated article and source text.

        Pure Python implementation — no external dependencies. Word-level n-grams
        (not character-level) because copied phrases span word boundaries.
        Portuguese stop words are NOT removed — they are part of copied phrases.

        Args:
            generated: Generated article text
            source: Original source text (texto_base)
            n: N-gram size (default 4 — catches 4-word exact phrases)
            threshold: Overlap ratio above which text is flagged as "high_copy" (default 15%)

        Returns:
            dict with keys:
              overlap_ratio: float (0.0-1.0)
              is_copy: bool (True when overlap_ratio > threshold)
              overlapping_ngrams: int (count of shared n-grams)
              total_generated_ngrams: int
        """
        import string

        def _normalize(text: str) -> list:
            """Lowercase, remove punctuation, split into words."""
            # Remove punctuation (keeps accented chars intact)
            translator = str.maketrans("", "", string.punctuation)
            clean = text.lower().translate(translator)
            return clean.split()

        gen_words = _normalize(generated)
        src_words = _normalize(source)

        # Build n-gram sets
        def _ngrams(words: list, size: int) -> set:
            if len(words) < size:
                return set()
            return set(tuple(words[i:i+size]) for i in range(len(words) - size + 1))

        gen_ngrams = _ngrams(gen_words, n)
        src_ngrams = _ngrams(src_words, n)

        if not gen_ngrams:
            return {
                "overlap_ratio": 0.0,
                "is_copy": False,
                "overlapping_ngrams": 0,
                "total_generated_ngrams": 0,
            }

        overlap = gen_ngrams & src_ngrams
        ratio = len(overlap) / len(gen_ngrams)

        return {
            "overlap_ratio": ratio,
            "is_copy": ratio > threshold,
            "overlapping_ngrams": len(overlap),
            "total_generated_ngrams": len(gen_ngrams),
        }
    ```

    ## Ensure check_originality is importable from generation_api.py

    The function is module-level in llm_service.py. Plan B will import it as:
    `from services.llm_service import check_originality`

    No additional export declarations needed in Python.
  </action>
  <verify>
    <automated>
      cd "FeedRSS/tmc-rss-collector" && python -c "
from services.llm_service import check_originality

# Test 1: Identical text → high overlap
result = check_originality(
    'O governo federal anunciou nesta quarta um pacote de medidas economicas',
    'O governo federal anunciou nesta quarta um pacote de medidas economicas'
)
assert result['is_copy'] == True, f'Identical text should be flagged as copy: {result}'
assert result['overlap_ratio'] > 0.5, f'Identical text ratio should be >0.5: {result}'
print(f'Test 1 (identical): overlap_ratio={result[\"overlap_ratio\"]:.2f} OK')

# Test 2: Fully rewritten text → low overlap
result2 = check_originality(
    'A administracao federal divulgou na tarde de quarta um conjunto de acoes para frear os precos',
    'O governo federal anunciou nesta quarta um pacote de medidas economicas para conter a inflacao'
)
assert result2['is_copy'] == False, f'Rewritten text should not be flagged: {result2}'
print(f'Test 2 (rewritten): overlap_ratio={result2[\"overlap_ratio\"]:.2f} OK')

# Test 3: Short text returns clean result (no crash)
result3 = check_originality('curto', 'texto muito curto aqui', n=4)
assert result3['is_copy'] == False
print('Test 3 (short text): OK')

print('check_originality: ALL TESTS PASSED')
"
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "def check_originality" FeedRSS/tmc-rss-collector/services/llm_service.py` returns exactly 1 match
    - `grep -n "overlap_ratio" FeedRSS/tmc-rss-collector/services/llm_service.py` returns at least 3 matches (in function body + docstring)
    - Function is at module level (not inside a class): verify the def is not indented under `class LLMService`
    - Unit tests above pass (identical text flagged, rewritten text not flagged, no crash on short input)
    - Syntax check: `cd FeedRSS/tmc-rss-collector && python -m py_compile services/llm_service.py && echo OK`
  </acceptance_criteria>
  <done>
    - check_originality(generated, source, n=4, threshold=0.15) exists as module-level function in llm_service.py
    - Returns dict with overlap_ratio (float), is_copy (bool), overlapping_ngrams (int), total_generated_ngrams (int)
    - Identical text produces is_copy=True (>15% overlap)
    - Genuinely rewritten text produces is_copy=False
    - No external dependencies (pure Python string/set operations)
    - Importable from generation_api.py via `from services.llm_service import check_originality`
  </done>
</task>

</tasks>

<verification>
After all 3 tasks complete, verify the full Plan A by running:

```bash
cd "FeedRSS/tmc-rss-collector"

# 1. Syntax check both modified files
python -m py_compile services/llm_service.py && echo "llm_service.py: OK"
python -m py_compile services/config.py && echo "config.py: OK"

# 2. Import smoke test
python -c "
from services.llm_service import get_system_prompt, check_originality, scan_competitor_mentions, ANTI_COPIA
from services.config import AppConfig
import dataclasses
fields = {f.name for f in dataclasses.fields(AppConfig)}
assert 'competitor_brands' in fields
assert 'ANTI_COPIA' in ANTI_COPIA
assert 'INACEITAVEL' in ANTI_COPIA
print('Import smoke test: ALL OK')
"

# 3. check_originality functional test
python -c "
from services.llm_service import check_originality
r = check_originality(
    'O governo federal anunciou nesta quarta um pacote de medidas economicas',
    'O governo federal anunciou nesta quarta um pacote de medidas economicas'
)
assert r['is_copy'] == True
print('check_originality: OK')
"

# 4. scan_competitor_mentions functional test
python -c "
from services.llm_service import scan_competitor_mentions
r = scan_competitor_mentions('Segundo o Globo e a Folha de S.Paulo ontem', 'Globo, Folha de S.Paulo')
assert 'Globo' in r
print('scan_competitor_mentions: OK')
"

# 5. Competitor brands config test
python -c "
import os
os.environ['PRODUCTION_SAFETY_MODE'] = 'false'
os.environ['JWT_SECRET_KEY'] = 'dev-secret-32-chars-minimum-here!'
os.environ['COMPETITOR_BRANDS'] = 'Globo, UOL'
from services import config as c
c._config = None
cfg = c.load_config()
assert cfg.competitor_brands == 'Globo, UOL'
print('COMPETITOR_BRANDS config: OK')
"
```
</verification>

<success_criteria>
- All 3 tasks complete with zero Python syntax errors
- check_originality() correctly identifies >15% 4-gram overlap as is_copy=True
- scan_competitor_mentions() finds competitor names via regex (case-insensitive)
- ANTI_COPIA constant injected into both _build_category_prompt() and legacy get_system_prompt() return values
- COMPETITOR_BRANDS env var loads into AppConfig.competitor_brands and flows through to system prompt
- Haiku extraction step runs BEFORE build_user_prompt() in generate_article()
- Extracted facts injected into user prompt with instruction NOT to copy from source-text
- No existing tests broken (run pytest tests/ if tests exist for llm_service)
</success_criteria>

<output>
After completion, create `.planning/phases/03-text-quality/03-A-pipeline-quality-SUMMARY.md`

Include:
- What was changed (file:line ranges for each surgical edit)
- The exact constant/function signatures added
- Any deviations from the plan and why
- Verification results (paste the verification command outputs)
</output>
