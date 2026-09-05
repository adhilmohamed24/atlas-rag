# Validation record

Verified locally on Windows / Python 3.12, September 6, 2026.

- 10 automated tests passed: chunk overlap, unsafe URL rejection, invalid PDF rejection, index deduplication, visibility, deletion, owner authorization, HTTP streaming, no-evidence response, and the LLM streaming contract with a simulated provider.
- JavaScript syntax and Python compilation passed.
- Real FastEmbed BGE model downloaded and used with Qdrant for the three-question retrieval smoke fixture: hit@5 = 3/3; MRR = 0.778. Expected document ranks were 3, 1, 1. This tiny fixture is not representative of general document retrieval accuracy.
- Browser preview rendered and a sample question produced excerpts; clicking citation [2] opened the matching Atlas architecture evidence panel.

External LLM generation, live Notion integration, Docker build, and hosted deployment require separate verification. No deployment or paid-provider success is claimed by these local checks. Dependency deprecation warnings were observed in the FastAPI test-client stack; they did not fail the tests.
