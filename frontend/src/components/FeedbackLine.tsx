import type { Feedback } from '../api/hooks'

/** The outcome of an action. Always mounted, so screen readers announce what appears in it: a
 * success as a status, an error as an alert. */
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
