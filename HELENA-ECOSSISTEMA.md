# Helena como ecossistema: pesquisa e plano

Data: 2026-10-16. Fontes: quatro relatórios em `extras/pesquisa-ecossistema/`:

- `r1`: cenário de ADEs (Hermes, Cursor 3, Conductor, Codex app, Claude Code desktop, Zed, BridgeSpace, Superset...)
- `r2`: como outros harnesses viraram ecossistema e como ganham dinheiro
- `r3`: lançamento, hype e waitlist
- `r4`: inventário das 48 features da Helena, do Cockpit e das suas restrições

Números de mercado vêm de fontes secundárias, e cada relatório marca o que não foi verificado.

---

## A conclusão em uma frase

**Não construa outro harness. Construa o ADE que confere.** A pesquisa achou os mesmos três buracos em todos os
apps do mercado, e a Helena já resolve os três por baixo. Só falta mostrar isso numa tela.

## Por que abrir a Helena em vez do terminal (r5, r6, 2026-10-16)

**O terminal mostra o que a IA diz. A Helena mostra o que ela fez, e se está certo.**

O app não substitui o Claude Code nem o Codex. Ele roda o mesmo CLI, com o mesmo login e as mesmas sessões, e põe por
cima a camada que o terminal não tem. Cada motivo abaixo é uma dor que a pesquisa achou, e cada um usa algo que a
Helena já tem por baixo. Por isso o Claude Code desktop não copia fácil.

| # | A dor (fonte) | O que a Helena faz | Estado |
|---|---|---|---|
| 1 | Não dá para ver o que cada subagente está fazendo; no VS Code eles viram "waiting" (r5 #1, r6) | Cada subagente vira um cartão com cada passo ao vivo, o tempo, os tokens e o que ele devolveu | feito (v0.1) |
| 2 | Não saber se terminou de verdade (r1 gap 2; nenhum app usa teste como portão, r6) | Cada turno termina com a conferência dela: ✓ testes passaram (qual comando, com testes escondidos) ou ✗ devolvido e por quê | hooks prontos; falta mostrar no turno (v0.2) |
| 3 | Fadiga de aprovação: "99 em 100 é sim óbvio, você para de ler" (r5 #3); esperando aprovação parece igual a pensando (r6) | O gate dela decide o óbvio sozinho. Só o que é arriscado vira um cartão com o motivo, e a Helena muda de cara quando espera você | v0.2 |
| 4 | A compactação apaga decisões e a IA volta para o caminho que já falhou (r5 #4) | Mostra no turno quais notas ela entregou ("lembrou: deploy-coolify"), e o que foi rejeitado ou substituído fica no handoff | eventos prontos; falta mostrar no turno (v0.2) |
| 5 | O limite de 5 h acaba cedo (r5 #6); ninguém troca de IA com o contexto (r1 gap 4, r6) | O limite aparece antes de acabar. Quando acaba, o mesmo chat continua no Codex ou no Gemini com o handoff | v0.3 |
| 6 | O custo é por sessão e nunca por tarefa (r1 gap 3, r6) | Custo de cada turno e tokens de cada subagente | feito (v0.1) |
| 7 | Precisa de input e ninguém avisa; o pedido no Claude Code foi fechado como "not planned" (r5 #8, issue #36885) | Notificação do Windows quando ela precisa de você ou quando termina; depois, pelo celular | v0.2 |
| 8 | Revisar o que mudou (r5 #7) | Linha do tempo do turno: arquivos tocados e desfazer até ali (o `rewind.js` já existe) | v0.3 |

**O que quem gosta de terminal não quer perder** (r5 §3), e como fica:
- **Ver a saída crua:** um botão abre o stream cru do turno.
- **Teclado:** Enter envia, Shift+Enter quebra a linha e Esc para a execução.
- **Velocidade:** HTML estático, sem framework nem build, e o servidor sobe em menos de 1 s.
- **O terminal continua lá:** clicar numa sessão continua ela numa cópia (`--fork-session`), e a original segue intacta.

**O momento que faz trocar** (r6 não achou nenhum app com um momento claro): mandar uma tarefa grande e, em vez de um
"waiting…", ver três subagentes trabalhando lado a lado. A Helena barra um deles, ele corrige, e o turno fecha com
"✓ testes passaram · npm test".

## O que o mercado tem e o que falta (r1)

Todo mundo já faz a mesma coisa. Cursor 3, Codex app, Claude Code desktop, Conductor, Zed, Superset e BridgeSpace
têm sessões paralelas numa barra lateral, um git worktree por agente, revisão de diff e terminal embutido. Isso virou
o mínimo. Competir aí é brigar com OpenAI, Anthropic e Cursor de graça. Um harness próprio (loop de agente, modelos,
gateway) também já existe aos montes: o OpenCode tem cerca de 170 mil estrelas e o Hermes Desktop saiu em junho.

Ninguém cobre bem três coisas:

| Buraco no mercado | O que a Helena já tem |
|---|---|
| **Memória entre sessões com controle humano.** Ver o que o agente lembra, editar, esquecer e usar a mesma memória no Claude, no Codex e no Cursor. Só o Hermes declara memória, e só dentro dele. | Notas no Obsidian, router, STALE, supersede, tidy, forget, `mcp.js` para outras IAs |
| **Verificação com evidência executável.** O mercado faz revisão de diff. Ninguém marca "verificado" com teste rodado, teste escondido ou teste que falha sem o patch. | Portão de "pronto", holdout, differential check, race, contraste WCAG, red team |
| **Custo por tarefa e troca de IA sem perder contexto.** Os créditos são confusos em todos. Os apps multi-provider só põem CLIs lado a lado, sem roteamento. | ledger, `/helena:budget`, limites por plano, troca em 80%/95% com HANDOFF conferido |

Isso confirma o posicionamento que já está na sua memória (`helena-positioning`): a Helena é memória, verificação e
economia para as IAs que você já assina. Ela não é mais um agente. O app deve vender isso.

---

## O ecossistema: cinco peças, um só lugar de dados

Todas as peças leem os mesmos arquivos: `~/.helena/*.jsonl`, o cofre Obsidian e `.helena/` no repo. Nada de SQL, de
Docker, de servidor sempre ligado ou de API key. As restrições continuam valendo.

### 1. Helena Core (já existe): plugin, hooks e MCP
O que melhorar antes de qualquer app:
- **Instalar com um comando** e um GIF de 30 segundos no README. Sem isso, nenhum lançamento converte (r3).
- **Entrar nos marketplaces do Claude Code e do Codex**, como o Superpowers fez (r2). Custo baixo, alcance alto.
- **MCP só de memória e handoff** para Cursor, Zed e Goose, sem exigir o plugin inteiro. O `mcp.js` já tem 7
  ferramentas. É empacotar e documentar.
- **Testar ao vivo o que entrou na 1.5.0** e ainda não foi testado numa sessão real: spec-only, holdout, differential
  check e `/helena:race`. Corrigir também o falso bloqueio do holdout com `sed`, que apareceu hoje no `audit.jsonl`.
- Do backlog: handoff em segundo plano a ~65% da janela.

### 2. Helena Deck: o app desktop (ADE)
O app não compete com o Cursor. É o painel que mostra o que a Helena sabe, conferiu e gastou.

**v0: janela companheira só de leitura.** Ela fica ao lado do Claude Code, do Codex ou do Cursor e lê os arquivos que
já existem. Não tem PTY nem módulo nativo. Dá para fazer em dias, não em meses.

| Tela | Fonte que já existe |
|---|---|
| Selo por sessão: pronto verde ou vermelho, holdout, differential | `~/.helena/audit.jsonl` (hoje só grava bloqueio; o `done.js` precisa gravar o "passou" também, uma linha) |
| O que a Helena injetou neste pedido | router (precisa gravar quais notas mandou) |
| Memória: notas STALE com motivo, aprovar ou rejeitar o que foi destilado, esquecer | cofre, `distilled.json` |
| Limites por IA, com projeção de "acaba dia X" e botão **Continuar no Codex** | `limits-*.json`, HANDOFF.md |
| Custo por tarefa e custo da própria Helena | `ledger.jsonl` |
| Linha do tempo de decisões: bloqueios, egress, rewind | `audit.jsonl`, `egress.jsonl` |

**v1: rodar os agentes dentro do Deck.** Isso reaproveita o Cockpit (`C:\Users\vijc\dev\agent-project`), que tem React
19, Vite, xterm.js, node-pty, PaneGrid, QuadroTarefas, Consumo e a casca WebView2 em C#. Cada painel mostra o agente
(claude, codex, agy) com o selo da Helena em cima. O `/helena:race` vira dois painéis lado a lado, e o vencedor é
quem passou nos testes. Atenção: a casca WebView2 só roda no Windows. Mac e Linux pedem Tauri depois, só se a waitlist
mostrar demanda.

Nome provisório: **Helena Deck**. Troque à vontade.

### 3. Helena no bolso: aprovação pelo celular
Quando um hook pede confirmação ("ask"), a pergunta vai para o Telegram e você responde sim ou não. O Claude Code já
tem Channels com allowlist (r2). A Helena só encaminha as decisões dela. Isso é útil exatamente no caso de hoje: você
longe do PC.

### 4. Registro com selo de prova e um benchmark público
Cada skill no `site/registry.json` mostra o ganho medido contra o baseline. Nenhum concorrente publica isso (r2, ideia
1). Com o tempo, os resultados do `race` (anonimizados) viram um placar público. Regra do r3: todo número sai com
script para reproduzir e com os casos em que a Helena perde.

### 5. Helena para times (depois, e é aqui que entra dinheiro)
- Memória de time por PR: o `/helena:share` vira um pull request revisado.
- Holdout no CI como GitHub Action: os testes escondidos rodam no time inteiro.
- Política como código (`.helena/policy`) aplicada a todos os desenvolvedores.

**Modelo de negócio (r2, r3):** o core fica open source e grátis para sempre. Cobra-se o que é conveniência ou time:
build assinado do Deck, recursos de equipe, talvez sincronização entre máquinas via git. Nada de preço antes de haver
uso, e nada de cobrar o que já está no repo.

---

## Waitlist e hype: como fazer sem queimar (r3)

- **O core não entra em waitlist.** Dev de open source instala em 5 minutos ou esquece. A waitlist é **só do Deck**.
- **Sem backend:** formulário Tally numa seção do site que já existe. Texto de LGPD dizendo para que serve o e-mail e
  como sair. Indicação opcional sobe na fila. Sem contador falso.
- **A prova vende, não o hype.** O caso Devin mostra que demo escolhida a dedo vira desconfiança. Mostre o eval e os
  casos em que a Helena perde.
- **Show HN** numa terça a quinta, de manhã no horário americano, com um título que diz o problema e o trade-off.
  Em português: TabNews e LinkedIn com o mesmo conteúdo reescrito, não traduzido por máquina.
- O vídeo-teaser do Deck segue o seu estilo (`helena-video-style`): mockup das telas acima e um contraste real "com e
  sem Helena".

## Ordem sugerida

| Quando | O quê |
|---|---|
| Semana 1 | Instalação em um comando, GIF, entrada nos marketplaces CC e Codex, teste ao vivo da 1.5.0 |
| Semana 2 | Deck v0 (janela companheira, só leitura) e as duas linhas de log que faltam (pronto "passou", notas injetadas) |
| Semana 2 | Seção de waitlist no site e teaser em vídeo do Deck |
| Semana 3 | Show HN do core com o eval, X em inglês, TabNews/LinkedIn em português |
| Semanas 4 a 6 | Deck v1 sobre o Cockpit (painéis, race lado a lado). Beta em lotes para a lista |
| Depois | MCP standalone, aprovação pelo celular, placar público, recursos de time |

## O que não fazer

- Não escrever um loop de agente próprio nem um gateway de modelos. Isso é commodity, vai contra o posicionamento e
  pede API key.
- Não criar nuvem, banco ou proxy. As restrições `helena-sem-sql-docker` e `sem-api-key` continuam valendo.
- Não lançar o Deck antes de o core instalar sozinho.
- Não colocar o core atrás de waitlist, não criar escassez falsa e não publicar número sem script.

## Decisões que são suas

1. Nome do app (Deck, Cockpit ou outro).
2. Deck v0 só de leitura (recomendado) ou já partir para o v1 com o Cockpit.
3. Se o Cockpit vira o Deck v1 (fork enxuto) ou continua um produto separado.
