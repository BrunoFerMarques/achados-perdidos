import type { Option } from '../api/types'

/** One required list field: the first entry is empty, so the browser asks to choose one. */
export function OptionSelect(props: {
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
