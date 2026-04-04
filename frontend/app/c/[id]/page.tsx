"use client";

import { useParams } from "next/navigation";
import { ChatView } from "@/components/chat_view";

/**
 * Per-conversation page at /c/{id}.
 * Reads the conversation id from the URL and passes it to ChatView, which
 * loads the message history on mount and resumes the session.
 */
export default function ConversationPage() {
  const { id } = useParams<{ id: string }>();
  return <ChatView initial_conversation_id={id} />;
}
