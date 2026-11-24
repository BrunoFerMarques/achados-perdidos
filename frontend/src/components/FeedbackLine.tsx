import type { Feedback } from '../api/hooks'

/** Mostra o resultado de uma ação. Fica sempre montado pro leitor de tela anunciar o que
 * aparecer (sucesso como status, erro como alerta). */
export function FeedbackLine({ feedback }: { feedback: Feedback | null }) {
  return (
    <div aria-live="polite">
      {feedback && (
        <p role={feedback.ok ? 'status' : 'alert'} className={feedback.ok ? 'ok' : 'error'}>
          {feedback.text}
        </p>
      )}
    </div>
  )
}
