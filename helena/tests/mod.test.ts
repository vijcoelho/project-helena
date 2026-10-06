import { expect, mock, test } from 'claude-code/testing'

test('band shows context, cost and what trim.js blocked; spinner warns from 120k', async ($, on) => {
  mock.env(on, { USERPROFILE: 'C:/u' })
  on('session.id', () => ({ value: 's1' }))
  on('session.usage', () => ({ value: { context: { tokens: 130000, window: 200000, percent: 65 }, rateLimits: [], cost: { usd: 1.234 } } }))
  on('fs.read', () => ({ value: '{"session":"s1","what":"package-lock.json","tokens":20000}\n{"session":"other","what":"x","tokens":5}\n' }))
  on('fs.write', () => ({ value: undefined }))
  on('command.register', () => ({ value: undefined }))
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  // stands for Claude Code's own drawing; echoes the spinner suffix so the test can read it
  on('ui.render', ($, e) => ({ type: 'Text', props: {}, children: [e.props.suffix || 'engine'] }))

  await $.session.start({ source: 'startup', cwd: '.' })

  const band = await $.ui.mount({ plugin: 'helena', component: 'AbovePrompt', surface: 'terminal', viewport: { columns: 100, rows: 30 },
    props: { hasSurvey: false, isWorking: false, maxRows: 4, bodyColumns: 100, scroll: { offset: 0, bodyRows: 4 }, view: {} } })
  expect(await band.find({ type: 'Text', text: /^130k ▓+░+ 65%$/ })).toBeDefined()
  expect(await band.find({ type: 'Text', text: ' · $1.23' })).toBeDefined()
  expect(await band.find({ type: 'Text', text: ' · trim 1× −20k' })).toBeDefined()

  const spin = await $.ui.mount({ plugin: 'helena', component: 'Spinner', surface: 'terminal', viewport: { columns: 100, rows: 30 }, props: { message: 'Thinking' } })
  expect(await spin.find({ type: 'Text', text: ' · ctx 130k: /clear soon' })).toBeDefined()
})

test('/painel opens a pane with context by category and Helena spending', async ($, on) => {
  mock.env(on, { USERPROFILE: 'C:/u' })
  on('session.id', () => ({ value: 's1' }))
  on('session.usage', () => ({ value: { context: { tokens: 50000, window: 200000, breakdown: {
    categories: [{ name: 'Messages', tokens: 30000 }, { name: 'System tools', tokens: 20000 }, { name: 'Free space', tokens: 0 }],
    totalTokens: 50000, maxTokens: 200000 } }, rateLimits: [], cost: { usd: 0.5 } } }))
  on('fs.read', ($, e) => ({ value: e.path.endsWith('ledger.jsonl') ? '{"cost":0.02}\n{"cost":0.03}\n' : '' }))
  on('ui.open', () => ({ value: undefined }))

  expect((await $.command.run({ command: 'painel', args: '' })).text).toBe('painel aberto (esc fecha)')
  const pane = await $.ui.mount({ plugin: 'helena', component: 'Pane', requestId: 'helena', surface: 'terminal',
    viewport: { columns: 100, rows: 30 },
    props: { title: 'Helena', isFocused: true, bodyColumns: 60, placement: 'inline', scroll: { offset: 0, bodyRows: 20 }, view: {} } })
  expect(await pane.find({ type: 'Text', text: 'Messages' })).toBeDefined()
  expect(await pane.find({ type: 'Text', text: '    30k' })).toBeDefined()
  expect(await pane.find({ type: 'Text', text: '2 chamadas no total' })).toBeDefined()
  expect(await pane.find({ type: 'Text', text: '  $0.05' })).toBeDefined()
})
