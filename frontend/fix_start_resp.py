import re

with open("frontend/hooks/use_voice_chat.ts", "r") as f:
    content = f.read()

# 1. Add has_started_response_ref
content = content.replace(
    'const waiting_for_response_ref = useRef(false);',
    'const waiting_for_response_ref = useRef(false);\n  const has_started_response_ref = useRef(false);'
)

# 2. Reset has_started_response_ref to false in reset_response_buffers (wait, reset_response_buffers doesn't exist? Oh it does)
# Actually let's just put it in reset_turn_buffers and do_commit
content = content.replace(
    'waiting_for_response_ref.current = true;',
    'waiting_for_response_ref.current = true;\n    has_started_response_ref.current = false;'
)

content = content.replace(
    'waiting_for_response_ref.current = false;',
    'waiting_for_response_ref.current = false;\n    has_started_response_ref.current = false;'
)

# 3. Update arm_turn_timeout
# Right now it has:
# const arm_turn_timeout = useCallback(() => {
#    if (!waiting_for_response_ref.current) return;
#    clear_turn_timeout();

content = content.replace(
    'if (!waiting_for_response_ref.current) return;',
    'if (!waiting_for_response_ref.current || has_started_response_ref.current) return;'
)

# 4. In assistant.text.delta and output_audio.chunk, set has_started_response_ref.current = true and clear the timeout
content = content.replace(
    'case "assistant.text.delta": {\n          arm_turn_timeout();',
    'case "assistant.text.delta": {\n          has_started_response_ref.current = true;\n          clear_turn_timeout();'
)

content = content.replace(
    'case "output_audio.chunk": {\n          arm_turn_timeout();',
    'case "output_audio.chunk": {\n          has_started_response_ref.current = true;\n          clear_turn_timeout();'
)

with open("frontend/hooks/use_voice_chat.ts", "w") as f:
    f.write(content)
