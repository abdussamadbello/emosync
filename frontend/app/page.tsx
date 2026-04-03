import { ChatView } from "@/components/chat_view";

/**
 * Root page — renders a blank new-chat session.
 * When the user sends their first message, a conversation is created and the
 * URL updates to /c/{id} via replaceState without a component remount.
 */
export default function Home() {
  return <ChatView />;
}
