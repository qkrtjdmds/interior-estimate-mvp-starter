import type { ReactNode } from 'react'

export default function ApiState({ title, message, action }: { title: string; message: string; action?: ReactNode }) {
  return (
    <div className="api-state" role="status">
      <strong>{title}</strong>
      <p>{message}</p>
      {action}
    </div>
  )
}

