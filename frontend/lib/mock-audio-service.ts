const MOCK_TRANSCRIPTIONS = [
    "I've been feeling a bit overwhelmed lately.",
    "I'm doing okay, just thinking about things.",
    "I had a really good day today actually.",
  ];
  
  let index = 0;
  
  export function mock_speech_to_text(_audio_blob: Blob): Promise<string> {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(MOCK_TRANSCRIPTIONS[index % MOCK_TRANSCRIPTIONS.length]);
        index++;
      }, 800);
    });
  }
  
  export function mock_text_to_speech(text: string): Promise<void> {
    return new Promise((resolve) => {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      utterance.onend = () => resolve();
      speechSynthesis.speak(utterance);
    });
  }