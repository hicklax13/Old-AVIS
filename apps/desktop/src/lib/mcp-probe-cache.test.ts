import { describe, expect, it } from 'vitest'

import type { McpTestResult } from '@/hermes'

import {
  classifyProbe,
  clearProbePark,
  freshProbe,
  isTerminalProbeFailure,
  NEEDS_AUTH_RE,
  parkedProbe,
  PROBE_TTL_MS,
  probeCache,
  probeKey,
  rememberProbe
} from './mcp-probe-cache'

const result = (over: Partial<McpTestResult> = {}): McpTestResult => ({ ok: true, tools: [], ...over })

describe('classifyProbe', () => {
  it('classifies a successful probe as ok', () => {
    expect(classifyProbe(result())).toBe('ok')
  })

  it.each([
    'HTTP 401 Unauthorized',
    'invalid_token: The access token expired',
    'OAuth authorization required',
    'authentication failed'
  ])('classifies "%s" as needs-auth', error => {
    expect(classifyProbe(result({ ok: false, error }))).toBe('needs-auth')
  })

  it('classifies other failures as error', () => {
    expect(classifyProbe(result({ ok: false, error: 'ECONNREFUSED 127.0.0.1:3845' }))).toBe('error')
  })

  it('classifies a failure without an error string as error', () => {
    expect(classifyProbe(result({ ok: false }))).toBe('error')
  })
})

describe('probeKey', () => {
  it('scopes by profile, name, and connection-relevant config', () => {
    const server = { url: 'https://api.githubcopilot.com/mcp/' }
    expect(probeKey('github', server, 'default')).not.toBe(probeKey('github', server, 'work'))
    expect(probeKey('github', server, 'default')).not.toBe(probeKey('gh2', server, 'default'))
    expect(probeKey('github', server, 'default')).not.toBe(
      probeKey('github', { url: 'https://other.example/mcp' }, 'default')
    )
    expect(probeKey('github', server, 'default')).not.toBe(probeKey('github', { ...server, enabled: false }, 'default'))
  })

  it('ignores non-connection fields so cosmetic edits still hit the cache', () => {
    const server = { url: 'https://api.example/mcp' }
    expect(probeKey('s', server, 'default')).toBe(probeKey('s', { ...server, description: 'hi' }, 'default'))
  })
})

describe('freshProbe', () => {
  it('returns a cached result inside the TTL and null after it', () => {
    const key = probeKey('ttl-test', { url: 'https://x' }, 'default')
    const cached = result()
    probeCache.set(key, { at: 1_000, result: cached })

    expect(freshProbe(key, 1_000 + PROBE_TTL_MS - 1)).toBe(cached)
    expect(freshProbe(key, 1_000 + PROBE_TTL_MS)).toBeNull()
    expect(freshProbe('missing', 0)).toBeNull()
    probeCache.delete(key)
  })
})

describe('terminal probe parking', () => {
  const key = probeKey('terminal', { url: 'https://x' }, 'default')

  it('keeps terminal failures parked after the ordinary cache TTL', () => {
    const failed = result({ ok: false, error: 'OAuth authentication required', retryable: false })
    rememberProbe(key, failed, 1_000)

    expect(freshProbe(key, 1_000 + PROBE_TTL_MS)).toBeNull()
    expect(parkedProbe(key)).toBe(failed)

    clearProbePark(key)
    expect(parkedProbe(key)).toBeNull()
    probeCache.delete(key)
  })

  it('does not park transient failures and clears a park on success', () => {
    const retryable = result({ ok: false, error: 'connection refused', retryable: true })
    rememberProbe(key, retryable, 1_000)
    expect(parkedProbe(key)).toBeNull()

    rememberProbe(key, result(), 2_000)
    expect(parkedProbe(key)).toBeNull()
    probeCache.delete(key)
  })

  it('treats needs-auth from an older backend as terminal', () => {
    expect(isTerminalProbeFailure(result({ ok: false, error: 'OAuth authorization required' }))).toBe(true)
  })
})

describe('NEEDS_AUTH_RE', () => {
  it('does not match unrelated failure text', () => {
    expect(NEEDS_AUTH_RE.test('connection timed out after 60000ms')).toBe(false)
  })
})
