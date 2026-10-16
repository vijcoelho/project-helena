# Inventario Helena 1.5.0 + Cockpit + restricoes (r4)

Legenda UI hoje: SL = statusline (`helena/statusline.js`), SITE = site/ (index, docs, registry.json), CMD = so slash command em texto, NENHUMA.
GUI? = ganho de uma interface grafica: ALTO / MEDIO / BAIXO.

## 1. Inventario de features (48)

### Memoria (10)
| # | Feature | UI hoje | GUI? |
|---|---|---|---|
| 1 | Destilacao automatica via Haiku (a cada 6 msgs e no fim da sessao), segredos mascarados | NENHUMA | MEDIO (ver o que foi aprendido, aprovar/rejeitar) |
| 2 | Notas Markdown em pasta/Obsidian (`~/Helena`), uma nota por fato | Obsidian (externo) | MEDIO (navegador de notas com stale/checks) |
| 3 | Indice de memorias no inicio da sessao (descricao <= 90 chars) | NENHUMA | BAIXO |
| 4 | Router: 2 notas mais parecidas com o pedido entregues inteiras a cada prompt | NENHUMA | ALTO (mostrar "o que a Helena injetou neste pedido") |
| 5 | Memoria auto-conferida: `checks:` (codigo) e `until:` (data) -> marca STALE | NENHUMA | ALTO (lista de notas STALE com motivo) |
| 6 | Supersede: fato novo manda a antiga pro Archive | NENHUMA | MEDIO |
| 7 | Faxina (tidy): junta duplicadas/contradicoes, Archive reversivel | NENHUMA | MEDIO (diff de merge) |
| 8 | `/helena:recall` busca de texto nas sessoes passadas (sem LLM) | CMD | ALTO (busca com preview) |
| 9 | `/helena:remember`, `/helena:forget`, `/helena:setup`, `/helena:status` | CMD | MEDIO |
| 10 | Memoria de time: `.helena/memory` no repo + `/helena:share` | CMD | MEDIO (revisar nota -> PR) |

### Guardrails (14)
| # | Feature | UI hoje | GUI? |
|---|---|---|---|
| 11 | Guarda de git (commit/push): chaves API, .env, `.helena/git` (`main: no`, `never:`), gitleaks opcional | NENHUMA (so mensagem de deny) | MEDIO (editor das regras) |
| 12 | Bloqueio de comandos destrutivos (DROP, rm -rf, force push, terraform destroy, base64/python -c) | NENHUMA | MEDIO |
| 13 | `.env` nunca lido: so nomes das chaves, anti-truques | NENHUMA | BAIXO |
| 14 | Pacotes inventados/novos (npm/PyPI existe? <72h? downloads?) | NENHUMA | BAIXO |
| 15 | Testes nao podem ser enfraquecidos (remover assert, skip, apagar teste -> ask) | NENHUMA | BAIXO |
| 16 | Prompt-injection em resultado de ferramenta: marca e registra (nao bloqueia) | NENHUMA | MEDIO |
| 17 | Scan da config do repo (CLAUDE.md, AGENTS.md, .mcp.json, settings) na abertura | NENHUMA | MEDIO |
| 18 | Auditoria `~/.helena/audit.jsonl` + egress `egress.jsonl`, anti-apagar; `/helena:audit` | CMD | ALTO (timeline filtravel de decisoes e saidas de rede) |
| 19 | Politica como codigo `.helena/policy` (deny/ask/mcp allowlist) | NENHUMA | MEDIO (editor visual de politica) |
| 20 | Rewind: snapshot git antes de cada pedido, `/helena:rewind [n]`, desfaz o desfazer | CMD | ALTO (linha do tempo de pedidos + diff + botao Voltar) |
| 21 | Red team 36/37 + falso-positivo zero (`eval/test_redteam.py`) | NENHUMA (CLI) | BAIXO |
| 22 | Hook replay sem LLM + `test_falseblock.py` (`eval/replay.py`) | NENHUMA (CLI) | MEDIO (diff de decisoes entre versoes) |
| 23 | Holdout: `.helena/holdout/` escondido do agente, so pass/fail | NENHUMA | BAIXO |
| 24 | `tests: spec-only` (ask antes de criar teste novo nao pedido) | NENHUMA | BAIXO |

### Verificacao (6)
| # | Feature | UI hoje | GUI? |
|---|---|---|---|
| 25 | Portao "pronto": roda testes (npm/pytest/cargo/go/`.helena/test`) ou `tsc --noEmit`; 1 devolucao (done.js) | NENHUMA | ALTO (status verde/vermelho por sessao/agente) |
| 26 | Mesmo portao em subagentes (SubagentStop) | NENHUMA | ALTO |
| 27 | Differential check: teste novo tem que falhar sem o codigo (stash) | NENHUMA | MEDIO |
| 28 | Contraste WCAG AA no front-end (Edge/Chrome headless, desktop+celular; `tools/contrast.mjs`, `shot.mjs`) | NENHUMA (texto) | ALTO (screenshots com falhas marcadas) |
| 29 | Handoff conferido contra o repo (arquivos mudados, commits desde, sumidos) | NENHUMA | MEDIO |
| 30 | Scan de seguranca de skills de terceiros (`scan.py`, `--trust`) | CMD/CLI | MEDIO |

### Economia de tokens (10)
| # | Feature | UI hoje | GUI? |
|---|---|---|---|
| 31 | Kits + biblioteca de skills (custo zero ate gatilho): -11,9k tokens/msg | SITE (registry) | MEDIO |
| 32 | Desligar plugins nao usados por projeto (e religar sob demanda) | NENHUMA | MEDIO |
| 33 | trim.js: comandos barulhentos viram silenciosos; bloqueia lock/build/>100KB | NENHUMA | BAIXO |
| 34 | Avisos de contexto 120k/250k/500k + sugestao HANDOFF+/clear | SL | MEDIO |
| 35 | Statusline: ctx, cache-until, limit%, modelo, aviso de troca de modelo sem cache | SL (unica UI viva) | ALTO (versao rica/grafica) |
| 36 | Subagentes na coleira: pin Sonnet/Haiku, nunca acima da sessao, caps `.helena/delegate` (3 simult., 8/pedido) | NENHUMA | MEDIO |
| 37 | Nota de refacao, aviso de CLAUDE.md pesado, resumo git na abertura, HANDOFF so com "Next" | NENHUMA | BAIXO |
| 38 | `/helena:budget`: para onde foram tokens, custo de subagentes, custo da Helena (`ledger.jsonl`) | CMD (+ `/painel`) | ALTO (graficos de custo) |
| 39 | `/painel`: contexto por categoria + gasto Helena | CMD | ALTO |
| 40 | Chamadas de fundo baratas (Haiku sem plugins, ~12k vs ~48k) | NENHUMA | BAIXO |

### Multi-IA (5)
| # | Feature | UI hoje | GUI? |
|---|---|---|---|
| 41 | `connect.py` (Codex via plugin; Gemini/Qwen/Kimi/Grok/opencode via MCP) | CLI | ALTO (tela "IAs conectadas" com toggle) |
| 42 | `mcp.js`: 7 ferramentas (start, context, skill, remember, limits, undo, recall), stdio sem deps | NENHUMA | BAIXO |
| 43 | Limites por plano (5h + semana) lidos do disco; `/helena:limits`; ritmo da semana ("acaba dia X") | CMD + SL (limit%) | ALTO (barras por IA, projecao) |
| 44 | Troca automatica 80%/95%: salva HANDOFF.md e entrega comando pra proxima IA | texto no chat | ALTO (botao "continuar no Codex") |
| 45 | Unificacao CLAUDE.md/AGENTS.md | NENHUMA | BAIXO |

### Orquestracao (4)
| # | Feature | UI hoje | GUI? |
|---|---|---|---|
| 46 | `/helena:orchestrate`: plano -> scout (Haiku) -> builder (Sonnet, um por vez) -> testes -> diff | CMD | ALTO (kanban/etapas, diff, custo por worker) |
| 47 | `/helena:race`: 2 builders em worktrees, vence quem passa teste | CMD | ALTO (lado a lado dos 2 diffs/testes) |
| 48 | Skills autocriados + "Aprendido" + `/helena:skills`, `/helena:undo`; rotinas (`routines.py`, ci/deps, teto US$0,10); notas de projeto e revisao semanal no cofre | CMD | ALTO (painel de skills com uso, rotinas e "precisa de voce") |

### Eval / prova (nao contado acima, 20 suites `eval/test_*.py`, `eval/run.py`, `registry.py`, `promote.py`)
UI: SITE (tabela de registro e placar sem/com). GUI? MEDIO (dashboard de benchmark local).

### Site / distribuicao
- `site/` estatico: `index.html`, `docs.html`, `registry.json`, `assets/img`, favicons. UI = SITE (marketing + registro). Distribuicao via plugin Claude Code (`/plugin`), `connect.py`, `skills/` em `helena/skills` (handoff, readability, library). GUI desktop nao existe; esta so como "Future" no roadmap.
- Pecas no repo: `helena/hooks` (check, delegate, done, end, gate, guard, limits, memory, outside, paths, rewind, router, start, trim + `hooks.json`, `mod.mjs`), `helena/commands` (15 md), `helena/agents` (builder, scout), `helena/tools`, `helena/mcp.js`, `helena/statusline.js`, py: audit, budget, connect, distill, history, routines, scan, skills, tidy, worker.

### Backlog "Later" (HANDOFF Next, nada construido)
Handoff em background a ~65% da janela; cache de resultado de tool entre sessoes; "dreaming" noturno; pacote `claude plugin eval helena`; benchmark publico.
Decisao relevante: item 24 do backlog X ("limits widget") foi **rejeitado** porque "statusline.js e /helena:limits cobrem; desktop foi deprioritizado". Ou seja, o usuario ja decidiu uma vez contra desktop. Roadmap (helena-roadmap.md) ainda lista "Desktop app tipo Hermes Agent" como Future.

## 2. Cockpit

- **Caminho real**: `C:\Users\vijc\dev\agent-project` (a pasta `C:\Users\vijc\dev\cockpit` existe so com `.git`; todos os 306 arquivos aparecem deletados no working tree, entao e um clone vazio. O projects.md aponta `dev/cockpit`, mas o codigo vivo esta em `agent-project`; ultimo commit 2026-09-16, `cockpit.json` modificado).
- **Stack**: web local, nao Electron nem Tauri. Frontend React 19 + TypeScript + Vite 8 + xterm.js + CodeMirror 6. Backend Node (Express 5, `ws`, `node-pty`, chokidar). Casca desktop: `app/Cockpit.exe` (C# WinForms + WebView2, `Cockpit.cs`, scripts `compilar/instalar/verificar.ps1`) que embute a UI. CLI `bin/cockpit.mjs`. Porta 3000, `cockpit.json` como painel de controle.
- **O que tem**: projetos/missoes, paineis com terminal PTY real (bash, claude, codex, agy, grok), papeis semanticos, squads, modos de coordenacao, Maestro (continuidade e auto-switch de conta), quadro de tarefas, arquivos + editor, memoria, conexoes/handoffs entre agentes, contas e cotas (codex-quota), politica de IA, skills/marketplace/receitas, media, voz, integracao DSH (DeepSeek Harness) e OpenRouter, seguranca (approval, audit, sanitizer, permissions), ~100 scripts `check-*` (testes). Mobile layout. README completo em PT-BR.
- **Estado**: v1.0, "release v1.0" commitada; docs do DSH e uso completo escritos. Funcional segundo os commits; ha `server-runtime-error.log` e `PLANO-REDESIGN-UI.md` pendente (redesign de UI planejado). Princípio dele: sem API key, usa os CLIs logados (alinha com sem-api-key).
- **Reaproveitavel para desktop app/ADE da Helena**:
  - Casca `app/Cockpit.cs` (WebView2) + scripts de build/install: desktop Windows pronto, sem Electron/Tauri.
  - `web/Pane.tsx`, `PaneGrid.tsx`, `Workspace.tsx`, `Lateral.tsx`, `Modal.tsx`, `Editor.tsx`, `Arquivos.tsx`, `QuadroTarefas.tsx`, `Consumo.tsx`, `Skills.tsx`, `Redline.tsx`, `Maestro.tsx`, `PoliticaIA.tsx`: UI de multi-terminal, arquivos, tarefas, consumo, skills, politica.
  - `servidor/` : PTY, cotas Codex (`codex-quota.ts`), `cofre.ts` (cofre/memoria), `agy.ts`.
  - Cuidado: Cockpit precisa de servico Node sempre ligado + node-pty (modulo nativo). Isso colide com "sem servico sempre ligado" se virar parte do core da Helena; ok como app opcional separado que le `~/.helena` e o cofre.

## 3. Restricoes declaradas (Vault/Memory)
- **helena-sem-sql-docker / helena-roadmap**: nada de SQL, Docker, servicos sempre ligados; tudo cabe em LLM + Obsidian/arquivos. "Nao quero criar nada de SQL, nada que fique rodando em Docker." Hoje reforcado no HANDOFF Decisions ("everything is files + git + hooks"; sem dependencia nova, sem LLM em hook, sem proxy local).
- **economia-de-tokens**: plano de US$20, Opus 5.5 medium padrao, Sonnet 5.5 high no volume; sessoes curtas com /clear; respostas curtas (caveman+ponytail); sem benchmark grande nem subagentes sem necessidade, avisar custo antes; skill nova vai pra biblioteca.
- **sem-api-key**: nada de API key quando ha CLI logado (claude, agy, codex); imagens via `agy`. Vale pra produtos incluindo Cockpit. Um app da Helena deve autenticar so via CLIs.
- **estilo-visual**: minimalista, preto/branco + 1 acento, sem "cara de IA" (sem pontinhos, gradiente generico, card template), secoes em tela cheia, navbar so no scroll; animacao GSAP fluida. Legibilidade WCAG AA (helena-site-acompanha-features: contraste + print desktop/celular antes de mostrar).
- **helena-positioning**: Helena e memoria/verificacao para IAs que o usuario ja assina, NAO agente completo; nao compete com Hermes. Diferencial: verificacao e troca de IA conferida.
- **helena-site-acompanha-features**: toda feature nova vai ao site, README e CHANGELOG na mesma leva.
- **deploy-coolify**: deploy em VPS com Coolify, tudo em Docker compose (vale pros servicos dele, tensiona com "sem Docker" da Helena; app da Helena deveria ser desktop local, nao deploy).
- **vitor-quer-agente-faz-no-pc**: executar direto, nao mandar lista de comandos.
- **Branch por frente** (MEMORY.md): frente nova = branch propria, sem commit ate pedir. main protegida por `.helena/git` (commit em branch, merge).
- **Outras**: heredocs Bash comem barra invertida (usar Edit/Write); worker nunca sobrescreve `eval/results.json`; builders sequenciais (exceto race); preco de tooling "sob consulta" nos produtos comerciais.
