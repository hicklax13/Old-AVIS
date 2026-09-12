import type { McpTestResult } from '@/hermes'

// ---------------------------------------------------------------------------
// Shared MCP probe cache. Extracted from mcp-tab.tsx so the MCP page and the
// background health checker (store/mcp-health.ts) share ONE cache: a probe is
// a REAL connect/disconnect (stdio servers get spawned!), so neither surface
// may re-probe what the other just learned.
// ---------------------------------------------------------------------------

export const NEEDS_AUTH_RE = /\b(401|unauthorized|forbidden|invalid[_ ]?token|authentication|oauth)\b/i

// Probe results outlive any component: each probe is a real connect/disconnect,
// so re-entering the MCP page (or a background sweep) must not re-probe the
// fleet. Manual refresh / auth / toggle-on bypass the cache.
export const PROBE_TTL_MS = 5 * 60_000

export const probeCache = new Map<string, { at: number; result: McpTestResult }>()
const terminalProbeParks = new Set<string>()

// A probe is only valid for one (profile, exact-config) pair. Keying the cache
// by a fingerprint of the connection-relevant fields — plus the active profile
// — means a same-name edit (url/command/env change) or a same-named server in
// another profile MISSES the cache instead of showing a stale probe.
export const serverFingerprint = (server: Record<string, unknown>): string =>
  JSON.stringify([
    server.enabled,
    server.url,
    server.command,
    server.args,
    server.env,
    server.headers,
    server.transport,
    server.auth,
    server.oauth
  ])

export const probeKey = (name: string, server: Record<string, unknown> | undefined, profileKey: string): string =>
  `${profileKey}::${name}::${serverFingerprint(server ?? {})}`

/** Read a still-fresh cached probe result, or null (miss / expired). */
export function freshProbe(key: string, now = Date.now()): McpTestResult | null {
  const cached = probeCache.get(key)

  return cached && now - cached.at < PROBE_TTL_MS ? cached.result : null
}

/** A failed probe that time alone cannot fix. Needs-auth is terminal even when
 * an older backend omits the additive `retryable` field. */
export function isTerminalProbeFailure(result: McpTestResult): boolean {
  return !result.ok && (result.retryable === false || NEEDS_AUTH_RE.test(result.error ?? ''))
}

/** Record a probe and maintain the exact profile+config sticky-park bit. */
export function rememberProbe(key: string, result: McpTestResult, now = Date.now()): void {
  probeCache.set(key, { at: now, result })

  if (isTerminalProbeFailure(result)) {
    terminalProbeParks.add(key)
  } else {
    terminalProbeParks.delete(key)
  }
}

/** Return a terminal result regardless of the ordinary freshness TTL. */
export function parkedProbe(key: string): McpTestResult | null {
  if (!terminalProbeParks.has(key)) {
    return null
  }

  return probeCache.get(key)?.result ?? null
}

/** Manual retry/auth action explicitly releases a sticky park. */
export function clearProbePark(key: string): void {
  terminalProbeParks.delete(key)
}

/** Classify a finished probe the way the MCP page's status dot does. */
export function classifyProbe(result: McpTestResult): 'error' | 'needs-auth' | 'ok' {
  if (result.ok) {
    return 'ok'
  }

  return NEEDS_AUTH_RE.test(result.error ?? '') ? 'needs-auth' : 'error'
}
