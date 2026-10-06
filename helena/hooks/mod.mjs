// Helena mod (Claude Code 2.1.287+): context, cost and savings drawn in the interface, not injected into the prompt,
// so watching them costs the model nothing.
//  - band above the prompt: context size, % of the window, session cost, what trim.js kept out of the context
//  - spinner: a warning from 120k context (router.js then skips its 120k prompt warning; 250k/500k stay, they ask for HANDOFF.md)
//  - /painel: context by category, what trim.js blocked, Helena's own background spending
// Without mods, statusline.js and router.js do the same job.

const WARN = 120e3, HEAVY = 250e3
const k = n => (n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : Math.round(n / 1000) + 'k')
let usage = null, blocks = [], pane = false

async function helenaDir($) {
  return ((await $.env.get('USERPROFILE')) || (await $.env.get('HOME'))) + '/.helena'
}

async function jsonl($, file) {
  try {
    return (await $.fs.read(file)).split('\n').flatMap(l => { try { return [JSON.parse(l)] } catch { return [] } })
  } catch { return [] }
}

async function refresh($) {
  usage = await $.session.usage()
  const id = await $.session.id()
  blocks = (await jsonl($, (await helenaDir($)) + '/trim.jsonl')).filter(b => b.session === id)
}

function tone(n) { return n >= HEAVY ? 'red' : n >= WARN ? 'yellow' : undefined }

export function register(on) {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'painel', description: 'Helena: context by category, what was blocked, what she spent' })
    // router.js reads this flag and leaves the 120k warning to the interface
    await $.fs.write((await helenaDir($)) + '/warnings/' + (await $.session.id()) + '-mod', '')
    await refresh($)
    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    await refresh($)
    $.ui.invalidate('ui.render')
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)  // a survey holds the band; yield to it
    const others = await next(e)
    const c = usage && usage.context
    if (!c || !c.tokens) return others
    const { Box, Text } = $.ui.resolve(e)
    const pct = c.percent ?? (c.tokens / c.window) * 100
    const bar = '▓'.repeat(Math.round(pct / 10)) + '░'.repeat(10 - Math.round(pct / 10))
    const saved = blocks.reduce((s, b) => s + (b.tokens || 0), 0)
    const parts = [
      Text({ dimColor: true, children: ['helena · ctx '] }),
      Text({ color: tone(c.tokens), bold: c.tokens >= WARN, children: [k(c.tokens) + ' ' + bar + ' ' + Math.round(pct) + '%'] }),
    ]
    if (usage.cost) parts.push(Text({ dimColor: true, children: [' · $' + usage.cost.usd.toFixed(2)] }))
    if (blocks.length) parts.push(Text({ dimColor: true, children: [' · trim ' + blocks.length + '×' + (saved ? ' −' + k(saved) : '')] }))
    const mine = Box({ flexDirection: 'row', children: parts })
    return others ? Box({ flexDirection: 'column', children: [others, mine] }) : mine
  })

  on('ui.render', { component: 'Spinner' }, async ($, e, next) => {
    const t = usage && usage.context && usage.context.tokens
    if (!t || t < WARN) return next(e)
    const tip = t >= HEAVY ? ': HANDOFF.md + /clear' : ': /clear soon'
    return next({ ...e, props: { ...e.props, suffix: (e.props.suffix || '') + ' · ctx ' + k(t) + tip } })
  })

  on('command.run', { command: 'painel' }, async ($) => {
    pane = !pane
    if (pane) await $.ui.open({ id: 'helena', title: 'Helena', closeOnEscape: true })
    else await $.ui.close({ id: 'helena' })
    return { text: pane ? 'painel aberto (esc fecha)' : 'painel fechado' }
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== 'helena') return next(e)
    const { Box, Text } = $.ui.resolve(e)
    const full = await $.session.usage({ breakdown: 'summary' })
    const b = full.context.breakdown
    const spent = await jsonl($, (await helenaDir($)) + '/ledger.jsonl')
    const row = (label, value, color) => Box({ flexDirection: 'row', columnGap: 1, children: [
      Text({ children: [String(value).padStart(7)], color }), Text({ dimColor: true, wrap: 'truncate-end', children: [label] })] })
    const head = t => Text({ bold: true, children: [t] })
    const kids = [head('contexto · relido a cada mensagem')]
    if (b) {
      for (const cat of b.categories.filter(x => x.tokens > 0).sort((x, y) => y.tokens - x.tokens).slice(0, 8))
        kids.push(row(cat.name, k(cat.tokens)))
      kids.push(row('total de ' + k(b.maxTokens), k(b.totalTokens), tone(b.totalTokens)))
    } else kids.push(Text({ dimColor: true, children: ['sem dados ainda'] }))
    kids.push(Text({ children: [' '] }), head('barrado pelo trim.js nesta sessão'))
    if (blocks.length) for (const x of blocks.slice(-6)) kids.push(row(x.what, x.tokens ? '−' + k(x.tokens) : '—'))
    else kids.push(Text({ dimColor: true, children: ['nada até agora'] }))
    const usd = spent.reduce((s, x) => s + (x.cost || 0), 0)
    kids.push(Text({ children: [' '] }), head('Helena em segundo plano (Haiku)'),
      row(spent.length + ' chamadas no total', '$' + usd.toFixed(2)))
    if (full.cost) kids.push(row('esta sessão', '$' + full.cost.usd.toFixed(2)))
    return Box({ flexDirection: 'column', padding: 1, children: kids })
  })
}
