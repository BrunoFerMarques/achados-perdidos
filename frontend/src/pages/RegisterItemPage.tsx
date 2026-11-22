import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { useCatalog } from '../api/catalog'
import { useAction } from '../api/hooks'
import { itemsApi } from '../api/items'
import { usePoints } from '../api/points'
import type { Option, QuestionInput } from '../api/types'
import { FeedbackLine } from '../components/FeedbackLine'
import { Page } from '../components/Page'

// RN20: from 2 to 5 verification questions (the API answers 422 outside that)
const MIN_QUESTIONS = 2
const MAX_QUESTIONS = 5
const emptyQuestion: QuestionInput = { question: '', answer: '' }

/** One required list field: the first entry is empty, so the browser asks to choose one. */
function OptionSelect(props: {
  label: string
  value: string
  options: Option[]
  onChange: (value: string) => void
}) {
  return (
    <label>
      {props.label}
      <select required value={props.value} onChange={(e) => props.onChange(e.target.value)}>
        <option value="">Escolha…</option>
        {props.options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.name}
          </option>
        ))}
      </select>
    </label>
  )
}

/** Registering a found item: the object, where and when it was found, the counter it goes to,
 * and the questions only the owner can answer. */
export function RegisterItemPage() {
  const { categories, locations, colors } = useCatalog()
  const { points, pointName } = usePoints()
  const [categoryId, setCategoryId] = useState('')
  const [colorId, setColorId] = useState('')
  const [locationId, setLocationId] = useState('')
  const [pointId, setPointId] = useState('')
  const [foundDate, setFoundDate] = useState('')
  const [description, setDescription] = useState('')
  const [questions, setQuestions] = useState([emptyQuestion, emptyQuestion])
  const [itemId, setItemId] = useState<number | null>(null)
  const send = useAction()

  // a new list with one field of one question changed; the others stay as they were
  function updateQuestion(index: number, field: keyof QuestionInput, value: string) {
    setQuestions(questions.map((q, i) => (i === index ? { ...q, [field]: value } : q)))
  }

  function addQuestion() {
    setQuestions([...questions, emptyQuestion])
  }

  function removeQuestion(index: number) {
    setQuestions(questions.filter((_, i) => i !== index))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await send.run(async () => {
      const item = await itemsApi.register({
        // the selects hold text; the API wants numbers
        category_id: Number(categoryId),
        location_id: Number(locationId),
        color_id: Number(colorId),
        collection_point_id: Number(pointId),
        description,
        found_date: foundDate,
        questions,
      })
      setItemId(item.id)
    })
  }

  if (itemId !== null) {
    return (
      <Page title="Item registrado">
        <p className="ok">
          Item nº {itemId} registrado. Leve o objeto ao balcão de {pointName(Number(pointId))}: ele
          só aparece no mural depois que o atendente receber.
        </p>
        <p>
          <Link to="/">Voltar ao mural</Link>
        </p>
      </Page>
    )
  }

  return (
    <Page title="Registrar item achado">
      <form onSubmit={handleSubmit}>
        <OptionSelect label="Categoria" value={categoryId} options={categories.options} onChange={setCategoryId} />
        <OptionSelect label="Cor" value={colorId} options={colors.options} onChange={setColorId} />
        <OptionSelect label="Onde achou" value={locationId} options={locations.options} onChange={setLocationId} />
        <OptionSelect label="Ponto de coleta" value={pointId} options={points} onChange={setPointId} />
        <label>
          Data em que achou
          <input type="date" required value={foundDate} onChange={(e) => setFoundDate(e.target.value)} />
        </label>
        <label>
          Descrição pública
          <textarea
            required
            maxLength={500}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        {/* RN51: what identifies the owner becomes a question, never the public description */}
        <p className="muted">
          Todos vão ler esta descrição. Não coloque o que só o dono saberia (nome, número, marca
          escondida): isso vira uma pergunta abaixo.
        </p>

        <h2>Perguntas de verificação</h2>
        {questions.map((q, index) => (
          <fieldset key={index}>
            <legend>Pergunta {index + 1}</legend>
            <label>
              Pergunta
              <input
                type="text"
                required
                maxLength={500}
                value={q.question}
                onChange={(e) => updateQuestion(index, 'question', e.target.value)}
              />
            </label>
            <label>
              Resposta esperada
              <input
                type="text"
                required
                maxLength={500}
                value={q.answer}
                onChange={(e) => updateQuestion(index, 'answer', e.target.value)}
              />
            </label>
            <button
              type="button"
              disabled={questions.length <= MIN_QUESTIONS}
              onClick={() => removeQuestion(index)}
            >
              Remover
            </button>
          </fieldset>
        ))}
        <button type="button" disabled={questions.length >= MAX_QUESTIONS} onClick={addQuestion}>
          Adicionar pergunta
        </button>

        <FeedbackLine feedback={send.feedback} />
        <button type="submit" disabled={send.pending}>
          {send.pending ? 'Registrando…' : 'Registrar item'}
        </button>
      </form>
    </Page>
  )
}