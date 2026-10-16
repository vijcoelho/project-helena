# Landscape de ADEs (Agent Development Environments) e harnesses de agentes desktop, late 2026

Data de referência: 2026-10-16. Pesquisa feita com 16 buscas web. Não foram abertas páginas completas: os dados vêm dos trechos de busca e de fontes secundárias, salvo onde indicado. Itens marcados "unverified" repousam em uma fonte fraca ou conflitante.

## Resumo rápido

Quase todo produto do grupo converge no mesmo modelo: o humano vira um "gerente" de várias sessões de agente em paralelo, cada uma isolada em um git worktree, com uma sidebar de sessões e uma tela de revisão de diff. A diferença está em quem é dono do harness (vendor único x multi-provider), em local x nuvem, e em open x closed source.

## Fichas por produto

### Hermes Agent (Nous Research)
- **O que é:** agente de código/uso geral da Nous Research. Em junho de 2026 saiu o Hermes Desktop em preview público, app nativo para macOS, Windows e Linux (v0.15.2, licença MIT). Fonte: https://decrypt.co/369952 e https://the-decoder.com/nous-research-releases-hermes-desktop-an-open-source-ai-agent-for-every-platform/
- **UX de supervisão:** layout chat-first, várias conversas simultâneas, navegação por pasta de projeto. Sessões e memória são as mesmas da CLI (é o mesmo core), então dá para trocar de interface no meio.
- **Destaques:** memória de projeto persistente, criação automática de skills, delegação a sub-agentes, conexão com Telegram/Discord/Slack/WhatsApp/Signal, cinco backends de execução sandboxed (local, Docker, SSH, Singularity, Modal). Fonte: https://hermes-agent.nousresearch.com/docs/user-guide/desktop
- **Preço:** acesso a mais de 300 modelos via Nous Portal (tier gratuito e pago).
- **Open/closed:** open source (MIT), segundo as fontes de lançamento.
- **Lançamento:** lançamento oficial em junho de 2026. Antes disso, as GUIs eram comunitárias. Sem dados de traction.

### Cursor (Anysphere)
- **O que é:** IDE baseada em VS Code. Cursor 3 (2 de abril de 2026) tornou o **Agents Window** a interface padrão.
- **UX de supervisão:** muitos agentes em paralelo entre repos e ambientes (local, worktree, nuvem, SSH remoto). Sessões aparecem na sidebar, inclusive as iniciadas em mobile, web, Slack, GitHub e Linear. Dá para migrar sessão de nuvem para local e vice-versa. Design Mode permite anotar elementos de UI no browser. Fonte: https://cursor.com/changelog/3-0 e https://forum.cursor.com/t/cursor-3-agents-window/156509
- **Agentes em nuvem:** VMs Ubuntu dedicadas que continuam rodando com o notebook fechado (fonte terciária, unverified nos detalhes de UI).
- **Preço:** Hobby grátis, Pro $20/mês, Pro+ $60/mês, Ultra $200/mês, Teams $40/usuário/mês, Enterprise sob consulta. Modelo de créditos (cada plano pago inclui um pool igual ao preço). Os guias divergem sobre como o modo auto é cobrado. Fonte: https://www.morphllm.com/cursor-model-pricing (agregador, unverified).
- **Open/closed:** closed source.
- **Lançamento / traction:** IDE com base grande de usuários pagantes antes do Cursor 3; sem números confiáveis desta pesquisa.

### BridgeMind / BridgeSpace (unverified)
- **O que é:** "agentic organization" de vibe coding, fundada em 2025, sede em Natick/MA (remoto). Suíte de quatro produtos: BridgeCode (CLI), BridgeVoice (ditado), BridgeMCP (colaboração multi-agente) e BridgeSpace (terminal/workspace nativo de agentes, com Kanban e múltiplos painéis). Fonte: https://www.everydev.ai/developers/bridgemind e listagens em moge.ai.
- **UX:** command center com Kanban e até 16 agentes em paralelo, rodando Claude, Codex, Gemini e Cursor lado a lado (BridgeSpace 3). Fonte: https://www.hunted.space/product/bridgespace-3
- **Preço / open source:** não encontrado.
- **Lançamento / traction:** listagens em linguagem promocional, com depoimento de fundador. Status do BridgeCode conflita (em breve x ativo). Nenhuma review independente encontrada. Tudo unverified.

### Overclock
- **Não confirmado como ADE desktop.** A busca só encontrou overclock.work, descrito como ferramenta web de automação de marketing: "time de agentes" que revisam o trabalho uns dos outros, com aprovações e log de cada execução. Fonte: https://alternativeto.net/software/overclock/about
- O catálogo de agentes "overclock-*" presente no ambiente local é outro produto (pipeline de vídeo/site). Não o trate como o Overclock de squads desktop. Unverified que exista um app de "squads" desktop.

### Conductor
- **O que é:** app Mac para rodar vários agentes (Claude Code e Codex, e Cursor segundo o brandkit) em workspaces isolados, cada um com git worktree, terminal, diff e checks próprios. Fonte: https://www.conductor.build/workflows/run-parallel-codexes e https://www.morphllm.com/conductor-ai-coding
- **UX:** orquestra o time e revisa/faz merge das mudanças de cada workspace. Alvo de 5 a 10 agentes paralelos por repo. Scripts de setup e variável CONDUCTOR_PORT para dev servers paralelos.
- **Preço:** app gratuito, usa o login Claude/Codex existente (fonte: Morphllm). Apple Silicon apenas (v0.37 na época).
- **Open/closed:** closed source (inferido; não confirmado). **Lançamento:** não verificado. Há um "Conductor Cloud" anunciado, status não verificado.

### Warp (agentic terminal, Oz)
- **O que é:** terminal com agentes. Oz é a camada de agentes em nuvem/orquestração. Fonte: https://itsfoss.com/news/warp-launches-oz.md
- **Preço (conflitante):** review de 13/10/2026 coloca Build em ~$18/mês anual (com $20 de uso) e Business em $45/usuário/mês. Listagem de abril de 2026 dá Build $20 com 1.500 créditos e Max $200. Não achei preço específico do Oz. Fonte: https://www.deployhq.com/guides/warp (unverified).
- **Open/closed:** closed source (inferido). **Lançamento / traction:** sem dados confiáveis.

### Zed
- **O que é:** editor nativo open source. Parallel Agents no Agent Panel: vários agentes na mesma janela, sidebar de threads e escolha de quais pastas/repos cada um acessa. Terminal Threads (20/05/2026) permite rodar claude, codex, amp etc. como threads gerenciadas. Subagentes via `spawn_agent` (março/2026). Fontes: https://zed.dev/blog/parallel-agents e https://zed.dev/blog/terminal-threads
- **Preço:** editor gratuito; plano business com SSO/SOC 2 no roadmap (sem prazo).
- **Open/closed:** open source. **Lançamento:** Zed 1.0 em 29/04/2026 segundo fonte terciária (unverified).

### Codex desktop app (OpenAI)
- **O que é:** app macOS dedicado para orquestrar agentes Codex. Lançado em 2 de fevereiro de 2026. Fonte: https://openai.com/ms-BN/index/introducing-the-codex-app/ e https://alternativeto.net/news/2026/2/openai-unveils-a-dedicated-codex-desktop-app-for-macos-and-anyone-can-try-it-for-free
- **UX:** cada agente tem sua thread, agrupada por projeto. Suporte nativo a worktrees. Revisão de diff dentro da thread, comentários no diff e abertura no editor.
- **Preço:** incluído nas assinaturas do ChatGPT, com acesso limitado grátis.
- **Open/closed:** closed. **Plataforma:** só macOS Apple Silicon (confirmado pela doc da OpenAI na data da busca).

### Claude desktop / Claude Code desktop (Anthropic)
- **O que é:** Claude Code desktop redesenhado em 14/04/2026 em torno de sessões paralelas. Fonte: https://claude.com/blog/claude-code-desktop-redesign
- **UX:** sidebar de sessões filtrável por status, projeto ou ambiente; painéis arrastáveis (terminal, editor, diff viewer, preview HTML/PDF); "side chat" (Cmd+;) para perguntas laterais sem perder contexto. Routines (agentes agendados em nuvem) foram lançadas na mesma semana.
- **Preço:** planos Pro, Max, Team e Enterprise.
- **Open/closed:** closed (app); Claude Code CLI é a superfície principal.
- Um resultado datado de 22/08/2026 não bate com a data de abril. Tratar com cautela.

### Google Antigravity (2.0)
- **O que é:** IDE/plataforma agêntica do Google com quatro superfícies. Antigravity 2.0 no I/O em 19/05/2026. A CLI da Antigravity substituiu o Gemini CLI, que deixou de servir contas gratuitas e individuais em 18/06/2026. Fonte: https://www.cloudzero.com/blog/google-antigravity-pricing/ e https://mcp.directory/blog/antigravity-2-launch-google-io-2026
- **Preço (conflitante):** AI Pro $19,99/mês; novo tier AI Ultra $100/mês (5x Pro); tier de $200/mês (20x Pro, antes $250). Uma fonte dá $249,99 para o Ultra. Cotas semanais só para runs autônomos de agente. Créditos extras por consumo.
- **Open/closed:** closed. **Traction:** não verificado.

### Kiro (AWS)
- **O que é:** IDE agêntica "spec-driven": gera requisitos, design e tarefas antes de codar. Segundo fonte, é o sucessor designado do Amazon Q Developer (jun/2026). Fonte: https://noqta.tn/en/blog/kiro-aws-agentic-ide-spec-driven-development-guide-2026
- **Preço (credit-metered, conflitante nos números):** grátis com 50 créditos/mês; Pro $20 (1.000 créditos); Pro+ $40; Pro Max $100; Power $200. Créditos extra a $0,04. Fonte: https://tooldirectory.ai/tools/kiro (unverified).
- **Open/closed:** closed. **GA:** datas conflitantes (nov/2025, mar/2026, 7/05/2026). Unverified.

### Amp (Amp, Inc.)
- **O que é:** agente de código. Spin-out da Sourcegraph em dezembro de 2025, agora empresa independente. Fonte: https://rywalker.com/research/amp-sourcegraph
- **Preço:** pay-as-you-go com zero markup sobre preço de API para indivíduos (mínimo $5 de crédito), mais assinaturas. Enterprise com acréscimo de 50% segundo um agregador.
- **Modelo de negócio, conflitante:** o free tier era patrocinado por anúncios (grant diário de ~$10 com ads, receita reportada de $10M+ por ano). Uma análise diz que os ads acabaram em março/2026; outras páginas de meados de 2026 ainda descrevem o grant como patrocinado. Unverified.
- **Open/closed:** closed (inferido). Threads para salvar e compartilhar sessões.

### OpenCode (sst / anomalyco)
- **O que é:** agente de código em terminal, MIT, agora no repo anomalyco/opencode. Fonte: https://morphllm.com/comparisons/opencode-vs-claude-code
- **Traction:** o mais estrelado da categoria. Estimativas: ~157K (maio/2026) e ~172K (junho/2026) estrelas. Números variam por fonte; a comparação com Claude Code também vem de fontes secundárias.
- **Preço:** grátis e open source. Multi-provider (a "provider war" citada nas fontes).

### Crush (Charm)
- **O que é:** agente de código em terminal, escrito em Go, derivado da base Go original do OpenCode. Fonte: https://upd.dev/charmbracelet/crush
- **Traction:** ~25K a ~27,7K estrelas (datas variadas). **Licença:** conflitante (FSL-1.1-MIT ou MIT). Unverified.

### Outros que apareceram com tração ou relevância
- **Superset:** workspace de agentes da YC Spring 2026, macOS (Windows/Linux "chegando"). Licença Elastic License 2.0 (source-available, não OSI; antes Apache 2.0). Pro ~$20/mês. Roda 100+ agentes paralelos com worktrees e diff review. Fonte: https://superset.sh/compare/superset-vs-agent-orchestrator (página do próprio vendor; unverified). Não achei contagem de estrelas do próprio Superset.
- **Orca:** citado pelo Superset como o ADE open source mais popular, ~39K estrelas, MIT (fonte concorrente, unverified).
- **Agent Orchestrator, Emdash, Agent Desk, Agent Teams, Zenflow:** apps de orquestração citados em listagens. Sem dados de tração; não aprofundados.

## (a) Features que aparecem em 3 ou mais produtos (table stakes)

| Feature | Quem tem |
|---|---|
| Sessões/agentes paralelos com sidebar de status | Cursor, Conductor, Codex app, Claude Code desktop, Zed, Superset, BridgeSpace, Hermes Desktop |
| Isolamento por git worktree | Conductor, Codex app, Superset, Cursor (worktrees), Claude/Codex (worktrees) |
| Revisão de diff dentro do app + comentário | Codex app, Conductor, Superset, Cursor |
| Terminal integrado / agentes de terminal em thread | Zed (Terminal Threads), BridgeSpace, Claude Code desktop, Warp |
| Rodar agentes em nuvem e em local, com troca de ambiente | Cursor, Warp (Oz), Claude Code (Routines), Codex, Conductor Cloud (não verificado) |
| Multi-agente / sub-agentes | Zed (spawn_agent), Hermes, Antigravity, Kiro (?), Overclock (marketing) |
| Preço por créditos/uso com planos mensais | Cursor, Kiro, Warp, Antigravity, Amp |
| Login com a conta do provedor (BYO) | Conductor, Superset (free tier), OpenCode |

## (b) Features que só 1 produto tem e parecem diferenciais reais

- **Hermes:** memória de projeto persistente e criação automática de skills, mesmo core entre CLI e desktop (sessão migra entre interfaces).
- **Cursor:** Design Mode (anotar elementos de UI direto no browser dentro do Agents Window).
- **Kiro:** spec-driven: requisitos, design e tarefas antes do código.
- **Zed:** Terminal Threads (qualquer CLI vira thread gerenciada na sidebar) e editor open source.
- **Amp:** pass-through de preço de API sem markup para indivíduos.
- **Conductor:** scripts de setup e CONDUCTOR_PORT para dev servers paralelos sem colisão de porta.
- **Claude Code desktop:** side chat (branch de pergunta sem perder o contexto da tarefa rodando).
- **Antigravity:** superfície de equipe com /teamwork-preview (gated ao tier de $200).
- **Superset:** remote workspaces e integração com Linear no plano pago.

## (c) Gaps que ninguém cobre bem

**1. Memória entre sessões.** Hermes é o único com memória de projeto persistente declarada. Nos demais, o contexto morre com a sessão ou fica restrito a um worktree. Não achei produto que mostre ao humano o que o agente "lembra", deixe editar/esquecer, e que sincronize isso entre Claude, Codex e Cursor. Essa é uma inferência a partir da falta de resultados nas buscas, não um fato medido.

**2. Verificar a saída do agente.** O que aparece é revisão de diff e rodar checks no workspace (Conductor). Não encontrei nenhum app que trate verificação como produto: quem valida o que o agente afirmou, com evidência executável (teste, screenshot, reprodução), e marca o item como verificado ou reaberto. Inferência a partir da ausência de evidência, não medida.

**3. Controle de custo e tokens.** Os modelos de cobrança estão confusos e mudam sozinhos: créditos que variam por modelo (Cursor, Warp: "non-deterministic"), cotas semanais só para runs autônomos (Antigravity), tiers com números conflitantes entre fontes (Kiro). Nenhum app mostra por sessão, por agente e por tarefa quanto custou em tempo real com orçamento e corte automático. Amp é o mais transparente (zero markup), mas não resolve o orçamento por tarefa.

**4. Troca de provedor.** Multi-provider existe em Conductor, Superset, BridgeSpace, Zed (ACP) e OpenCode, mas quase sempre é "rodar vários CLIs lado a lado", e não roteamento: trocar o modelo de um agente no meio da tarefa, com o contexto preservado, parece raro. Os apps de vendor único (Codex app, Claude Code desktop, Antigravity) não fazem isso. Hermes oferece 300+ modelos via Nous Portal, mas sob o mesmo gateway. Inferência; não testei.

## Limitações desta pesquisa

- Fontes majoritariamente secundárias (agregadores, blogs de review, páginas de comparação de vendors). Só o changelog da Cursor, o changelog/blog da Claude e as páginas da OpenAI e da Nous foram tratados como primários, e mesmo assim só pelos trechos de busca.
- Não abri páginas completas (orçamento de tool calls).
- Overclock e BridgeMind têm fontes fracas; não confirmei a existência de um app desktop de squads da Overclock.
- Números de estrelas e preços mudam rápido. Confirmar nas páginas oficiais antes de usar em decisão.

## Fontes principais (por produto)

- Hermes: https://decrypt.co/369952 ; https://the-decoder.com/nous-research-releases-hermes-desktop-an-open-source-ai-agent-for-every-platform/ ; https://hermes-agent.nousresearch.com/docs/user-guide/desktop
- Cursor: https://cursor.com/changelog/3-0 ; https://forum.cursor.com/t/cursor-3-agents-window/156509 ; https://www.morphllm.com/cursor-model-pricing
- BridgeMind/BridgeSpace: https://www.everydev.ai/developers/bridgemind ; https://www.hunted.space/product/bridgespace-3
- Overclock: https://alternativeto.net/software/overclock/about
- Conductor: https://www.conductor.build/workflows/run-parallel-codexes ; https://www.morphllm.com/conductor-ai-coding
- Warp: https://itsfoss.com/news/warp-launches-oz.md ; https://www.deployhq.com/guides/warp
- Zed: https://zed.dev/blog/parallel-agents ; https://zed.dev/blog/terminal-threads
- Codex app: https://openai.com/ms-BN/index/introducing-the-codex-app/ ; https://alternativeto.net/news/2026/2/openai-unveils-a-dedicated-codex-desktop-app-for-macos-and-anyone-can-try-it-for-free
- Claude Code desktop: https://claude.com/blog/claude-code-desktop-redesign
- Antigravity: https://www.cloudzero.com/blog/google-antigravity-pricing/ ; https://mcp.directory/blog/antigravity-2-launch-google-io-2026
- Kiro: https://noqta.tn/en/blog/kiro-aws-agentic-ide-spec-driven-development-guide-2026 ; https://tooldirectory.ai/tools/kiro
- Amp: https://rywalker.com/research/amp-sourcegraph ; https://tessl.io/blog/amp-s-new-business-model-ad-supported-ai-coding
- OpenCode/Crush: https://morphllm.com/comparisons/opencode-vs-claude-code ; https://upd.dev/charmbracelet/crush
- Superset: https://superset.sh/compare/superset-vs-agent-orchestrator
