# Helena — próximo passo (branch `feat/helena-next`)

Data: 2026-10-06. Base: Helena 1.0.0 (plugin do Claude Code, memória no Obsidian, biblioteca de skills, routines).

## O que os 4 links ensinam

| Produto | O que faz bem | O que a Helena pega |
|---|---|---|
| [Vellum](https://www.vellum.ai/) | Assistente com memória que roda local, 24/7, em Mac/iOS/Android/web/voz/email/Slack/Telegram/terminal. Pede aprovação para ação de risco até você marcar como confiável. Free local; nuvem $30 / $100 / $200 | "Local primeiro, nuvem opcional"; permissão que vira confiança com o tempo |
| [Slashy](https://www.slashy.com/) | Email + agenda com memória do seu jeito de escrever. Aceite dos rascunhos sobe de ~30% no dia 1 para 80%+ no dia 30. Responde por Slack/iMessage | Métrica pública de "quanto ela aprendeu"; escrever no seu tom |
| [Perplexity Computer](https://www.perplexity.ai/products/computer) | Orquestra 19 modelos, cada tarefa no modelo certo. Sub-agentes com teto de gasto. Max $200/mês com créditos | Roteador de modelo por tarefa + teto de gasto (a Helena já tem `budget.py`) |
| [Hermes Agent](https://hermes-agent.nousresearch.com/) | MIT, mesma memória em Telegram/Discord/Slack/WhatsApp/Signal/Email/CLI, cria skills sozinho, 200+ modelos. Free / Plus $20 / Super $100 / Ultra $200, cada um com créditos (+10%) | Modelo de negócio: núcleo aberto grátis + planos que dão créditos de modelo e ferramentas hospedadas |

Conclusão: todos têm **uma memória, várias portas**. A Helena já tem a memória (Obsidian) e a parte que eles não têm: skills que só carregam quando precisa e benchmark que prova o ganho. Falta abrir as portas.

## Princípio (não quebrar)

- O núcleo continua leve, local, MIT e sem API key: usa o CLI que a pessoa já tem logado (Claude Code, Codex, Gemini CLI, agy).
- Tudo que é servidor (bot, site com conta, planos) vira uma camada separada, **Helena Cloud**, opcional. Quem não quer nuvem não perde nada.
- Isso muda a regra antiga "sem bot / sem chat no site". A troca é de propósito: o núcleo segue igual, a nuvem fica em outra pasta (`cloud/`).

## Plano de ação

### Fase 1 — Helena em qualquer IA (2 semanas)
A memória já está no Obsidian. Falta cada CLI saber ler e escrever nela.
1. `helena-mcp`: servidor MCP local com `recall`, `remember`, `skill_find`, `skill_load`, `budget`. Um servidor serve Claude Code, Codex, Gemini CLI, Cursor, Claude Desktop.
2. Adaptador Codex: gera `AGENTS.md` com o brief da sessão + registra o MCP no `~/.codex/config.toml`.
3. Adaptador Gemini CLI: `GEMINI.md` + MCP no `settings.json`.
4. Adaptadores Grok CLI, Qwen Code, Kimi CLI, opencode: mesmo MCP, só muda o arquivo de instrução.
5. `distill.py` aceita transcript de outros CLIs (Codex grava em `~/.codex/sessions`), então a memória aprende com todos.
6. Teste: lembrar algo no Claude, abrir o Codex, ele responde usando a lembrança.

### Fase 2 — Bot estilo Grok no X (2-3 semanas)
7. `@helena` responde menções: lê o post + thread, responde curto, no tom dela.
8. Roda como routine do `worker.py` (poll a cada N min), com teto de gasto por dia.
9. Modo "só rascunho" primeiro: as respostas vão para o Inbox do Obsidian, você aprova, ela posta.
10. Depois Telegram e Discord com o mesmo cérebro (mesma memória, mesmas skills).
Custo: a API do X é paga por uso. Medir antes de abrir para o público.

### Fase 3 — Site com conta e planos (3-4 semanas)
11. Login, painel "o que a Helena aprendeu", download do plugin, chaves do bot.
12. Stripe com os planos abaixo.
13. Créditos de modelo pela OpenRouter ou Vercel AI Gateway (um contrato, muitos modelos).

### Fase 4 — Desktop (depois)
14. App Tauri (leve, Windows/Mac) que mostra memória, routines, gasto e um chat. Por baixo chama os CLIs já instalados.

## Planos (rascunho)

| Plano | Preço | O que libera |
|---|---|---|
| Free | R$ 0 | Plugin completo, local, MIT, usa o seu CLI (Claude/Codex/Gemini). Memória no seu Obsidian |
| Plus | R$ 49/mês | Sync da memória entre máquinas, bot no Telegram/Discord, 5 routines na nuvem, créditos para modelos baratos (Haiku, Gemini Flash, Grok mini, Qwen, Kimi) |
| Pro | R$ 149/mês | Tudo do Plus + modelos top (Opus, GPT, Gemini Pro, Grok), bot no X com sua conta, routines ilimitadas com teto, painel de time pequeno |
| Time | R$ 99/assento | Memória compartilhada do time, skills do time, controle de quem aprova o quê |

Créditos com +10% de bônus, igual ao Hermes. Teto de gasto sempre visível.

## 50 ideias

**Memória e cérebro**
1. Servidor MCP da Helena (base de tudo que vem depois)
2. Memória única para Claude, Codex, Gemini, Grok, Qwen, Kimi
3. Distill que lê transcript de qualquer CLI
4. "Quem me ensinou isso": cada memória guarda de qual IA e sessão veio
5. Métrica de aprendizado estilo Slashy: % de vezes que você aceitou sem corrigir, por semana
6. Memória por pessoa (contato) além de por projeto
7. Sync do vault entre máquinas (Plus), criptografado
8. Esquecer automático: memória que não foi usada em 90 dias vai para "arquivo"
9. Busca semântica local no vault (embeddings locais, sem API)
10. Importar memória do ChatGPT/Claude.ai (export JSON) no `/helena:setup`

**Multi-modelo**
11. Roteador: tarefa simples vai para modelo barato, tarefa difícil para o top (Perplexity Computer)
12. "Segunda opinião": pede a resposta de outro modelo quando o primeiro erra 2 vezes
13. Benchmark por modelo: `eval/run.py` roda a mesma tarefa em Claude, Codex e Gemini e mostra quem ganha
14. Teto de gasto por modelo e por dia
15. Fallback: limite do Claude estourou, continua no Codex com o mesmo contexto
16. Handoff entre IAs: `HANDOFF.md` que qualquer CLI entende
17. Skills no formato aberto `SKILL.md` funcionando em todos os CLIs que suportam

**Bot (estilo Grok)**
18. `@helena` no X responde menções
19. Modo rascunho com aprovação no Inbox
20. "@helena resume essa thread"
21. "@helena checa isso" (fact-check com busca na web e fonte)
22. "@helena transforma isso em código" (gera gist ou repo)
23. Bot no Telegram com a mesma memória
24. Bot no Discord para comunidade da Helena
25. WhatsApp (você já tem o MCP do WhatsApp Business)
26. Personalidade fixa e reconhecível (voz, humor, limites), escrita como skill
27. Rate limit e lista de bloqueio para não queimar crédito com spam

**Agente que trabalha sozinho**
28. Routines na nuvem (Plus) além das locais
29. Permissão que vira confiança: aprova 3 vezes a mesma ação, ela pergunta se pode fazer sozinha (Vellum)
30. Briefing da manhã: agenda + emails + PRs + o que ela aprendeu ontem
31. Email no seu tom (Gmail MCP já conectado), sempre em rascunho
32. Triagem de issues do GitHub nos seus repos
33. Vigia de deploy: falhou na Vercel, ela abre o log e propõe o fix
34. Metas longas: "lança a v1.1 até sexta", ela quebra em routines e mostra progresso
35. Sub-agentes com teto de gasto cada um

**Site e negócio**
36. Página de planos com Stripe
37. Painel web "o que a Helena aprendeu" (memórias, skills, gasto, economia)
38. Marketplace de skills: a pessoa publica a skill dela, outros instalam com um clique
39. Skills pagas com repasse para o autor
40. Página pública "Helena de fulano" para mostrar as skills de alguém (portfólio)
41. Programa de indicação: indicou, ganha créditos
42. Plano Time com memória compartilhada
43. Landing em inglês e português
44. Changelog público e roadmap votável no site

**Desktop e experiência**
45. App Tauri com memória, routines, gasto e chat
46. Ícone na bandeja: avisa "precisa de você"
47. Atalho global: abre um prompt rápido em qualquer lugar do Windows
48. Voz: fala com ela pelo microfone (Whisper local)
49. Modo apresentação: grava um vídeo curto do que ela fez na semana (skill video-demo já existe)
50. Instalador de um clique para Windows que configura Claude, Codex e Gemini de uma vez

## Ordem sugerida (o que fazer primeiro)
1. Ideia 1 (MCP) + 2 + 3: destrava todo o resto e não custa nada para rodar.
2. Ideia 13: prova com número qual IA ganha com a Helena. Vira marketing.
3. Ideias 18 + 19: bot no X em modo rascunho, só na sua conta.
4. Ideias 36 + 37: site com plano Free e Plus.
5. Desktop depois que tiver usuário pagando.
