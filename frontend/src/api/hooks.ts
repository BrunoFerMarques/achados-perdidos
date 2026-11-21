import { useCallback, useEffect, useRef, useState } from 'react'
import { errorText } from './client'

/** Loads once on mount, and again on reload(). `load` must be stable (a module function or a
 * useCallback), or it loads on every render. An answer that arrives after a newer request is
 * dropped, so the screen never shows the older one. */
export function useLoad<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const latest = useRef(0)

  // the state only changes when the request answers, never synchronously inside the effect
  const run = useCallback(() => {
    const request = ++latest.current
    const current = () => request === latest.current
    load()
      .then((value) => {
        if (!current()) return
        setData(value)
        setError('')
      })
      .catch((err: unknown) => {
        if (current()) setError(errorText(err))
      })
      .finally(() => {
        if (current()) setLoading(false)
      })
  }, [load])

  useEffect(run, [run])

  const reload = useCallback(() => {
    setLoading(true)
    run()
  }, [run])

  return { data, error, loading, reload }
}

export type Feedback = { ok: boolean; text: string }

/** One action at a time (approve, cancel, send...): `pending` disables the buttons while it
 * runs, and `feedback` holds the success text or the API's error. run() says if it worked. */
export function useAction() {
  const [pending, setPending] = useState(false)
  const [feedback, setFeedback] = useState<Feedback | null>(null)

  async function run(action: () => Promise<unknown>, success?: string): Promise<boolean> {
    setPending(true)
    setFeedback(null)
    try {
      await action()
      if (success) setFeedback({ ok: true, text: success })
      return true
    } catch (err) {
      setFeedback({ ok: false, text: errorText(err) })
      return false
    } finally {
      setPending(false)
    }
  }

  return { run, pending, feedback }
}
