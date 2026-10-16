# R3: Playbook de lançamento para ferramenta de dev com IA (Helena)

Data da pesquisa: 2026-10-16. Pesquisa web com ~12 chamadas. Itens marcados como **(não verificado)** têm fonte secundária, blog de marketing ou dado conflitante.

## Resumo executivo

- Waitlist sozinha não gera adoção. O caso mais documentado (Superhuman) combinava produto excelente, onboarding 1:1 e indicação. O fundador nega que o funil fosse escassez artificial.
- Para um projeto open source, o caminho que funciona é: repositório que instala em um comando, benchmark reproduzível, post no Hacker News e no X com um problema específico. Waitlist entra depois, só para o app desktop.
- Não há número público confiável de conversão de waitlist para nenhuma das ferramentas pesquisadas.

## 1. Mecânica de waitlist: o que existe de fato

- **Superhuman (o caso mais citado).** Lista de espera com mais de 180 mil a 275 mil pessoas, relatada em 2019-2020 (fonte secundária, **não verificado** no número exato). Cada usuário fazia uma chamada ao vivo de 30 minutos com especialista de onboarding. Indicação de outro usuário pulava a fila, sem incentivo monetário. Preço citado de 30 dólares por mês. Fontes: [TechCrunch, 2020](https://techcrunch.com/2020/02/28/superhuman-ceo-rahul-vohra-on-waitlists-freemium-pricing-and-future-products/), [Mixergy](https://mixergy.com/interviews/superhuman-with-rahul-vohra/), [AdviceScout](https://advicescout.com/why-superhuman-made-users-do-30-minute-video/).
  - Vohra nega que a espera fosse escassez artificial (FOMO), e diz que ela existia para garantir que cada usuário tivesse um bom primeiro uso. Ou seja, a lista é uma ferramenta de qualidade de onboarding, não só de marketing.
  - Números secundários que não consegui confirmar: "2,3x mais chance de virar pagante", "ROI de cerca de 60x nas chamadas", avaliação de 825 milhões de dólares. Não usar sem fonte primária.
- **Devin (Cognition, 2024).** Acesso por waitlist/early access, com demo viral no Upwork. Criticado por demos escolhidas a dedo (análise do canal Internet of Bugs, citado em [fikisipi](https://fikisipi.substack.com/p/short-post-a-look-at-devin-the-ai) e [eesel](https://eesel.ai/blog/cognition-ai-reviews)). O CEO reconheceu que estava "longe de perfeito". Lição: waitlist com demo exagerada gera hype que vira desconfiança.
- **Warp.** A lista de espera foi removida em 2022 com beta público (o título da pesquisa dizia 2026, mas a fonte [Warp, "Introducing Warp"](https://www.warp.dev/blog/introducing-warp) indica 2022). Em 2026 o cliente virou open source (MIT + AGPL, data divergente entre fontes: 28/04 ou 30/04 ou 11/05, [It's FOSS](https://itsfoss.com/news/warp-goes-open-source.md), [FOSS Linux](https://www.fosslinux.com/warp-terminal-goes-open-source-is-the-ai-first-terminal-ready-for-foss-purists)). Aqui o open source foi o motor de atenção, não a lista.
- **Cursor.** Crescimento de baixo para cima, por desenvolvedor dentro do fluxo de trabalho, sem evidência de waitlist. Fonte: [Sacra](https://sacra.com/chat/h/18f0d36d-8893-4ea2-8117-8c9a2fa56390/) (análise de terceiros).
- **Linear, Arc, Lovable, Bolt, Warp (waitlist de 2021-2022).** Não encontrei case com números publicados. Não afirmar nada sobre eles sem fonte primária.
- **Indicação com fila.** Blogs de ferramentas de waitlist (LaunchList, Waitlister) citam crescimento de 3.900% com indicação e 1 milhão de cadastros antes do lançamento da Robinhood. São vendedores de ferramenta, **não verificado**.

## 2. Waitlist ajuda ou atrapalha um projeto open source?

- **Ajuda** quando a waitlist é só para o que ainda não existe (app desktop, versão hospedada) e tem um benefício real (acesso antecipado, sem hype).
- **Atrapalha** quando barra o núcleo que o dev quer instalar hoje. Dev de OSS testa em 5 minutos ou esquece. Quem tem `git clone` não espera convite.
- Exemplos de OSS que cresceram por GitHub + X/HN (estrelas de agregadores, datas conflitantes, **usar como ordem de grandeza**):
  - OpenCode: cerca de 120 mil estrelas em março de 2026 (secundário), perto de 193 mil em agosto de 2026 em outra lista.
  - Cline: cerca de 65 mil. Aider: cerca de 48 mil. Superpowers: 177 mil, dado de transcrição de vídeo, **não verificado**.
  - Ghostty: não encontrei fonte sobre o lançamento ou o número de estrelas. Não usar como exemplo sem checar.
  - Fonte geral: [awesome-coding-agent](https://github.com/jqueryscript/awesome-coding-agent), [Medium, comparação de harnesses 2026](https://medium.com/tech-stackups/coding-agent-harness-comparison-2026-claude-code-codex-amp-opencode-gemini-cli-pi-command-ba441d499bc3).
- **Dado mais útil sobre lançamento:** um preprint de novembro de 2025 com 138 lançamentos de repositórios de IA/LLM ([arXiv 2511.04453](https://arxiv.org/abs/2511.04453)) concluiu que o horário da postagem importa mais que a tag "Show HN". Média de cerca de 121 estrelas em 24 horas e 289 em uma semana. É um único preprint sobre IA, então é indicativo, não definitivo.

## 3. Benchmarks e evals como marketing

- Não pesquisei a fundo esse ponto (limite de chamadas). Evidência indireta:
  - O caso Devin mostra que demo escolhida a dedo é desconfiado por quem é técnico. Um eval público com metodologia, dados e falhas expostas é o oposto disso.
  - Helena já tem números públicos (6 rodadas de eval, segundo o commit 71f84d6). Isso é o ativo principal: o diferencial é reproduzível.
- **Recomendação:** cada número ("com vs sem Helena") deve vir com script para reproduzir, versão exata do modelo e de Claude Code, custo e taxa de falha. Mostrar também onde a Helena perde.
- Não encontrei dados de conversão de "eval como marketing". Tratar como **não verificado**.

## 4. Comunidade brasileira e build in public em português

- Build in public tem comunidade ativa em português, principalmente no TabNews ([exemplo](https://www.tabnews.com.br/bokamoto/buildinpublic-o-que-e-e-porque-todo-mundo-esta-montando-seu-saas-em-publico)). Há também Product Launch e Prateleira Dev, versões brasileiras de Product Hunt.
- Um post relata cerca de 10 mil impressões no LinkedIn. Crítica no mesmo conjunto: build in public funciona melhor para dev e indie hacker do que para vender a empresas tradicionais.
- **Leitura:** português ajuda na comunidade local e na credibilidade de "dev brasileiro que construiu isso", mas o público que instala ferramenta de agente de código no GitHub e no HN lê inglês. Inglês para HN, X e GitHub. Português para TabNews, LinkedIn e comunidades de dev no Brasil. Mesmo conteúdo, duas versões, não tradução automática de tudo.
- A utilidade de build in public em português é **plausível mas não verificada** em termos de conversão.

## 5. Preço para ferramenta de dev prosumer

- Cursor (terceiros, valores conflitantes entre fontes): Hobby grátis, Pro 20 dólares/mês, Pro+ 60, Ultra 200, Business 40 por usuário. Uso por créditos. [jetadmin](https://www.jetadmin.io/blog/cursor-pricing-explained-plans-credit-system-and-real-costs-in-2026/), [aicodereview](https://aicodereview.cc/blog/cursor-pricing). Confirmar na página oficial.
- Cline e Roo Code: extensão grátis, paga-se a API direto (BYOK). [pricepertoken](https://pricepertoken.com/coding-assistants/cursor)
- **Sugestão (não verificada, é opinião):** núcleo OSS sempre grátis (MIT ou Apache). Pagar só por o que é hospedado ou de conveniência: app desktop assinado, sincronização de memória entre máquinas, painel de custo e de equipe. Faixa de referência: 10 a 20 dólares/mês. Não cobrar por recurso que já está no repositório, para não perder a confiança da comunidade.

## 6. Stack mínima para waitlist sem backend

- **Tally** (formulário, plano grátis; fonte terciária diz "unlimited"). Dados ficam no painel e saem por webhook. Melhor opção.
- **Formspree** (plano grátis, 50 envios por mês segundo agregador, **não verificado**). Boa se for só enviar e-mail.
- **Hospedagem:** GitHub Pages (grátis) ou Netlify. Página HTML de uma arquivo.
- **Alternativa sem página:** GitHub Discussions ou issue fixa "Desktop waitlist" no próprio repositório. Zero custo, público e já com o público certo.
- **Google Forms** e **ConvertKit**: não verifiquei o plano grátis de 2026.
- **LGPD:** coletar e-mail no Brasil exige finalidade clara e consentimento. Texto curto no formulário com a finalidade e opção de sair.

## 7. Plano de lançamento recomendado (6 a 8 passos, com datas)

Hoje é sexta-feira, 16/10/2026. Semanas em blocos de 7 dias.

1. **Semana 1 (16 a 23/10): porta de entrada do repositório.** README com instalação em um comando, GIF de 30 segundos, tabela "Helena vs Claude Code puro" com números reproduzíveis, link para o eval. Nada de waitlist aqui. Critério: um dev externo instala e roda em menos de 5 minutos.
2. **Semana 2 (24 a 30/10): publicar o eval como artefato.** Script, dados brutos, metodologia, seção de falhas. Post técnico em inglês, versão curta em português para o TabNews.
3. **Semana 2 (até 30/10): waitlist do app desktop, sem backend.** Página do GitHub Pages com Tally, texto de LGPD, e promessa concreta (acesso antecipado e ajuda na configuração, sem contador falso). Indicação opcional que sobe na fila. Meta de sucesso: definir antes do lançamento (exemplo: 300 cadastros em 30 dias, **sugestão, não verificada**).
4. **Semana 3 (terça a quinta, 2 a 5/11): Show HN e Reddit.** Título com problema específico e trade-off ("Show HN: Helena, memória e guardrails para Claude Code. Medimos X e Y; aqui onde perde"). Horário da manhã em fuso americano, segundo o preprint. Responder todos os comentários no primeiro dia.
5. **Mesma semana: X em inglês e LinkedIn/TabNews em português.** Thread curta com o gráfico do eval e o link do repositório. Mesmo dia do HN, não antes.
6. **Semanas 4 a 6 (9 a 27/11): demos de problema real.** Vídeo de 60 segundos em um repositório real, com e sem Helena, com custo e tempo na tela. Responder com conteúdo útil nas threads de quem reclama de custo de token ou de agente que esquece contexto. Não fazer spam.
7. **Semana 7 (até 4/12): decisão de gate.** Se a waitlist e o uso do núcleo justificarem, abrir beta do desktop em lotes para a lista, com acesso por ordem de cadastro e por indicação. Só então definir o preço.
8. **Contínuo: release com eval a cada versão.** Publicar o número junto com o changelog. Medir semanalmente: instalações, estrelas, issues abertas por contribuidores externos, cadastros na waitlist.

## 8. O que NÃO fazer

- Não criar escassez falsa (contador de vagas, "só 50 restantes" sem verdade). Vohra nega que a Superhuman fizesse isso, e a comunidade de dev detecta rápido.
- Não colocar o núcleo OSS atrás de waitlist ou convite.
- Não fazer demo escolhida a dedo (caso Devin). Mostrar também onde a Helena falha.
- Não publicar número sem script para reproduzir.
- Não comprar estrelas nem usar grupos de engajamento. Detecção por GitHub e perda de credibilidade no HN.
- Não postar o mesmo título no HN várias vezes seguidas.
- Não coletar e-mail sem texto de finalidade e consentimento (LGPD).
- Não definir preço antes de haver uso. Não cobrar pelo que já é open source.
- Não lançar o app desktop antes de o instalador do OSS funcionar sozinho.
- Não confiar em números de agregadores de estrelas sem conferir a página do repositório.

## Lacunas da pesquisa

- Sem números primários de conversão de waitlist de nenhuma ferramenta.
- Sem pesquisa específica sobre benchmark como marketing (ficou em evidência indireta).
- Sem postmortem de lançamento no Show HN de 2025-2026 com números.
- Sem verificação de preço atual de Cursor, Warp e Devin na página oficial.

## Fontes principais

- Superhuman: [TechCrunch 2020](https://techcrunch.com/2020/02/28/superhuman-ceo-rahul-vohra-on-waitlists-freemium-pricing-and-future-products/), [Mixergy](https://mixergy.com/interviews/superhuman-with-rahul-vohra/), [AdviceScout](https://advicescout.com/why-superhuman-made-users-do-30-minute-video/)
- Devin: [eesel](https://eesel.ai/blog/cognition-ai-reviews), [fikisipi](https://fikisipi.substack.com/p/short-post-a-look-at-devin-the-ai)
- Warp: [Introducing Warp](https://www.warp.dev/blog/introducing-warp), [It's FOSS](https://itsfoss.com/news/warp-goes-open-source.md)
- Cursor: [Sacra](https://sacra.com/chat/h/18f0d36d-8893-4ea2-8117-8c9a2fa56390/), [jetadmin](https://www.jetadmin.io/blog/cursor-pricing-explained-plans-credit-system-and-real-costs-in-2026/)
- Lançamento e estrelas: [arXiv 2511.04453](https://arxiv.org/abs/2511.04453), [awesome-coding-agent](https://github.com/jqueryscript/awesome-coding-agent)
- Brasil: [TabNews, build in public](https://www.tabnews.com.br/bokamoto/buildinpublic-o-que-e-e-porque-todo-mundo-esta-montando-seu-saas-em-publico)
- Waitlist sem backend: [Tally, via Rocket.new](https://docs.rocket.new/integrations/tally), [Formgrid](https://formgrid.dev/blog/how-to-build-a-waitlist-page-for-your-startup-in-2026)
