# STEPS: A Systematic Testing Proposal for Progressive Cognitive Abilities in Language Models

Large language models (LLMs) aligned with humans are reshaping AI research and applications, but a comprehensive and reliable evaluation of them remains a conundrum in academia. As an initial attempt, we present STEPS, a Systematic TEsting PropoSal tailored for chat-based LLMs' progressive cognitive abilities. Enlightened by taxonomy in cognitive science, we categorize existing identified abilities of LLMs into 5 progressive levels: Task Knowledge, Test-Taking, Grounding, Resourcefulness, and Decisiveness. On top of the design, we compile and create a series of novel tasks, settings, datasets, and environments with a scalable and handy toolkit for unified LLM evaluation. Our extensive testing over APIs and open-sourced chat-based LLMs unveil that, while gaps between star companies' and open-sourced competitors are tolerable at preliminary levels (e.g., I & II), on advanced challenges (e.g., IV & V) their performances are poles apart. STEPS demonstrates a significant discrepancy between GPT-4 and other models. We appeal to the community to join the effort to review and benchmark our current progresses and limitations holistically.

## STEPS Overall Result

| Model                  | I    | II   | III  | IV   | V    | AVG  |
| ---------------------- | ---- | ---- | ---- | ---- | ---- | ---- |
| gpt-4                  | 60.2 | 57.2 | 52.5 | 61.2 | 48.6 | 55.9 |
| gpt-turbo-3.5          | 48.9 | 48.3 | 48.8 | 56.8 | 27.2 | 46.0 |
| claude-v1.3            | 49.1 | 47.8 | 46.8 | 50.9 | 31.2 | 45.2 |
| claude-instant-v1.1    | 46.0 | 46.8 | 45.1 | 42.4 | 27.8 | 41.6 |
| text-davinci-003       | 46.5 | 42.5 | 46.8 | 38.6 | 23.4 | 39.5 |
| text-davinci-002       | 41.4 | 41.6 | 45.6 | 32.0 | 15.2 | 35.2 |
| text-bison-001         | 44.0 | /    | 46.9 | 25.3 | 15.0 | 32.8 |
| chatglm-130b           | 41.6 | 42.4 | 44.6 | 20.9 | 5.0  | 30.9 |
| chatglm-6b             | 36.8 | 36.0 | 43.0 | 13.3 | 3.0  | 26.4 |
| vicuna-13b             | 34.4 | 28.2 | 42.6 | 20.9 | 3.6  | 25.9 |
| bloomz-7b1-mt          | 38.1 | 36.1 | 43.0 | 2.6  | 2.4  | 24.4 |
| vicuna-7b              | 32.2 | 27.1 | 42.2 | 13.7 | 1.7  | 23.4 |
| dolly-v2-12b           | 29.1 | 29.6 | 37.7 | 11.4 | 3.2  | 22.2 |
| bloomz-7b1             | 35.9 | 27.2 | 42.3 | 2.9  | 2.1  | 22.1 |
| koala-13b              | 28.1 | 27.1 | 41.8 | 11.1 | 0.7  | 21.8 |
| moss-moon-003-sft      | 26.5 | 26.2 | 40.9 | 9.8  | 0.1  | 20.7 |
| oasst-sft-4-pythia-12b | 26.2 | 28.3 | 40.5 | 7.9  | 0.5  | 20.7 |