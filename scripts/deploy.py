"""Publish this directory to a Hugging Face Docker Space using a locally configured HF_TOKEN."""
import argparse
import os
from pathlib import Path
from huggingface_hub import HfApi

parser = argparse.ArgumentParser()
parser.add_argument("repo_id", help="Your Hugging Face username/atlas-knowledge-studio")
parser.add_argument("--demo", action="store_true", help="Enable the public offline excerpt demo")
args = parser.parse_args()
if not os.getenv("HF_TOKEN"):
    raise SystemExit("Set HF_TOKEN in your local environment. Never commit it.")
api = HfApi(token=os.environ["HF_TOKEN"])
api.create_repo(repo_id=args.repo_id, repo_type="space", space_sdk="docker", private=False, exist_ok=True)
if args.demo:
    api.add_space_variable(repo_id=args.repo_id, key="DEMO_MODE", value="1")
api.upload_folder(repo_id=args.repo_id, repo_type="space", folder_path=str(Path(__file__).resolve().parents[1]), ignore_patterns=["data/**", "**/__pycache__/**", ".pytest_cache/**", ".env", ".venv/**", ".git/**"], commit_message="Deploy Atlas RAG workspace")
print(f"Uploaded. Inspect build status at https://huggingface.co/spaces/{args.repo_id}")
