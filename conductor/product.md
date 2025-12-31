# Initial Concept
LLM Council: A local web app that uses OpenRouter to send queries to multiple LLMs, has them review and rank each other's work, and then uses a Chairman LLM to produce a final response.

# Product Guide

## Target Users
- **Power Users:** Individuals seeking high-quality, verified LLM outputs for complex tasks.
- **Writers and Content Creators:** Users looking for diverse perspectives and creative brainstorming.
- **Software Developers:** Engineers needing multiple opinions on complex software architectural questions and technical trade-offs.

## Value Proposition
The LLM Council solves the problem of "single-model bias" for challenging questions that require reasoning, taste, or experience. It helps users:
- **Navigate Ambiguity:** Explore different valid approaches to the same problem.
- **Expand Brainstorming:** Use multiple models to increase the creative "surface area."
- **Identify Alignment:** Look for consensus among different models in high-uncertainty scenarios.
- **Synthesize Quality:** Use peer review and chairmanship to filter and refine model outputs.
- **Resilient Reliability:** Gracefully handles individual model timeouts or API failures, ensuring the council process continues even if some experts are unavailable.

## Core Features
- **Stage 1: Resilient Parallel Execution:** Simultaneously send user queries to a configurable council of LLMs, with robust error handling for individual model failures. Intermediate steps are collapsible to maintain a clean workspace.
- **Stage 2: Blinded Peer Review:** Anonymized cross-review where models rank and critique each other's insights and accuracy, maintaining flow even if some models fail to respond.
- **Stage 3: Chairman Synthesis:** A designated Chairman LLM synthesizes all individual outputs and peer reviews into a single, high-quality final response.
- **Chairman Follow-up:** Direct dialogue with the Chairman model after synthesis, allowing for clarifications or deeper exploration of the final response without re-running the full council.
- **File Context Support:** Drag and drop or attach text-based files (.txt, .md, code) to provide grounding context for council queries or Chairman follow-ups.
- **Conversation Management:** Robust sidebar controls for pinning important chats, archiving old ones, and duplicating conversations. Inline title editing allows for easy organization.
- **Enhanced Deletion Experience:** A custom, theme-aware confirmation modal replaces native browser prompts for both single and bulk deletions, ensuring a consistent and accessible UI.
