import { useState, type FormEvent } from 'react'
import { useCatalog } from '../api/catalog'
import { useAction, useLoad } from '../api/hooks'
import { lostReportsApi } from '../api/lostReports'
import type { LostReport } from '../api/types'
import { FeedbackLine } from '../components/FeedbackLine'
import { OptionSelect } from '../components/OptionSelect'
import { LoadState, Page } from '../components/Page'
import { formatDate, LOST_REPORT_STATUS } from '../labels'

/** Quem perdeu algo conta o que foi, onde e quando. Quando um item parecido chega a um balcão,
 * o sistema compara com os relatos ativos e avisa o dono (RN30). Embaixo, os relatos da pessoa. */
export function LostReportsPage() {
  const { categories, locations, colors } = useCatalog()
  const { data: reports, error, loading, reload } = useLoad(lostReportsApi.mine)
  const [categoryId, setCategoryId] = useState('')
  const [colorId, setColorId] = useState('')
  const [locationId, setLocationId] = useState('')
  const [lostDate, setLostDate] = useState('')
  const [description, setDescription] = useState('')
  const send = useAction()
  const action = useAction()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const done = await send.run(
      () =>
        lostReportsApi.create({
          // os selects guardam texto; a API quer números
          category_id: Number(categoryId),
          location_id: Number(locationId),
          color_id: Number(colorId),
          description,
          lost_date: lostDate,
        }),
      'Relato registrado. Avisaremos aqui se um item parecido chegar a um balcão.',
    )
    if (!done) return
    // limpa o formulário para um próximo relato e mostra o novo na lista
    setCategoryId('')
    setColorId('')
    setLocationId('')
    setLostDate('')
    setDescription('')
    reload()
  }

  // encerrar não tem volta (o relato para de gerar avisos), então pergunta antes
  async function close(report: LostReport) {
    if (!window.confirm(`Encerrar o relato "${report.description}"? Você não será mais avisado.`)) return
    const done = await action.run(
      () => lostReportsApi.close(report.id),
      'Relato encerrado. Que bom se você achou!',
    )
    if (done) reload()
  }

  return (
    <Page title="Perdi algo" subtitle="Conte o que perdeu. Quando um item parecido chegar a um balcão, você é avisado.">
      <form onSubmit={handleSubmit}>
        <OptionSelect label="Categoria" value={categoryId} options={categories.options} onChange={setCategoryId} />
        <OptionSelect label="Cor" value={colorId} options={colors.options} onChange={setColorId} />
        <OptionSelect label="Onde perdeu" value={locationId} options={locations.options} onChange={setLocationId} />
        <label>
          Data em que perdeu
          <input type="date" required value={lostDate} onChange={(e) => setLostDate(e.target.value)} />
        </label>
        <label>
          Descrição
          <textarea required maxLength={500} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <p className="muted">Só você vê o seu relato. Ele vale por 60 dias.</p>
        <FeedbackLine feedback={send.feedback} />
        <button type="submit" disabled={send.pending}>
          {send.pending ? 'Registrando…' : 'Registrar relato'}
        </button>
      </form>

      <h2>Meus relatos</h2>
      <FeedbackLine feedback={action.feedback} />
      <LoadState loading={loading} error={error} />
      {reports?.length === 0 && <p>Você ainda não relatou nenhuma perda.</p>}
      <ul className="grid">
        {reports?.map((report) => (
          <li key={report.id} className="card">
            <span className="chip">{categories.nameOf(report.category_id)}</span>
            <strong>{report.description}</strong>
            <span>{LOST_REPORT_STATUS[report.status]}</span>
            <span className="muted">
              {colors.nameOf(report.color_id)} · perdido em {locations.nameOf(report.location_id)} em{' '}
              {formatDate(report.lost_date)}
            </span>
            {/* só um relato ativo pode ser encerrado; encerrado e vencido são finais */}
            {report.status === 'ativo' && (
              <div className="actions">
                <button type="button" disabled={action.pending} onClick={() => close(report)}>
                  Encerrar
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </Page>
  )
}
