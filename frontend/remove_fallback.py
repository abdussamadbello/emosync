with open("frontend/hooks/use_voice_chat.ts", "r") as f:
    t = f.read()

t = t.replace('async (fallback_text: string) => {', 'async () => {')
t = t.replace('void play_legacy_audio(full_text_ref.current);', 'void play_legacy_audio();')

with open("frontend/hooks/use_voice_chat.ts", "w") as f:
    f.write(t)
