# R2: como harnesses viraram ecossistema, e 10 ideias para a Helena

Data da pesquisa: 2026-10-16. Fontes de busca web, com 9 chamadas. Itens marcados como **(unverified)** têm números de fontes secundárias, conflitantes ou sem confirmação oficial.

## 1. Camadas de ecossistema e ordem em que apareceram

Ordem observada nos projetos pesquisados (não é uma regra fixa, é um padrão):

1. **Core open source (CLI/harness + licença permissiva).** OpenCode é MIT e gratuito, com BYOK (https://rywalker.com/research/opencode). Goose é Apache 2.0, roda como desktop, CLI e API (https://www.arcade.dev/blog/goose-the-open-source-agent-that-shaped-mcp). Letta tem framework Apache 2.0 (https://vectorize.io/articles/mem0-vs-letta). Mem0 também é self-hostable (mesma fonte).
2. **Compatibilidade com padrões de plugin/MCP.** Goose se apoia em MCP como sistema de extensões, em vez de plugin proprietário (arcade.dev, acima). Codex adicionou plugins em março de 2026, com marketplace por URL Git ou pasta local (https://nz.dealroom.co/news/feed/openai-adds-plugins-to-codex-playing-catch-up-with-claude-code-and-gemini). Um plugin oficial deixa o Codex rodar dentro do Claude Code (codex-plugin-cc, 30/03/2026, fonte: mesma notícia dealroom). Superpowers (obra) existe nos dois marketplaces (https://www.sourcepulse.org/projects/21489938).
3. **Canais de chat e controle remoto.** Claude Code Remote Control (fev/2026) permite pegar a sessão local pelo app móvel. Channels (mar/2026) conecta Telegram e Discord à sessão, com allowlist de remetentes (https://www.atcyrus.com/stories/what-are-claude-code-channels e https://eu.36kr.com/en/p/3730899849773313). Hermes Agent (Nous) faz um único gateway para Telegram, Discord, Slack, WhatsApp, Signal e CLI, com voz (https://jimmysong.io/ai/hermes-agent e https://hermes-agent.org/). Status no Windows nativo é **(unverified)**, fontes conflitam.
4. **Cloud / VM / sandbox.** Hermes roda em VM na nuvem e você conversa pelo Telegram (jimmysong, acima). Devin, Factory e Codex/Claude Code usam sandbox na nuvem para tarefas paralelas (https://www.mojoauth.com/blog/top-10-ai-dev-agents é fonte de comparação; uso como sinal de mercado, não como prova).
5. **Desktop app.** OpenCode tem app Tauri para macOS, Windows e Linux, sobre a arquitetura cliente/servidor que também permite controle por mobile (https://awesomeagents.ai/news/opencode-8m-users-one-year/ — **(unverified)**, fonte autodeclarada). Goose tem desktop app.
6. **Gateway pago de modelo.** OpenCode Zen (pay-as-you-go de modelos premium) e Go (US$ 10/mês, modelos open-weight) (rywalker, acima). Kilo vende créditos a partir de US$ 19/mês (https://fast.io/resources/kilo-code-vs-cline.md).
7. **Enterprise: SSO, gateway interno, seats.** OpenCode Enterprise: config central, SSO, gateway de IA interno, preço por seat, sem cobrança de token se o cliente trouxer o próprio gateway (https://opencode.ai/docs/enterprise/). Factory Business para até 150 seats, Enterprise com on-prem e chaves gerenciadas pelo cliente (https://usagepricing.com/blueprint/factory).
8. **Marketplace e registry.** Anthropic tem marketplace oficial com revisão; marketplaces comunitários não têm (fonte: fast.io e sourcepulse, acima). Continue tem marketplace de prompts e regras compartilhadas, com CI que checa código gerado por IA (fonte de vendor, **(unverified)**).

Lição que aparece em mais de um caso: **governança pesa tanto quanto código.** Goose foi para a Linux Foundation (Agentic AI Foundation, dez/2025), porque a marca ainda com a Block travava adoção enterprise (arcade.dev; https://aaif.io/blog/where-new-mcp-ideas-go-to-become-real-goose-as-a-proving-ground). Datas divergem entre fontes (nov ou dez/2025).

Memória: Mem0 levantou US$ 24M (seed + Série A, Basis Set) e Letta US$ 10M seed liderado pela Felicis, a ~US$ 70M pós (https://vectorize.io/articles/mem0-vs-letta e https://ecorpit.com/ai-agent-memory-mem0-zep-letta-cloudflare-comparison-2026/ — valores **(unverified)**, de blogs de comparação).

## 2. Como ganham dinheiro

| Modelo | Exemplos e números (fonte) |
|---|---|
| Core grátis + inferência paga (BYOK ou gateway) | OpenCode, Cline (individual grátis, paga só inferência), Kilo (rywalker; fast.io) |
| Assinatura de conveniência para modelo | OpenCode Go US$ 10/mês; Pro/Max em Devin e Factory US$ 20 e US$ 200/mês (pensero.ai; usagepricing.com). Preços de Devin divergem entre fontes **(unverified)** |
| Hub / features pagas sobre o core | Continue, a partir de US$ 10/mês (fonte de vendor, **unverified**) |
| Seats de time | Cline, US$ 20/usuário/mês (**unverified**, fontes conflitam); Factory Business; OpenCode Enterprise sob cotação |
| Memória como SaaS | Mem0: Hobby grátis, Starter US$ 19, Growth US$ 79, Pro US$ 249 (grafo de memória só no Pro). Letta Pro US$ 20 (vectorize.io; ecorpit — **unverified**) |
| Agente hospedado | Devin, Factory, Codex, Claude Code cloud: cobrança por seat com quota de uso |
| Foundation/open governance | Goose, sem receita direta; ganho é adoção enterprise |

Padrão: o core é grátis e open source, a receita vem de (a) não querer configurar modelo (gateway), (b) seats e SSO para empresa, (c) hospedagem. BYOK é o padrão em todos os de terminal.

## 3. Dez ideias para a Helena, ranqueadas por impacto / custo (solo dev)

Ordem: impacto alto e custo baixo primeiro. Cada ideia cita o que já existe na Helena.

1. **Selo de eval no registry (prova vs baseline).** Cada skill publicada no registry mostra o ganho medido contra o baseline. Nenhum dos concorrentes pesquisados publica prova de ganho por skill. Reusa: eval harness, `site/registry.json`. Custo: baixo. Impacto: alto, é o diferencial que a Helena já tem.
2. **Helena como MCP server standalone para Goose, Cursor e outros.** Goose e o ecossistema MCP são o lugar onde o padrão se consolida (arcade.dev). Expor só memória (vault Obsidian) e handoff como MCP, sem exigir o plugin inteiro. Reusa: MCP server, memória. Custo: baixo a médio.
3. **Listar no marketplace do Claude Code e no plugin do Codex.** Publicar a Helena como marketplace (Git URL) nos dois, nos moldes de Superpowers. Reusa: plugin atual. Custo: baixo. Impacto: alto em distribuição.
4. **Handoff automático quando o limite de plano acaba.** Quando `helena:limits` detecta que a janela de 5h ou a semana acabou, gera o handoff e sugere (ou abre) a outra IA. Reusa: limits, handoff, budget. Custo: médio. Impacto: alto para quem usa vários planos.
5. **Aprovação remota por Telegram/Discord para os bloqueios do hook.** Quando o hook bloqueia um comando destrutivo, manda a pergunta ao celular e aceita sim/não. Reusa: hooks. Custo: médio. Mesmo padrão de Channels, mas com o diferencial de gate de segurança (fonte de Channels: atcyrus, acima).
6. **Race público com placar.** `helena:race` já decide o vencedor por testes; publicar o resultado anonimizado (modelo, tarefa, tempo, custo) como benchmark da comunidade. Reusa: race, budget. Custo: médio.
7. **Memória de time versionada em git, com revisão.** `helena:share` já copia nota para `.helena/memory`. Tornar isso um fluxo de PR: a nota entra no repo só depois de review. Reusa: share, memória Obsidian. Custo: médio. Impacto: médio, é o gancho para equipe.
8. **Holdout tests como serviço de CI.** Rodar os testes escondidos do agente no CI do time, com selo. Reusa: holdout, done gate. Custo: médio. Vira ponto de venda para equipe.
9. **Adaptador de hooks para Goose e Hermes.** Traduzir o contrato de hook da Helena para o gateway/extensões desses projetos. Reusa: hooks. Custo: médio-alto. Impacto: médio, depende de API deles estar estável **(unverified)**.
10. **Gateway de modelo com BYOK e roteamento barato.** O `orchestrate` já manda tarefa para worker mais barato; expor como gateway com chave própria. Mais caro de manter, e disputa com OpenCode Zen e Kilo. Deixar para depois.

**Top 3 por impacto/custo:** (1) selo de eval no registry, (3) listar a Helena como marketplace no Claude Code e Codex, (2) MCP standalone de memória e handoff para Goose/Cursor.

## 4. Lacunas e cautelas

- Não achei fonte primária para **oh-my-opencode** nem para **agent OS** como categoria. Não afirmo nada sobre eles.
- Goose e Block: a busca mostrou só a fundação, não a estratégia comercial **(unverified)**.
- Aider: sem sinal de nuvem hospedada em 2026.
- Números de funding, usuários e receita (OpenCode, Cline, Kilo, Devin) vêm de blogs de comparação. Conferir nas páginas oficiais de preço antes de usar em material público.
- Hermes: suporte a Windows nativo conflita entre fontes.

## Fontes principais

- https://jimmysong.io/ai/hermes-agent
- https://hermes-agent.org/
- https://rywalker.com/research/opencode
- https://opencode.ai/docs/enterprise/
- https://awesomeagents.ai/news/opencode-8m-users-one-year/
- https://www.arcade.dev/blog/goose-the-open-source-agent-that-shaped-mcp
- https://aaif.io/blog/where-new-mcp-ideas-go-to-become-real-goose-as-a-proving-ground
- https://rywalker.com/research/letta
- https://vectorize.io/articles/mem0-vs-letta
- https://ecorpit.com/ai-agent-memory-mem0-zep-letta-cloudflare-comparison-2026/
- https://nz.dealroom.co/news/feed/openai-adds-plugins-to-codex-playing-catch-up-with-claude-code-and-gemini
- https://www.sourcepulse.org/projects/21489938
- https://www.atcyrus.com/stories/what-are-claude-code-channels
- https://eu.36kr.com/en/p/3730899849773313
- https://fast.io/resources/kilo-code-vs-cline.md
- https://usagepricing.com/blueprint/factory
- https://pensero.ai/blog/devin-pricing
- https://neuronfeed.com/startups/opencode
