from flask import g
import json
from datetime import datetime
from sentence_transformers import SentenceTransformer
import os

# def create_doc(video_id: str, service_identifier: str, video_data: dict):
#     """Create or update a video document in OpenSearch."""
#     opensearch_client = g.video_opensearch
#     timestamp = int(datetime.utcnow().timestamp() * 1000)

#     existing_doc = opensearch_client.get(index="videos", id=video_id, ignore=[404])

#     if existing_doc.get("found"):
#         existing_data = existing_doc["_source"]
#         existing_data["updated_at"] = timestamp

#         if service_identifier in existing_data:
#             existing_data[service_identifier]["updated_at"] = timestamp
#             existing_data[service_identifier]["data"].update(video_data)
#         else:
#             existing_data[service_identifier] = {
#                 "service_identifier": service_identifier,
#                 "created_at": timestamp,
#                 "updated_at": timestamp,
#                 "data": video_data,
#             }
#     else:
#         existing_data = {
#             "video_id": video_id,
#             "created_at": timestamp,
#             "updated_at": timestamp,
#             service_identifier: {
#                 "service_identifier": service_identifier,
#                 "created_at": timestamp,
#                 "updated_at": timestamp,
#                 "data": video_data,
#             },
#         }

#     return opensearch_client.index(
#         index="videos", id=video_id, body=existing_data, refresh=True
#     )


_model = None
_model_init_error = None


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def get_embedding_model():
    global _model
    global _model_init_error

    if _model is not None:
        return _model
    if _model_init_error is not None:
        return None

    if _env_flag("DISABLE_EMBEDDINGS", default=False):
        _model_init_error = RuntimeError("Embeddings disabled by DISABLE_EMBEDDINGS")
        return None

    model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    local_files_only = _env_flag("EMBEDDING_LOCAL_ONLY", default=True)
    try:
        _model = SentenceTransformer(model_name, local_files_only=local_files_only)
        return _model
    except Exception as exc:
        _model_init_error = exc
        print(f"Embedding model unavailable ({model_name}): {exc}")
        return None


def create_doc(video_id: str, service_identifier: str, video_data: dict):
    """Create/update video document with vector embedding"""
    opensearch_client = g.video_opensearch
    timestamp = int(datetime.utcnow().timestamp() * 1000)

    # Extract text for embedding: title + description + tags
    text_to_embed = (
        " ".join(
            [
                video_data.get("title", ""),
                video_data.get("description", ""),
                " ".join(video_data.get("tag", [])),
                " ".join(video_data.get("keyword", [])),
            ]
        )
        or "default"
    )

    model = get_embedding_model()
    embedding = model.encode([text_to_embed])[0].tolist() if model else None

    # Fetch existing doc or initialize new
    existing_doc = opensearch_client.get(index="videos", id=video_id, ignore=[404])

    if existing_doc.get("found"):
        existing_data = existing_doc["_source"]
        existing_data["updated_at"] = timestamp
        if embedding is not None:
            existing_data["text_vector"] = embedding

        if service_identifier in existing_data:
            existing_data[service_identifier]["updated_at"] = timestamp
            existing_data[service_identifier]["data"].update(video_data)
        else:
            existing_data[service_identifier] = {
                "service_identifier": service_identifier,
                "created_at": timestamp,
                "updated_at": timestamp,
                "data": video_data,
            }
    else:
        existing_data = {
            "video_id": video_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            service_identifier: {
                "service_identifier": service_identifier,
                "created_at": timestamp,
                "updated_at": timestamp,
                "data": video_data,
            },
        }
        if embedding is not None:
            existing_data["text_vector"] = embedding

    return opensearch_client.index(
        index="videos", id=video_id, body=existing_data, refresh=True
    )


def update_document(document_id, update_body):
    opensearch_client = g.video_opensearch
    response = opensearch_client.update(
        index="videos", id=document_id, body={"doc": {"video_data": update_body}}
    )
    return response


def delete_document(document_id):
    opensearch_client = g.video_opensearch
    response = opensearch_client.delete(index="videos", id=document_id)
    return response


def preprocess_query(query: dict):
    """
    Transform simplified query keys (e.g., "cts.append") into full paths (e.g., "cts.data.append").
    """
    processed_query = {}
    for field, value in query.items():
        if "." in field:
            # Split the field into service and subfield (e.g., "cts.append" -> ["cts", "append"])
            service, subfield = field.split(".", 1)
            # Construct the full path (e.g., "cts.data.append")
            full_path = f"{service}.data.{subfield}"
            processed_query[full_path] = value
        else:
            # If the field doesn't need transformation, keep it as-is
            processed_query[field] = value
    return processed_query


def handle_operators(field: str, value):
    """
    Handle different operators for fields.
    """
    if "__gte" in field:
        return {"range": {field.replace("__gte", ""): {"gte": value}}}
    elif "__lte" in field:
        return {"range": {field.replace("__lte", ""): {"lte": value}}}
    elif "__gt" in field:
        return {"range": {field.replace("__gt", ""): {"gt": value}}}
    elif "__lt" in field:
        return {"range": {field.replace("__lt", ""): {"lt": value}}}
    elif "__in" in field:
        return {"terms": {field.replace("__in", ""): value}}
    else:
        return {"term": {field: value}}


def search_videos(query: dict, offset: int = 0, limit: int = 10):
    """
    Main search function to construct and execute an OpenSearch query.
    """
    offset = max(0, offset)
    limit = max(1, limit)
    processed_query = preprocess_query(query)

    must_conditions = []
    filter_conditions = []

    for field, value in processed_query.items():
        condition = handle_operators(field, value)
        if "__" in field:
            filter_conditions.append(condition)
        else:
            must_conditions.append(condition)

    search_query = {
        "query": {
            "bool": {
                "must": must_conditions,
                "filter": filter_conditions,
            }
        },
        "from": offset,
        "size": limit,
        "aggs": {},  # Optional: add specific aggregations here if needed
    }

    opensearch_client = g.video_opensearch
    response = opensearch_client.search(index="videos", body=search_query)

    hits = response.get("hits", {})
    hit_items = hits.get("hits", [])
    videos = [hit.get("_source", {}) for hit in hit_items]
    total = hits.get("total", {}).get("value", len(videos))
    next_offset = offset + limit if (offset + limit) < total else None

    # Use the external facets function
    # facets = get_dynamic_facets(index="videos")
    print(search_query)
    return {
        "videos": videos,
        "documents": [video.get("video_id") for video in videos if video.get("video_id")],
        "res": hit_items,
        "offset": offset,
        "limit": limit,
        "next_offset": next_offset,
        # "facets": facets,
        "total": total,
    }


def get_dynamic_facets(index="videos"):
    """
    Discover aggregatable fields in the mapping and return facet aggregations for them.
    """
    opensearch_client = g.video_opensearch
    mapping = opensearch_client.indices.get_mapping(index=index)
    properties = mapping[index]["mappings"]["properties"]

    facet_fields = []

    def find_facet_fields(props, prefix=""):
        for k, v in props.items():
            full_field = f"{prefix}.{k}" if prefix else k

            if "type" in v:
                field_type = v["type"]
                if field_type in (
                    "keyword",
                    "integer",
                    "long",
                    "float",
                    "boolean",
                    "date",
                ):
                    facet_fields.append(full_field)
                elif (
                    field_type == "text" and "fields" in v and "keyword" in v["fields"]
                ):
                    facet_fields.append(f"{full_field}.keyword")
            elif "properties" in v:
                find_facet_fields(v["properties"], full_field)

    find_facet_fields(properties)

    if not facet_fields:
        return {}

    aggs = {
        field.replace(".", "_"): {"terms": {"field": field, "size": 10}}
        for field in facet_fields
    }

    body = {"size": 0, "aggs": aggs}

    response = opensearch_client.search(index=index, body=body)

    facets = {}
    for field in facet_fields:
        agg_key = field.replace(".", "_")
        buckets = response.get("aggregations", {}).get(agg_key, {}).get("buckets", [])
        facets[field] = buckets
    # print(f"Facets: {facets}")

    return facets


def vector_search(
    query: str,
    k: int = 5,
    categories: list = None,
    tags: list = None,
    duration_min: float = None,
    duration_max: float = None,
    created_date_start: int = None,  # Changed from created_dates
    created_date_end: int = None,  # Added end date
    locations: list = None,
    resolutions: list = None,
    orientation: list = None,
):
    opensearch_client = g.video_opensearch
    model = get_embedding_model()
    vector = model.encode(query).tolist() if model is not None else None

    must_clauses = []
    if vector is not None:
        must_clauses.append({"knn": {"text_vector": {"vector": vector, "k": k}}})
    elif query:
        # Fallback when embeddings are unavailable: lexical query with filters.
        must_clauses.append(
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "video_id^3",
                        "rms.data.name^2",
                        "rms.data.description^2",
                        "rms.data.additional.Title^2",
                        "rms.data.additional.Description",
                        "rms.data.tag",
                        "rms.data.keyword",
                        "rms.data.ownerName",
                    ],
                    "type": "best_fields",
                    "lenient": True,
                }
            }
        )
    else:
        must_clauses.append({"match_all": {}})
    filter_clauses = []

    # Categories filter
    if categories:
        filter_clauses.append({"terms": {"rms.data.keyword.keyword": categories}})

    # Tags filter
    if tags:
        filter_clauses.append({"terms": {"rms.data.tag.keyword": tags}})

    # Duration range filter (in seconds)
    if duration_min is not None or duration_max is not None:
        range_filter = {"range": {"rms.data.metadata.RDuration": {}}}
        if duration_min is not None:
            range_filter["range"]["rms.data.metadata.RDuration"]["gte"] = duration_min
        if duration_max is not None:
            range_filter["range"]["rms.data.metadata.RDuration"]["lte"] = duration_max
        filter_clauses.append(range_filter)

    # Created date range filter (timestamps) - Using the "created" field
    if created_date_start is not None or created_date_end is not None:
        range_filter = {"range": {"rms.data.created": {}}}
        if created_date_start is not None:
            range_filter["range"]["rms.data.created"]["gte"] = created_date_start
        if created_date_end is not None:
            range_filter["range"]["rms.data.created"]["lte"] = created_date_end
        filter_clauses.append(range_filter)

    # Locations filter
    if locations and len(locations) > 0:
        filter_clauses.append(
            {"terms": {"rms.data.additional.Location.keyword": locations}}
        )

    # Resolutions filter
    if resolutions and len(resolutions) > 0:
        filter_clauses.append(
            {"terms": {"rms.data.default.Dimensions.keyword": resolutions}}
        )

    # Orientation filter
    if orientation and len(orientation) > 0:
        filter_clauses.append(
            {"terms": {"rms.data.metadata.Orientation.keyword": orientation}}
        )

    fquery = {
        "size": k,
        "query": {"bool": {"must": must_clauses, "filter": filter_clauses}},
    }

    print("OpenSearch Query:", fquery)
    response = opensearch_client.search(index="videos", body=fquery)

    return {
        "status": "success",
        "mode": "vector" if vector is not None else "fallback_lexical",
        "documents": [hit["_source"] for hit in response["hits"]["hits"]],
    }


def keyword_search(keyword: str = None):
    opensearch_client = g.video_opensearch

    if keyword:
        query = {
            "query": {
                "multi_match": {"query": keyword, "fields": ["*"], "fuzziness": "AUTO"}
            }
        }
    else:
        query = {"query": {"match_all": {}}}

    response = opensearch_client.search(index="videos", body=query)
    videos = [hit["_source"] for hit in response["hits"]["hits"]]
    total = response["hits"]["total"]["value"]

    return {
        "status": "success",
        "videos": videos,
        "documents": videos,
        "total": total,
    }


def get_categories():
    opensearch_client = g.video_opensearch

    response = opensearch_client.search(
        index="videos",
        size=0,
        body={
            "aggs": {
                "unique_categories": {
                    "terms": {
                        "field": "rms.data.keyword.keyword",  # <- must use .keyword for aggregation
                        "size": 1000,
                    }
                }
            }
        },
    )

    buckets = response["aggregations"]["unique_categories"]["buckets"]
    categories = [bucket["key"] for bucket in buckets]

    return {"status": "success", "categories": categories, "buckets": buckets}


def get_latest_videos():
    """
    Get the latest videos from OpenSearch sorted by 'updated_at' (or 'created_at').
    """
    opensearch_client = g.video_opensearch  # from your Flask global context

    query = {
        "size": 20,
        "sort": [{"created_at": {"order": "desc"}}],
        "query": {"match_all": {}},
    }

    response = opensearch_client.search(index="videos", body=query)

    # Extract the hits
    hits = response["hits"]["hits"]
    results = [hit["_source"] for hit in hits]

    return {"total": response["hits"]["total"]["value"], "videos": results}


def get_facets():
    """
    Fetch facet aggregations from the 'videos' index.
    Only include aggregations if the field exists.
    """
    opensearch_client = g.video_opensearch
    index_name = "videos"

    body = {
        "size": 0,
        "aggs": {
            "locations": {
                "terms": {"field": "rms.data.additional.Location.keyword", "size": 1000}
            },
            "durations": {
                "terms": {"field": "rms.data.metadata.RDuration", "size": 1000}
            },
            "resolutions": {
                "terms": {"field": "rms.data.default.Dimensions.keyword", "size": 100}
            },
            "orientation": {
                "terms": {
                    "field": "rms.data.metadata.Orientation.keyword",
                    "size": 10,
                }
            },
            "tags": {"terms": {"field": "rms.data.tag.keyword", "size": 1000}},
        },
    }

    response = opensearch_client.search(index=index_name, body=body)
    aggs = response.get("aggregations", {})

    facets = {
        "locations": [b["key"] for b in aggs.get("locations", {}).get("buckets", [])],
        "durations": [b["key"] for b in aggs.get("durations", {}).get("buckets", [])],
        "resolutions": [
            b["key"] for b in aggs.get("resolutions", {}).get("buckets", [])
        ],
        "orientation": [
            b["key"] for b in aggs.get("orientation", {}).get("buckets", [])
        ],
        "tags": [b["key"] for b in aggs.get("tags", {}).get("buckets", [])],
    }

    return {"status": "success", "facets": facets, "raw_aggs": aggs}
