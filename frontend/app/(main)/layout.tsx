"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { 
  get_token, 
  get_display_name,
  list_conversations,
  delete_conversation,
  type ConversationOut
} from "@/lib/api";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [sidebar_open, setSidebarOpen] = useState(true);
  const [display_name, setDisplayName] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationOut[]>([]);

  useEffect(() => {
    const token = get_token();
    if (!token) {
      router.replace("/auth/login");
      return;
    }
    
    setDisplayName(get_display_name() || "User");
    
    // Fetch conversations for the sidebar history
    list_conversations(token)
      .then(setConversations)
      .catch(() => {});
  }, [router]);

  function handle_new_chat() {
    router.push("/chat");
  }

  function handle_delete_chat(id: string) {
    const token = get_token();
    if (!token) return;
    delete_conversation(token, id).then(() => {
      setConversations((prev) => prev.filter((c) => c.id !== id));
    });
  }

  // Active conversation is only relevant if we are on /c/[id]
  // Since this layout is for non-chat pages, it's null.
  const active_conversation_id = null;

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden relative">
      <Sidebar
        open={sidebar_open}
        on_toggle={() => setSidebarOpen((v) => !v)}
        is_logged_in={!!display_name}
        on_new_chat={handle_new_chat}
        on_delete_chat={handle_delete_chat}
        conversations={conversations}
        active_conversation_id={active_conversation_id}
      />
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
