export const startStream = (text: string) => {
  return new EventSource(`/api/text-chat/char-stream?text=${encodeURIComponent(text)}`)
}