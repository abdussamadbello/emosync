import re

with open("frontend/hooks/use_voice_chat.ts", "r") as f:
    content = f.read()

# 1. Remove speak_fallback definition
content = re.sub(r'function speak_fallback.*?window\.speechSynthesis\.speak\(utterance\);\n}\n*', '', content, flags=re.DOTALL)

# 2. Remove window.speechSynthesis.cancel() from disconnect
content = content.replace('window.speechSynthesis.cancel();\n', '')

# 3. Replace speak_fallback calls
# For: speak_fallback(fallback_text, on_audio_ended);
content = content.replace(
    'speak_fallback(fallback_text, on_audio_ended);',
    'window.setTimeout(on_audio_ended, Math.max(word_count * 120, 500) + 500);'
)

# For: speak_fallback(text, on_audio_ended);
content = content.replace(
    'speak_fallback(text, on_audio_ended);',
    'window.setTimeout(on_audio_ended, Math.max(word_count * 120, 500) + 500);'
)

with open("frontend/hooks/use_voice_chat.ts", "w") as f:
    f.write(content)
