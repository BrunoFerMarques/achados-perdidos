import { useCallback, useEffect, useRef, useState } from 'react'
import { errorText } from './client'

/** Carrega quando a tela abre e de novo no reload(). O `load` tem que ser estável (função de
 * módulo ou useCallback), senão carrega a cada render. Se uma resposta antiga chegar depois de
 * uma mais nova, ela é ignorada. */
export function useLoad<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const latest = useRef(0)

  // só mexe no estado quando a resposta chega, nunca direto dentro do efeito
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

/** Uma ação por vez (aprovar, cancelar, enviar...). `pending` desabilita os botões enquanto
 * roda e `feedback` guarda a mensagem de sucesso ou o erro. O run() devolve se deu certo. */
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
