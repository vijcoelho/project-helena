# R5 - Dores de quem usa agentes de código no terminal

Pesquisa feita com buscas web e leitura de algumas páginas (GitHub, mirrors de issues, blogs). Não consegui abrir Reddit nem Hacker News diretamente; as citações de Reddit vêm de snippets de busca ou de snapshots. Itens sem fonte estão marcados como (não verificado). Lembrar que vários "mirrors" de issues do GitHub (claudeissues.com) não são a fonte original.

## 1. As 10 dores mais citadas

**1. Visibilidade de subagentes (o que cada um está fazendo).** Em snapshot de Reddit, um usuário diz que no painel do VS Code só aparecem stubs ("waiting", sleep) enquanto subagentes rodam; um comentarista diz que no terminal aparece bem mais. Um guia afirma que o pai não vê os passos intermediários do subagente.
- https://www.morphllm.com/claude-subagents
- https://reddit.sentinel-team.org/posts/1uldqa5/snapshots/2026-07-03T03%3A00%3A16.73148Z
- Status atual não verificado.

**2. Sessões paralelas e conflito de arquivos.** Usuários que rodam vários agentes no mesmo repo preferem o CLI: "separate panes, separate git worktrees, zero conflict" (citação de snippet de busca, não verificado na página original).
- https://www.conductor.build/compare/claude-code

**3. Fadiga de aprovação.** "99 times out of 100 the answer is an obvious yes, you stop reading." Um post do Digg atribui o termo "approval fatigue" ao Anthropic e cita 93% de prompts aprovados; este número não tem fonte primária (não verificado).
- https://spin.atomicobject.com/permission-fatigue-claude-code/
- https://digg.com/ai/8te506p3

**4. Perder contexto na compactação.** Issues descrevem que o /compact apaga decisões e conhecimento estabelecido, e que o Claude volta a tentar abordagens que já tinham falhado. Contagens de comentários (200+, 150+) vêm de um dev.to, não verificadas.
- https://claudeissues.com/issue/29890-bug-context-compaction-loses-critical-working-knowledge-mid-session
- https://claudeissues.com/issue/574-bug-compact-is-now-being-run-automatically
- https://dev.to/gonewx/the-hidden-cost-of-ai-coding-context-loss-and-how-developers-are-fixing-it-4b0d

**5. Saber se a tarefa terminou de verdade (testes).** (não verificado): não encontrei fonte específica nas buscas desta rodada.

**6. Custo e limites de uso.** Relatos de limite de 5 horas batendo cedo ("earlier and earlier") e de sessões esgotando em ~19 minutos no plano Max. Anthropic admitiu horário de pico mais restritivo no limite de 5 horas e um bug de exibição corrigido em junho de 2026 que afetou ~3% dos usuários (fontes secundárias).
- https://claudeissues.com/issue/7550-bug-5-hour-limit-reached-randomly-earlier-and-earlier
- https://devops.com/claude-code-quota-limits-usage-problems/

**7. Revisar diffs.** Usuários dizem que o diff visual é mais fácil de escanear que o terminal; o Conductor se vende pela UI de revisão (aprovar/rejeitar por diff). Um podcast-transcrito afirma que o valor é a revisão, não o paralelismo.
- https://www.conductor.build/workflows/run-parallel-claude-codes

**8. Notificação quando precisa de input.** Há um hook oficial de Notification (osascript no macOS). A issue pedindo evento nativo "waiting for input" (#36885) está **fechada como "not planned"** com 6 comentários; um mirror dizia "resolved", o que está errado.
- https://code.claude.com/docs/en/hooks-guide
- https://github.com/anthropics/claude-code/issues/36885

**9. Retomar trabalho depois.** (não verificado): não encontrei fonte nesta rodada.

**10. Aprovação excessiva no Codex (Windows).** Issue #9062 do openai/codex, relatada via mirror: após atualizar para v0.80.0 no Windows nativo, o modo agent pedia aprovação para quase todo comando, inclusive leitura dentro do workspace, e falhava com `CreateProcessWithLogonW failed: 5`. Workaround relatado: `experimental_windows_sandbox = false`.
- https://github.com/openai/codex/issues/9062 (mirror: https://upd.dev/openai/codex/issues/9062)

## 2. Gambiarras e tração

- **claude-squad** (smtg-ai/claude-squad): tmux + git worktrees para rodar várias sessões. GitHub, verificado nesta rodada: **8,6k estrelas, 630 forks**; descrição: "Manage multiple AI terminal agents like Claude Code, Codex, OpenCode, and Amp." https://github.com/smtg-ai/claude-squad
- **Notificação via hook** (Notification/Stop + osascript ou app de menu bar): padrão caseiro documentado oficialmente e um app de menu bar citado em Reddit. Estrelas não verificadas.
- **Statusline com % de contexto** (kcchien/claude-code-statusline, usedhonda/statusline ccsl, gists): contagens de estrelas não encontradas (não verificado). https://github.com/kcchien/claude-code-statusline
- **ccusage**: busca não retornou nada específico (não verificado); não tenho estrelas nem reclamações sobre ele.
- **claude-session-driver** (tmux, controla sessões como workers): 90 estrelas segundo um diretório de terceiros (não verificado). https://gittrend.io/repo/obra/claude-session-driver
- **oh-my-claudecode**: 39,6k estrelas segundo um diretório de terceiros (não verificado).

## 3. O que usuários de terminal não querem perder ao migrar para desktop

- **Ver tudo cru / saída do subagente**: o terminal mostra mais do que o painel do VS Code (snapshot de Reddit, ver item 1).
- **Velocidade**: uma issue fechada de abril de 2026 relata que o terminal parece mais rápido que o app desktop no Mac; é um relato único, não benchmark. https://claudeissues.com/issue/50906-feature-request-performance-comparison-and-optimization-for-desktop-cli-vs-termi
- **Pipeline e automação** (`--print`, Agent SDK): citado como território do terminal (blog de marketing).
- **Teclado e scrollback**: (não verificado): não encontrei fonte.

## 4. Reclamações sobre apps desktop

- **Claude Code desktop**: múltiplas contas mal suportadas e extensão instável com três sessões no mesmo workspace (comentário de Reddit via snippet, não verificado); no Linux só há CLI (comparação de blog); por padrão fala só com a API da Anthropic, Bedrock exige terminal (guia).
- **Codex app / Cursor agents**: (não verificado): não pesquisei reclamações específicas nesta rodada.
- **Conductor**: Apple Silicon only, e a pergunta de se a UI de revisão compensa o custo de uma app nova (podcast-transcrito, não verificado).

Fontes de apoio: https://www.morphllm.com/conductor-ai-coding , https://prosperinai.substack.com/p/claude-code-terminal-vs-desktop-app
