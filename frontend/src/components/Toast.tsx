interface Props {
  message: string | null
}

// Transient toast notification (bottom-center), matching the prototype's #toast.
export default function Toast({ message }: Props) {
  return (
    <div id="toast" style={{ display: message ? 'block' : 'none' }}>
      {message}
    </div>
  )
}
