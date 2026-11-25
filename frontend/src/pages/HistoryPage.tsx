import { useCallback, type FormEvent } from 'react'
import { useSearchParams } from 'react-router'
import { useLoad } from '../api/hooks'
import { itemsApi } from '../api/items'
import { usePoints } from '../api/points'
import { LoadState, Page } from '../components/Page'
import { CUSTODY_EVENT, formatDateTime } from '../labels'

/** Custody history (RN42, RN43), staff only (RN53). The item's number lives in the address
 * (?item=4), so the link on the listing and F5 both open the right one. */
export function HistoryPage() {
  const [params, setParams] = useSearchParams()
  const itemId = Number(params.get('item'))
  const chosen = Number.isInteger(itemId) && itemId > 0

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const typed = new FormData(event.currentTarget).get('item')
    setParams({ item: String(typed) })
  }

  return (
    <Page title="Histórico do item" subtitle="Tudo o que aconteceu com o item, do registro em diante.">
      {/* the keys start over when the address changes; siblings can't share one, so each has its
          own prefix */}
      <form key={`form-${itemId}`} onSubmit={handleSubmit}>
        <label>
          Número do item
          <input type="number" name="item" min={1} defaultValue={chosen ? itemId : ''} required />
        </label>
        <button type="submit">Ver histórico</button>
      </form>
      {chosen && <HistoryTable key={`table-${itemId}`} itemId={itemId} />}
    </Page>
  )
}

function HistoryTable({ itemId }: { itemId: number }) {
  const load = useCallback(() => itemsApi.history(itemId), [itemId])
  const { data: lines, error, loading } = useLoad(load)
  const { pointName } = usePoints()

  return (
    <>
      <h2>Item nº {itemId}</h2>
      <LoadState loading={loading} error={error} />
      {lines && (
        <table>
          <thead>
            <tr>
              <th>Quando</th>
              <th>O que aconteceu</th>
              <th>Onde</th>
              <th>Responsável</th>
            </tr>
          </thead>
          <tbody>
            {/* the lines never change order or disappear (RN43), so the position is a safe key */}
            {lines.map((line, index) => (
              <tr key={index}>
                <td>{formatDateTime(line.at)}</td>
                <td>{CUSTODY_EVENT[line.event]}</td>
                <td>{pointName(line.collection_point_id)}</td>
                <td>{line.actor_name ?? <em>conta excluída</em>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}
