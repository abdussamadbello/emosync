import re

with open("frontend/hooks/use_voice_chat.ts", "r") as f:
    content = f.read()

# Add a boolean ref to track if we're waiting for the backend response
# Let's insert it alongside the other refs
content = content.replace(
    'const turn_timeout_ref = useRef<number | null>(null);',
    'const turn_timeout_ref = useRef<number | null>(null);\n  const waiting_for_response_ref = useRef(false);'
)

# Update arm_turn_timeout to only arm if we are waiting for a response
content = content.replace(
    'const arm_turn_timeout = useCallback(() => {',
    'const arm_turn_timeout = useCallback(() => {\n    if (!waiting_for_response_ref.current) return;'
)

# In do_commit, set waiting_for_response_ref = true
content = content.replace(
    'reset_response_buffers();',
    'reset_response_buffers();\n    waiting_for_response_ref.current = true;'
)

# In turn.done, set waiting_for_response_ref = false
content = content.replace(
    'case "turn.done":',
    'case "turn.done":\n          waiting_for_response_ref.current = false;'
)

# In output_audio.done, also set waiting_for_response_ref = false (just be safe, though turn.done should do it)
content = content.replace(
    'case "output_audio.done":',
    'case "output_audio.done":\n          waiting_for_response_ref.current = false;'
)

# In recover_from_stalled_turn, set to false
content = content.replace(
    'reset_turn_buffers();',
    'reset_turn_buffers();\n    waiting_for_response_ref.current = false;'
)

# In disconnect, set to false
content = content.replace(
    'clear_turn_timeout();\n    stop_live_playback();',
    'clear_turn_timeout();\n    waiting_for_response_ref.current = false;\n    stop_live_playback();'
)

with open("frontend/hooks/use_voice_chat.ts", "w") as f:
    f.write(content)
