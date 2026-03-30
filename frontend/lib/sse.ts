/** A parsed SSE event with its event name and decoded JSON data. */
export interface SseEvent {
  event: string;
  data: Record<string, unknown>;
}

/**
 * Parses a raw SSE block (the text between two blank lines) into an SseEvent.
 * Returns null if the block cannot be parsed.
 */
function parse_sse_block(block: string): SseEvent | null {
  let event = "message";
  let raw_data = "";

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      raw_data = line.slice("data:".length).trim();
    }
  }

  if (!raw_data) return null;

  try {
    const data = JSON.parse(raw_data) as Record<string, unknown>;
    return { event, data };
  } catch {
    return null;
  }
}

/**
 * Reads a Server-Sent Events response body and yields typed SseEvent objects.
 * Works with fetch() responses — use this instead of EventSource so that the
 * Authorization header can be included in the request.
 */
export async function* read_sse_stream(
  response: Response
): AsyncGenerator<SseEvent> {
  if (!response.body) return;

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by a blank line (\n\n)
      const blocks = buffer.split("\n\n");
      // Last entry is an incomplete block — keep it in the buffer
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        if (!block.trim()) continue;
        const evt = parse_sse_block(block);
        if (evt) yield evt;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
