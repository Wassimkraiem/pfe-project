from flask import g
from marshmallow import ValidationError


def create_mapping_index(index_name: str):
    opensearch_client = g.video_opensearch
    response = opensearch_client.indices.exists(index=index_name)
    if response:
        raise ValidationError({"error": "index already exists"})
    response = opensearch_client.indices.create(index=index_name, ignore=400)
    return response


def delete_index(index_name):
    opensearch_client = g.video_opensearch
    index_exists(index_name)
    response = opensearch_client.indices.delete(index=index_name)
    return response


def add_field_to_schema(schema, path_parts, field_type):
    current_schema = schema["properties"]

    for i, part in enumerate(path_parts):
        if i == len(path_parts) - 1:
            if part in current_schema:
                raise ValidationError(
                    {"error": f"Field '{'.'.join(path_parts)}' already exists"}
                )
            current_schema[part] = {"type": field_type}
        else:
            if part not in current_schema:
                current_schema[part] = {"type": "nested", "properties": {}}
            elif "properties" not in current_schema[part]:
                raise ValidationError(
                    {
                        "error": f"'{part}' is not a nested field and cannot have subfields"
                    }
                )
            current_schema = current_schema[part]["properties"]


def add_fields_to_schema(schema, fields):
    """
    Add multiple fields to the schema. Fields should be a dictionary where keys are field names or paths,
    and values are either field types or nested dictionaries for nested fields.
    """
    current_schema = schema["properties"]

    def add_field_recursive(schema_level, path_parts, field_type):
        current = schema_level
        for i, part in enumerate(path_parts):
            if i == len(path_parts) - 1:
                if part in current:
                    raise ValidationError(
                        {"error": f"Field '{'.'.join(path_parts)}' already exists"}
                    )
                current[part] = {"type": field_type}
            else:
                if part not in current:
                    current[part] = {"type": "nested", "properties": {}}
                elif "properties" not in current[part]:
                    raise ValidationError(
                        {
                            "error": f"'{part}' is not a nested field and cannot have subfields"
                        }
                    )
                current = current[part]["properties"]

    for field_path, field_type in fields.items():
        field_path_parts = field_path.split(".")
        add_field_recursive(current_schema, field_path_parts, field_type)


def get_mapping(index_name):
    opensearch_client = g.video_opensearch
    index_exists(index_name)
    response = opensearch_client.indices.get_mapping(index=index_name)

    return response


def reindex_videos(source_index, dest_index):
    """
    Reindex all videos from the source index to the destination index.
    Can also be used to reindex within the same index.
    """
    body = {"source": {"index": source_index}, "dest": {"index": dest_index}}
    opensearch_client = g.video_opensearch
    response = opensearch_client.reindex(body=body, wait_for_completion=True)
    return response


def delete_old_index(old_index_name):
    """Delete the old index after reindexing."""
    opensearch_client = g.video_opensearch
    opensearch_client.indices.delete(index=old_index_name)


def video_exists(index_name, video_id):
    """Check if the video exists in the specified index."""
    opensearch_client = g.video_opensearch
    response = opensearch_client.get(index=index_name, id=video_id)
    if not response:
        raise ValidationError({"error": "video does not exist"})
    return response


def index_exists(index_name):
    """Check if the specified index exists."""
    opensearch_client = g.video_opensearch
    response = opensearch_client.indices.exists(index=index_name)
    if not response:
        raise ValidationError({"error": "index does not exist"})
    return response


def get_index(index_name):
    """Check if the specified index exists."""
    opensearch_client = g.video_opensearch
    response = opensearch_client.indices.get(index=index_name)
    if not response:
        raise ValidationError({"error": "index does not exist"})
    return response


def build_videos_v2_mapping(embedding_dimension: int = 1536) -> dict:
    return {
        "settings": {
            "index": {
                "knn": True,
            }
        },
        "mappings": {
            "properties": {
                "video_id": {"type": "keyword"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "description": {"type": "text"},
                "tags": {"type": "keyword"},
                "categories": {"type": "keyword"},
                "duration_sec": {"type": "float"},
                "location": {"type": "keyword"},
                "resolution": {"type": "keyword"},
                "orientation": {"type": "keyword"},
                "views_max": {"type": "long"},
                "created_ts": {"type": "long"},
                "owner_name": {"type": "keyword"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": embedding_dimension,
                },
                "raw": {"type": "object", "enabled": False},
                "rms": {"type": "object", "enabled": False},
                "cts": {"type": "object", "enabled": False},
            }
        },
    }


def bootstrap_videos_v2_aliases(
    index_name: str = "videos_v2",
    read_alias: str = "videos_read",
    write_alias: str = "videos_write",
    embedding_dimension: int = 1536,
) -> dict:
    opensearch_client = g.video_opensearch

    if not opensearch_client.indices.exists(index=index_name):
        opensearch_client.indices.create(
            index=index_name,
            body=build_videos_v2_mapping(embedding_dimension=embedding_dimension),
        )

    actions = []
    for alias_name in (read_alias, write_alias):
        try:
            alias_indexes = opensearch_client.indices.get_alias(name=alias_name)
            for alias_index in alias_indexes.keys():
                actions.append({"remove": {"index": alias_index, "alias": alias_name}})
        except Exception:
            # Alias may not exist yet; that's expected on first bootstrap.
            pass

    actions.extend(
        [
            {"add": {"index": index_name, "alias": read_alias}},
            {"add": {"index": index_name, "alias": write_alias, "is_write_index": True}},
        ]
    )
    opensearch_client.indices.update_aliases(body={"actions": actions})

    aliases = opensearch_client.indices.get_alias(index=index_name)
    return {
        "status": "success",
        "index_name": index_name,
        "read_alias": read_alias,
        "write_alias": write_alias,
        "aliases": aliases.get(index_name, {}).get("aliases", {}),
    }
