# Validation record

Verified locally on Windows / Python 3.12, September 6–7, 2026.

- 11 automated tests passed: chunk overlap, unsafe URL rejection, invalid PDF rejection, index deduplication, visibility, deletion, owner authorization, HTTP streaming, no-evidence response, the LLM streaming contract with a simulated provider, and streamed HTML extraction.
- JavaScript syntax and Python compilation passed.
- Real FastEmbed BGE model downloaded and used with Qdrant for the three-question retrieval smoke fixture: hit@5 = 3/3; MRR = 0.778. Expected document ranks were 3, 1, 1. This tiny fixture is not representative of general document retrieval accuracy.
- Browser preview rendered and a sample question produced excerpts; clicking citation [2] opened the matching Atlas architecture evidence panel.

The Docker build and public Render deployment succeeded. Live semantic retrieval and Groq generation were verified using `openai/gpt-oss-20b`: one question returned five source chunks, 156 token events, a final completion event, and inline citations. This is an integration observation, not a performance benchmark.

GitHub Actions passed for deployment commit `32a996f793d8ec3bc68f077625d3a5da67ea3c5a`. The initial 24 published files were compared with the local project and matched after normalizing line endings.

Live owner PDF ingestion into Qdrant Cloud succeeded. A synthetic one-page PDF returned the expected retention period (37 days) and review owner (Library Team); clicking its citation displayed the exact excerpt and Page 1. The same PDF remained retrievable after Render redeployed commit `33476ca`, verifying persistence across that deployment. An anonymous client could neither list the private PDF nor retrieve it by explicitly supplying its document ID.

Live testing found and corrected alternate numeric citation brackets and an HTML bytearray parsing error. HTTPS ingestion of example.com then indexed one private chunk successfully. Empty provider streams now emit an error instead of reporting a successful blank answer; automated coverage verifies this behavior. GPT-OSS uses low reasoning effort and a 2,048-token completion allowance.

Live Notion integration still requires a NOTION_TOKEN and a shared page and has not been verified. Dependency deprecation warnings were observed in the FastAPI test-client stack; they did not fail the tests.
