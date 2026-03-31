# **EmoSync: Context-Aware Multimodal Grief Coach (PRD)**

## **1\. Project Overview**

EmoSync is a privacy-first, hybrid AI coach for navigating grief and heartbreak. It integrates **Voice** and **Text Chat** with the **Model Context Protocol (MCP)** to ground conversations in the user's actual life events (Calendar) and reflections (Journals), applying **CBT**, **ACT**, and **Narrative Therapy** frameworks.

## **2\. Core Features**

* **Hybrid Interface:** Seamlessly switch between real-time voice and traditional text chat.  
* **Voice-First Empathy:** Low-latency STT/TTS with "prosody-aware" system prompts for soothing output.  
* **MCP Integration:**  
  * **Calendar Server:** Identifies anniversaries, holidays, and significant dates.  
  * **Journal Server:** Performs semantic search over private local Markdown/Text files to find evidence for CBT reframing.  
* **Agentic Reasoning (LangGraph):**  
  * **The Historian:** Pulls context from MCP servers.  
  * **The Specialist:** Applies CBT/ACT protocols (e.g., Thought Records) based on context.  
  * **The Anchor:** Ensures all responses are validating and trauma-informed.

## **3\. Technical Stack**

* **Frontend:** Next.js 14, Tailwind CSS, Web Audio API, Lucide React.  
* **Backend:** Python 3.11, FastAPI, LangGraph, LangChain.  
* **AI/LLM:** Gemini 3.1  Pro (Multimodal Capabilities), Whisper (STT), ElevenLabs (TTS).  
* **Storage:** PostgreSQL \+ pgvector for RAG; Local Filesystem for MCP.

## **4\. Hybrid Workflow**

1. **Input:** User provides Voice (Web Audio API) or Text (Input Field).  
2. **Processing:** \- Voice is transcribed via Whisper.  
   * Text is sent directly to the agentic router.  
3. **Reasoning:** LangGraph triggers the **Historian** \-\> Queries MCP for "Evidence" or "Dates".  
4. **Synthesis:** **Specialist Agent** uses CBT frameworks \+ MCP data to draft a response.  
5. **Output:** \- Text response is streamed to the chat UI.  
   * Audio response is synthesized via ElevenLabs and streamed to the user.