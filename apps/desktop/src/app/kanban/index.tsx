import type * as React from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { cn } from '@/lib/utils'

import { PAGE_INSET_X } from '../layout-constants'

// The kanban board is served by the Mission Control dashboard (always-on
// LaunchAgent `com.hermes.dashboard` on :8787) which reads ~/.hermes/kanban.db.
// Both this desktop view and the dashboard's TASKS tab hit the SAME endpoint,
// so they render the same live board.
const KANBAN_API = 'http://127.0.0.1:8787/api/kanban'

const COLUMN_ACCENT: Record<string, string> = {
  todo: '#7c6cff',
  running: '#00e5ff',
  review: '#ffb22e',
  blocked: '#ff3b5c',
  done: '#1bff9b',
  archived: '#5b7a86',
  other: '#94a3b8'
}

interface KanbanCard {
  id: string
  title: string
  body?: string
  assignee?: string
  status: string
  priority?: number
  result?: string
  error?: string
}

interface KanbanColumn {
  key: string
  label: string
  cards: KanbanCard[]
}

interface KanbanBoard {
  columns: KanbanColumn[]
  assignees: string[]
  error?: string
}

type KanbanViewProps = React.ComponentProps<'section'>

export function KanbanView({ className, ...props }: KanbanViewProps) {
  const [board, setBoard] = useState<KanbanBoard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [assignee, setAssignee] = useState('')
  const [adding, setAdding] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const load = useCallback(async () => {
    try {
      const res = await fetch(KANBAN_API, { cache: 'no-store' })
      const data = (await res.json()) as KanbanBoard
      setBoard(data)
      setError(data.error ?? null)
    } catch {
      setError('Cannot reach the AVIS dashboard service (com.hermes.dashboard) on 127.0.0.1:8787.')
    }
  }, [])

  useEffect(() => {
    void load()
    const tick = () => {
      timer.current = setTimeout(() => {
        void load().then(tick)
      }, 5000)
    }
    tick()
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [load])

  const addCard = useCallback(async () => {
    const trimmed = title.trim()
    if (!trimmed) return
    setAdding(true)
    try {
      const res = await fetch(KANBAN_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: trimmed, assignee: assignee.trim() })
      })
      const data = (await res.json()) as { ok?: boolean; error?: string }
      if (data.ok) {
        setTitle('')
        setAssignee('')
        await load()
      } else {
        setError(data.error ?? 'Failed to add card')
      }
    } catch {
      setError('Failed to add card')
    } finally {
      setAdding(false)
    }
  }, [title, assignee, load])

  const total = board?.columns.reduce((sum, col) => sum + col.cards.length, 0) ?? 0

  const inputClass =
    'rounded-md border border-(--ui-stroke-tertiary) bg-transparent px-3 py-2 text-sm text-foreground outline-none focus:border-foreground'

  return (
    <section className={cn('flex h-full min-h-0 flex-col gap-3 pt-3', PAGE_INSET_X, className)} {...props}>
      <header>
        <h1 className="text-base font-semibold text-foreground">Kanban</h1>
        <p className="text-(--ui-text-secondary) text-xs">
          AVIS agent task board · {total} card{total === 1 ? '' : 's'}
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <input
          className={cn(inputClass, 'min-w-40 flex-1')}
          maxLength={120}
          onChange={event => setTitle(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter') void addCard()
          }}
          placeholder="New task title…"
          value={title}
        />
        <input
          className={cn(inputClass, 'w-44')}
          list="kanban-assignees"
          maxLength={40}
          onChange={event => setAssignee(event.target.value)}
          placeholder="assignee (optional)"
          value={assignee}
        />
        <datalist id="kanban-assignees">
          {(board?.assignees ?? []).map(name => (
            <option key={name} value={name} />
          ))}
        </datalist>
        <button
          className="rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background) px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-(--ui-control-hover-background) disabled:opacity-40"
          disabled={adding || !title.trim()}
          onClick={() => void addCard()}
          type="button"
        >
          Add card
        </button>
      </div>

      {error && <div className="text-xs text-red-400">{error}</div>}

      <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto pb-2">
        {(board?.columns ?? []).map(col => {
          const accent = COLUMN_ACCENT[col.key] ?? '#00e5ff'
          return (
            <div
              className="flex w-60 shrink-0 flex-col rounded-lg border border-(--ui-stroke-tertiary)"
              key={col.key}
            >
              <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-3 py-2">
                <span className="text-(--ui-text-secondary) text-xs font-semibold uppercase tracking-wider">
                  {col.label}
                </span>
                <span className="text-xs font-semibold" style={{ color: accent }}>
                  {col.cards.length}
                </span>
              </div>
              <div className="flex min-h-10 flex-1 flex-col gap-2 overflow-y-auto p-2">
                {col.cards.length === 0 && (
                  <div className="text-(--ui-text-secondary) py-3 text-center text-[11px] opacity-50">—</div>
                )}
                {col.cards.map(card => (
                  <div
                    className="rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background) p-2.5"
                    key={card.id}
                    style={{ borderLeft: `3px solid ${accent}` }}
                  >
                    <div className="text-[13px] font-medium text-foreground">{card.title}</div>
                    <div className="text-(--ui-text-secondary) mt-1.5 flex flex-wrap gap-2 text-[10px] uppercase tracking-wide">
                      {card.assignee && <span style={{ color: accent }}>▸ {card.assignee}</span>}
                      {card.priority ? <span>P{card.priority}</span> : null}
                      <span>{card.status}</span>
                    </div>
                    {card.body && <div className="text-(--ui-text-secondary) mt-1.5 text-[11px]">{card.body}</div>}
                    {card.result && <div className="mt-1.5 text-[11px] text-emerald-400/80">✓ {card.result}</div>}
                    {card.error && <div className="mt-1.5 text-[11px] text-red-400/80">⚠ {card.error}</div>}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
