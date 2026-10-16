# R6: GUIs para agentes de código (tração e gaps)

Data da pesquisa: 2026-10-16. Stars são snapshots de agregadores ou da página do repo, podem estar defasadas. "(não verificado)" = sem fonte encontrada nesta pesquisa.

## Apps (12)

1. **opcode** (ex-Claudia): desktop Tauri 2 para gerenciar sessões do Claude Code e agentes customizados. ~21–22k stars (agregadores divergem). Elogio: (não verificado). Reclamação: uma review diz que não há commits públicos desde 13/out/2025; atividade incerta. https://github.com/winfunc/opcode (contagem: https://summary.ecosyste.ms/projects/374396)

2. **Crystal**: desktop para várias sessões Codex/Claude Code em worktrees separados, para comparar abordagens. ~3.1k stars. Status: descontinuado, substituído pelo Nimbalyst. Elogio/reclamação: (não verificado). https://github.com/stravu/crystal

3. **claude-squad**: TUI no terminal para rodar Claude Code, Codex, OpenCode e Amp em workspaces isolados. ~8.6k stars. Reclamação (blog citado em busca, sem URL capturado): faz pouco que skills e slash commands já não façam. https://github.com/smtg-ai/claude-squad

4. **Conductor** (Melty Labs): app para Mac que roda Claude Code e Codex em worktrees, com dashboard de diffs e merge. Também tem Conductor Cloud. Tração: (não verificado). Reclamação: só macOS com Apple Silicon. https://www.conductor.build/llms-full.txt ; https://www.morphllm.com/conductor-ai-coding

5. **Vibe Kanban** (BloopAI): kanban em que cada tarefa tem branch, worktree, terminal e dev server. ~28.4k stars. Elogio (página do repo): comentários inline no diff voltam direto para o agente. Reclamação (busca secundária): overhead para edições pequenas. Status: a página do repo diz "Vibe Kanban is sunsetting", mantido pela comunidade. https://github.com/BloopAI/vibe-kanban

6. **Claude Code desktop**: sidebar com sessões paralelas, Ctrl/Cmd+clique para ver duas lado a lado, painel de tarefas com subagentes e shells em background, notificação do SO quando a sessão termina. Os rótulos "Needs input / Working / Completed" não aparecem na doc oficial (a doc fala em filtrar por status). Agent View (`claude agents`) é research preview, segundo comentário de terceiros. Reclamação: no VS Code, subagentes aparecem como stubs ("Waiting for a reviewer task"), segundo um post do Reddit em snapshot de terceiro. https://code.claude.com/docs/en/desktop ; https://reddit.sentinel-team.org/posts/1uldqa5/snapshots/2026-07-03T03%3A00%3A16.73148Z

7. **Codex desktop app** (OpenAI): threads em modos Local, Worktree ou Cloud. Painel de review com escopo (não commitado, branch ou último turno). Controle remoto pelo app mobile do ChatGPT. Lançado em 2/fev/2026 no macOS, Windows em mar/2026 (blog de terceiro). Elogio/reclamação: (não verificado). https://developers.openai.com/codex/app ; https://developers.openai.com/codex/app/review

8. **Sculptor** (Imbue): UI para agentes paralelos, cada um em container Docker com cópia do projeto e branch próprio. O repo local só muda ao puxar. Tração e reviews independentes: (não verificado). O "startup em segundos" é número do próprio fornecedor. https://docs.imbue.com/features/containers ; https://imbue.com/blog/containers

9. **Omnara**: app mobile e web para acompanhar, dirigir e aprovar sessões de Claude Code e Codex, com push quando o agente pede input. Nota 4.3 com 18 avaliações na App Store. Elogio: aprovação pelo celular (fonte: Launch HN, YC S25). Reclamação: (não verificado). https://apps.apple.com/app/id6748426727

10. **happy** (slopus): app open source (MIT) para usar Claude, Codex e Grok com assinaturas existentes, com app mobile criptografado de ponta a ponta e sessões multiplayer. ~24.2k stars. Elogio/reclamação: (não verificado). https://github.com/slopus/happy

11. **ccusage**: CLI que lê os logs JSONL locais do Claude Code e mostra tokens e custo estimado por dia, mês, sessão e bloco de 5h, com dashboard ao vivo. ~10.1k stars (snapshot de jan/2026). Elogio/reclamação: (não verificado). https://github.com/ryoppippi/ccusage

12. **claudecodeui / CloudCLI** (siteboon): web e mobile responsivo com chat, shell, explorador de arquivos e git. Listagens novas incluem OpenCode, Cursor CLI e Codex. ~11.5k stars (snapshot). Licença divergente: AGPL-3.0 (OSSInsight) ou GPL v3 (SourcePulse). Elogio/reclamação: (não verificado). https://github.com/siteboon/claudecodeui

Não pesquisados ou sem confirmação: Terragon (um artigo diz "now-dead", sem confirmação), CUI (não pesquisado).

## Gaps (evidência fraca, a maioria marcada)

- **Subagentes como árvore ao vivo**: o desktop do Claude Code tem painel de tarefas, mas o relato do Reddit diz que a visão no VS Code colapsa o stream. Árvore ao vivo: (não verificado).
- **Por que a IA fez isso**: nenhuma fonte encontrada (não verificado).
- **Provar que terminou (testes passaram)**: Vibe Kanban e Crystal mostram diff e preview, mas não encontrei teste como gate de conclusão (não verificado).
- **Memória entre sessões controlada pelo humano**: não encontrado (não verificado).
- **Trocar de IA quando o limite acaba**: Happy e claude-squad suportam vários agentes, mas troca automática por limite não foi encontrada (não verificado).
- **Custo por tarefa**: ccusage mede por sessão e por bloco de 5h, não por tarefa ou worktree (inferência minha).
- **Replay/linha do tempo**: não encontrado (não verificado).
- **Bloqueado vs pensando**: um blog de Crystl argumenta que agente esperando aprovação parece igual a agente pensando, e pede logs de tool-call navegáveis. Fonte de vendor, não verificada: https://crystl.dev/blog/what-a-claude-code-gui-should-do/

## Momento mágico

Não achei citações reais de usuários elogiando um app. Os sinais mais fortes são de produto: notificação do SO quando a sessão termina (Claude Code desktop), aprovar pelo celular com push (Omnara, happy) e comentário inline no diff que volta ao agente (Vibe Kanban). A dor mais citada é perder de vista qual agente está fazendo o quê, quando há vários em terminais separados (MindStudio, fonte de vendor).

## Limites

Pesquisa feita em modo padrão, sem threads diretas do Reddit ou do Hacker News além de um snapshot. Stars vêm de agregadores e podem estar defasadas. Elogios e reclamações quase todos são (não verificado).
