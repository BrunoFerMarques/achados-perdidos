import { useEffect, useState } from 'react'
import { useLocation } from 'react-router'
import { api } from './client'
import type { Notification } from './types'

export const notificationsApi = {
  // os avisos dos relatos de quem está logado, do mais novo para o mais antigo
  mine: () => api<Notification[]>('/v1/notifications'),
  markRead: (id: number) => api<Notification>(`/v1/notifications/${id}/read`, { method: 'PATCH' }),
}

// a tela de avisos dispara este evento depois de marcar como lido, e o sino conta de novo
const CHANGED = 'notifications-changed'

export function announceNotificationsChanged() {
  window.dispatchEvent(new Event(CHANGED))
}

/** Quantos avisos estão sem ler. Conta de novo a cada troca de tela e quando a tela de avisos
 * marca um como lido. Não é em tempo real: um item que chega agora aparece na próxima troca. */
export function useUnreadCount(enabled: boolean): number {
  const { pathname } = useLocation()
  const [count, setCount] = useState(0)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    const bump = () => setVersion((v) => v + 1)
    window.addEventListener(CHANGED, bump)
    return () => window.removeEventListener(CHANGED, bump)
  }, [])

  useEffect(() => {
    if (!enabled) return
    let current = true
    notificationsApi
      .mine()
      .then((list) => {
        if (current) setCount(list.filter((n) => n.read_at === null).length)
      })
      // o sino é só um atalho: se falhar, fica sem número, e a tela de avisos mostra o erro
      .catch(() => {})
    return () => {
      current = false
    }
  }, [enabled, pathname, version])

  return enabled ? count : 0
}
