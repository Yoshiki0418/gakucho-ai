export const startStream = (text: string) => {
  return new EventSource(`/api/text-chat/char-stream-agent?text=${encodeURIComponent(text)}`)
}