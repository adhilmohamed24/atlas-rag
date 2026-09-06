import hashlib
import math
import os
import re
import uuid
from collections import Counter
from qdrant_client import QdrantClient, models
from .ingest import chunks

class Store:
    def __init__(self, demo=False, path=None):
        self.demo = demo
        self.model = None
        self.dimension = 384
        if os.getenv("QDRANT_URL") and path is None:
            self.client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.getenv("QDRANT_API_KEY"), timeout=30)
        else:
            self.client = QdrantClient(path=path or os.path.join(os.getenv("DATA_DIR", "data"), "qdrant"))
        self.collection = "atlas_demo_v1" if demo else "atlas_" + hashlib.sha256(os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5").encode()).hexdigest()[:12]
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(self.collection, vectors_config=models.VectorParams(size=self.dimension, distance=models.Distance.COSINE))
        if os.getenv("QDRANT_URL") and path is None:
            # Cloud strict mode requires indexes for filtered vector queries.
            self.client.create_payload_index(self.collection, field_name="public", field_schema=models.PayloadSchemaType.BOOL, wait=True)
            self.client.create_payload_index(self.collection, field_name="doc_id", field_schema=models.PayloadSchemaType.KEYWORD, wait=True)

    def embed(self, texts, query=False):
        if self.demo:
            vectors = []
            for text in texts:
                vector = [0.0] * self.dimension
                for term, count in Counter(re.findall(r"\w+", text.lower())).items():
                    vector[int(hashlib.sha256(term.encode()).hexdigest()[:8], 16) % self.dimension] += count
                norm = math.sqrt(sum(x*x for x in vector)) or 1
                vectors.append([x/norm for x in vector])
            return vectors
        if self.model is None:
            from fastembed import TextEmbedding
            self.model = TextEmbedding(model_name=os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"), threads=2)
        method = self.model.query_embed if query else self.model.embed
        return [v.tolist() for v in method(texts, batch_size=8)]

    def ingest(self, title, kind, pages, url="", public=False):
        content = "\n".join(text for _, text in pages)
        if len(content) > 500_000:
            raise ValueError("Document exceeds the 500,000 character limit.")
        if len(content.strip()) < 30:
            raise ValueError("Document contains too little readable text.")
        doc_id = hashlib.sha256((kind + url + title + content).encode()).hexdigest()[:24]
        pieces = [(page, text) for page, text in pages for text in chunks(text)]
        vectors = self.embed([text for _, text in pieces])
        points = [models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc_id}:{i}")), vector=vector, payload={"doc_id": doc_id, "title": title, "kind": kind, "page": page, "text": text, "url": url, "public": public, "chunk": i, "chunks": len(pieces)}) for i, ((page, text), vector) in enumerate(zip(pieces, vectors))]
        self.client.upsert(self.collection, points=points, wait=True)
        return {"id": doc_id, "title": title, "kind": kind, "chunks": len(pieces)}

    def documents(self, public_only=False):
        docs = {}
        offset = None
        while True:
            points, offset = self.client.scroll(self.collection, scroll_filter=self.filters(public_only), limit=100, offset=offset, with_vectors=False)
            for p in points:
                d = p.payload
                docs[d["doc_id"]] = {"id": d["doc_id"], "title": d["title"], "kind": d["kind"], "chunks": d["chunks"]}
            if offset is None:
                return list(docs.values())

    def filters(self, public_only=False, ids=None):
        must = []
        if public_only:
            must.append(models.FieldCondition(key="public", match=models.MatchValue(value=True)))
        if ids:
            must.append(models.FieldCondition(key="doc_id", match=models.MatchAny(any=ids)))
        return models.Filter(must=must) if must else None

    def search(self, question, ids=None, public_only=False):
        results = self.client.query_points(self.collection, query=self.embed([question], query=True)[0], query_filter=self.filters(public_only, ids), limit=5, with_payload=True).points
        return [{**p.payload, "score": round(p.score, 4), "citation": i+1} for i, p in enumerate(results) if p.score > 0.25]

    def delete(self, doc_id):
        self.client.delete(self.collection, points_selector=models.FilterSelector(filter=self.filters(ids=[doc_id])), wait=True)
