"""Create MongoDB indexes, including the vector search index for chunks.

This script tries to create:
- standard (B-tree) unique indexes for deduplication
- an Atlas Search / vectorSearch index for semantic search

If the server does not support search indexes, it will print instructions.
"""

import json

from src.shared.config import get_config
from src.shared.db import get_db


VECTOR_INDEX_NAME = "chunks_vector_index"


def main() -> None:
    cfg = get_config()
    db = get_db()

    # Standard indexes
    db[cfg["messages_collection"]].create_index("message_id", unique=True)
    db[cfg["linked_docs_collection"]].create_index("url", unique=True)
    db[cfg["chunks_collection"]].create_index("chunk_id", unique=True)

    # Vector search index (Atlas Search / MongoDB with search indexes enabled)
    """
    definition = {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": int(cfg["embedding_dimension"]),
                "similarity": "cosine",
            }
        ]
    }

    cmd = {
        "createSearchIndexes": cfg["chunks_collection"],
        "indexes": [{"name": VECTOR_INDEX_NAME, "definition": definition}],
    }
    """

    definition = {
        "mappings": {
            "dynamic": False,
            "fields": {
                "embedding": {
                    "type": "knnVector",
                    "dimensions": int(cfg["embedding_dimension"]),
                    "similarity": "cosine"
                }
            }
        }
    }

    cmd = {
        "createSearchIndexes": cfg["chunks_collection"],
        "indexes": [
            {
                "name": VECTOR_INDEX_NAME,
                "definition": definition
            }
        ],
    }    

    try:
        result = db.command(cmd)
        print("Created/updated search index:", result)
    except Exception as e:
        print("Could not create search/vector index automatically.")
        print("Reason:", str(e))
        print()
        print("If you're using MongoDB Atlas, create a Search index with this definition:")
        print(json.dumps({"name": VECTOR_INDEX_NAME, "definition": definition}, indent=2))


if __name__ == "__main__":
    main()

