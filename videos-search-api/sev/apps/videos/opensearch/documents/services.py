from __future__ import annotations

from flask import g
import json
from datetime import datetime
import os
import re
import time

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - local provider is optional
    SentenceTransformer = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional until dependencies are installed
    OpenAI = None

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
_openai_client = None
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSION = 1536
_CATEGORY_ALIASES = {
    "animals": "Animals",
    "animal": "Animals",
    "travel": "Travel",
    "travel hotel": "Travel & Hotel",
    "travel and hotel": "Travel & Hotel",
    "hotel": "Travel & Hotel",
    "gym": "Gym",
    "workout": "Gym/Workout",
    "gym workout": "Gym/Workout",
    "food": "Food",
    "comedy": "Comedy",
    "sports": "Sports",
    "beauty": "Beauty",
    "fails": "Fails",
    "weather": "Weather",
    "feels": "Feels",
    "feel good": "Feel good",
    "crafty": "Crafty",
    "diy": "DIY",
    "boozy": "Boozy",
    "cool": "Cool",
}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def get_videos_read_index() -> str:
    return os.environ.get("VIDEOS_READ_ALIAS", "videos_read")


def get_videos_write_index() -> str:
    return os.environ.get("VIDEOS_WRITE_ALIAS", "videos_write")


def get_embedding_dimension() -> int:
    return _env_int("EMBEDDING_DIMENSION", DEFAULT_EMBEDDING_DIMENSION)


class _Vector(list):
    def tolist(self):
        return list(self)


class _OpenAIEmbeddingModel:
    def __init__(self, client, model_name: str, dimensions: int) -> None:
        self._client = client
        self._model_name = model_name
        self._dimensions = dimensions

    def encode(self, texts):
        single = isinstance(texts, str)
        inputs = [texts] if single else list(texts)
        response = self._client.embeddings.create(
            model=self._model_name,
            input=inputs,
            dimensions=self._dimensions,
        )
        vectors = [_Vector(item.embedding) for item in response.data]
        return vectors[0] if single else vectors


def _get_openai_client():
    global _openai_client

    if OpenAI is None:
        raise RuntimeError("openai package is not installed")
    if _openai_client is None:
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


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

    provider = os.environ.get("EMBEDDING_PROVIDER", "openai").strip().lower()
    model_name = os.environ.get("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    if provider == "openai":
        try:
            _model = _OpenAIEmbeddingModel(
                client=_get_openai_client(),
                model_name=model_name,
                dimensions=get_embedding_dimension(),
            )
            print(f"Embedding model ready ({model_name}, provider=openai)")
            return _model
        except Exception as exc:
            _model_init_error = exc
            print(f"OpenAI embedding model init failed ({model_name}): {exc}")
            return None

    if provider not in {"sentence-transformers", "sentence_transformers", "local"}:
        _model_init_error = RuntimeError(f"Unsupported EMBEDDING_PROVIDER={provider}")
        return None
    if SentenceTransformer is None:
        _model_init_error = RuntimeError("sentence-transformers package is not installed")
        return None

    model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    prefer_local_files_only = _env_flag("EMBEDDING_LOCAL_ONLY", default=True)
    attempted_modes = [prefer_local_files_only]
    if prefer_local_files_only:
        # If local cache is missing, retry with download enabled so semantic search can still run.
        attempted_modes.append(False)

    last_error = None
    for local_files_only in attempted_modes:
        try:
            _model = SentenceTransformer(model_name, local_files_only=local_files_only)
            print(
                f"Embedding model ready ({model_name}), local_files_only={local_files_only}"
            )
            return _model
        except Exception as exc:
            last_error = exc
            print(
                f"Embedding model load failed ({model_name}, local_files_only={local_files_only}): {exc}"
            )

    _model_init_error = last_error
    return None


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = [part.strip() for part in re.split(r"[,;]", value) if part.strip()]
        return parts or [value.strip()]
    return [str(value).strip()] if str(value).strip() else []


def _first_text(*values) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _nested(data: dict, *keys):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _float_or_none(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value):
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def build_video_embedding_text(video_data: dict) -> str:
    title = _first_text(
        video_data.get("title"),
        video_data.get("name"),
        _nested(video_data, "additional", "Title"),
    )
    description = _first_text(
        video_data.get("description"),
        _nested(video_data, "additional", "Description"),
    )
    tokens = [
        title,
        description,
        " ".join(_as_list(video_data.get("tag") or video_data.get("tags"))),
        " ".join(_as_list(video_data.get("keyword") or video_data.get("category") or video_data.get("categories"))),
        _first_text(video_data.get("location"), _nested(video_data, "additional", "Location")),
        _first_text(video_data.get("ownerName"), video_data.get("owner_name")),
    ]
    text = " ".join(token for token in tokens if token).strip()
    return text or "default"


def build_video_denormalized_fields(video_data: dict) -> dict:
    metadata = video_data.get("metadata") if isinstance(video_data.get("metadata"), dict) else {}
    default = video_data.get("default") if isinstance(video_data.get("default"), dict) else {}
    additional = video_data.get("additional") if isinstance(video_data.get("additional"), dict) else {}

    categories = _as_list(
        video_data.get("keyword") or video_data.get("category") or video_data.get("categories")
    )
    tags = _as_list(video_data.get("tag") or video_data.get("tags"))
    views = _int_or_none(video_data.get("views") or video_data.get("views_max"))

    return {
        "title": _first_text(video_data.get("title"), video_data.get("name"), additional.get("Title")),
        "description": _first_text(video_data.get("description"), additional.get("Description")),
        "tags": tags,
        "categories": categories,
        "duration_sec": _float_or_none(
            video_data.get("duration")
            or metadata.get("duration")
            or metadata.get("RDuration")
        ),
        "location": _first_text(video_data.get("location"), additional.get("Location")),
        "resolution": _first_text(video_data.get("resolution"), default.get("Dimensions")),
        "orientation": _first_text(video_data.get("orientation"), metadata.get("Orientation")),
        "views_max": views,
        "created_ts": _int_or_none(video_data.get("created") or video_data.get("created_ts")),
        "owner_name": _first_text(video_data.get("ownerName"), video_data.get("owner_name")),
        "raw": video_data,
    }


def embed_video_data(video_data: dict):
    model = get_embedding_model()
    if model is None:
        return None
    embedding = model.encode([build_video_embedding_text(video_data)])[0].tolist()
    expected_dimension = get_embedding_dimension()
    if len(embedding) != expected_dimension:
        raise RuntimeError(
            f"Embedding dimension mismatch: got {len(embedding)}, expected {expected_dimension}"
        )
    return embedding


def create_doc(video_id: str, service_identifier: str, video_data: dict):
    """Create/update video document with vector embedding"""
    opensearch_client = g.video_opensearch
    timestamp = int(datetime.utcnow().timestamp() * 1000)
    index_name = get_videos_write_index()
    embedding = embed_video_data(video_data)
    denormalized = build_video_denormalized_fields(video_data)

    # Fetch existing doc or initialize new
    existing_doc = opensearch_client.get(index=index_name, id=video_id, ignore=[404])

    if existing_doc.get("found"):
        existing_data = existing_doc["_source"]
        existing_data["updated_at"] = timestamp
        if embedding is not None:
            existing_data["embedding"] = embedding
        existing_data.update({key: value for key, value in denormalized.items() if value not in (None, "", [])})

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
            **{key: value for key, value in denormalized.items() if value not in (None, "", [])},
            service_identifier: {
                "service_identifier": service_identifier,
                "created_at": timestamp,
                "updated_at": timestamp,
                "data": video_data,
            },
        }
        if embedding is not None:
            existing_data["embedding"] = embedding

    return opensearch_client.index(
        index=index_name, id=video_id, body=existing_data, refresh=True
    )


def update_document(document_id, update_body):
    opensearch_client = g.video_opensearch
    doc_update = {"video_data": update_body, **build_video_denormalized_fields(update_body)}
    embedding = embed_video_data(update_body)
    if embedding is not None:
        doc_update["embedding"] = embedding
    response = opensearch_client.update(
        index=get_videos_write_index(), id=document_id, body={"doc": doc_update}
    )
    return response


def delete_document(document_id):
    opensearch_client = g.video_opensearch
    response = opensearch_client.delete(index=get_videos_write_index(), id=document_id)
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
    total_started = int(time.time() * 1000)
    normalize_started = int(time.time() * 1000)

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
    normalize_ms = int(time.time() * 1000) - normalize_started

    opensearch_client = g.video_opensearch
    retrieval_started = int(time.time() * 1000)
    response = opensearch_client.search(index=get_videos_read_index(), body=search_query)
    retrieval_ms = int(time.time() * 1000) - retrieval_started

    hits = response.get("hits", {})
    hit_items = hits.get("hits", [])
    videos = [hit.get("_source", {}) for hit in hit_items]
    total = hits.get("total", {}).get("value", len(videos))
    next_offset = offset + limit if (offset + limit) < total else None

    # Use the external facets function
    # facets = get_dynamic_facets(index="videos")
    print(search_query)
    execution = {
        "normalize_ms": normalize_ms,
        "subquery_ms": 0,
        "retrieval_ms": retrieval_ms,
        "fusion_ms": 0,
        "rerank_ms": 0,
        "blend_ms": 0,
        "total_ms": int(time.time() * 1000) - total_started,
    }
    return {
        "videos": videos,
        "documents": [video.get("video_id") for video in videos if video.get("video_id")],
        "res": hit_items,
        "offset": offset,
        "limit": limit,
        "next_offset": next_offset,
        # "facets": facets,
        "total": total,
        "execution": execution,
    }


def get_dynamic_facets(index=None):
    """
    Discover aggregatable fields in the mapping and return facet aggregations for them.
    """
    opensearch_client = g.video_opensearch
    index = index or get_videos_read_index()
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
    k: int = 50,
    sort_by: str = None,
    sort_order: str = "desc",
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
    total_started = int(time.time() * 1000)
    normalize_started = int(time.time() * 1000)

    opensearch_client = g.video_opensearch
    query_text = query or ""

    ranking_only_query = _has_ranking_intent(query_text)
    effective_sort_by = sort_by
    if effective_sort_by is None and ranking_only_query:
        effective_sort_by = "views"
    effective_sort_order = _normalize_sort_order(sort_order)

    if not categories:
        categories = _extract_categories_from_query(query_text)
    if duration_max is None:
        duration_max = _extract_duration_max_from_query(query_text)
    normalize_ms = int(time.time() * 1000) - normalize_started

    retrieval_started = int(time.time() * 1000)
    model = get_embedding_model()
    try:
        vector = model.encode(query_text).tolist() if model is not None and query_text else None
    except Exception as exc:
        print(f"Embedding query failed: {exc}")
        vector = None

    must_clauses = []
    if ranking_only_query:
        # For generic "top/trending" intent, ranking should be by views, not lexical matching.
        must_clauses.append({"match_all": {}})
    elif vector is not None:
        must_clauses.append({"knn": {"embedding": {"vector": vector, "k": k}}})
    elif query:
        # Fallback when embeddings are unavailable: lexical query with filters.
        must_clauses.append(
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "video_id^3",
                        "rms.data.name^2",
                        "cts.data.name^2",
                        "rms.data.description^2",
                        "cts.data.description^2",
                        "rms.data.additional.Title^2",
                        "cts.data.additional.Title^2",
                        "rms.data.additional.Description",
                        "cts.data.additional.Description",
                        "rms.data.tag",
                        "cts.data.tag",
                        "rms.data.keyword",
                        "cts.data.keyword",
                        "rms.data.ownerName",
                        "cts.data.ownerName",
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
        filter_clauses.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"categories": categories}},
                        {"terms": {"rms.data.keyword.keyword": categories}},
                        {"terms": {"cts.data.keyword.keyword": categories}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    # Tags filter
    if tags:
        filter_clauses.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"tags": tags}},
                        {"terms": {"rms.data.tag.keyword": tags}},
                        {"terms": {"cts.data.tag.keyword": tags}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    # Duration range filter (in seconds)
    if duration_min is not None or duration_max is not None:
        rms_range = {"range": {"rms.data.metadata.RDuration": {}}}
        cts_range = {"range": {"cts.data.metadata.RDuration": {}}}
        if duration_min is not None:
            rms_range["range"]["rms.data.metadata.RDuration"]["gte"] = duration_min
            cts_range["range"]["cts.data.metadata.RDuration"]["gte"] = duration_min
        if duration_max is not None:
            rms_range["range"]["rms.data.metadata.RDuration"]["lte"] = duration_max
            cts_range["range"]["cts.data.metadata.RDuration"]["lte"] = duration_max
        filter_clauses.append(
            {"bool": {"should": [rms_range, cts_range], "minimum_should_match": 1}}
        )

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
            {
                "bool": {
                    "should": [
                        {"terms": {"location": locations}},
                        {"terms": {"rms.data.additional.Location.keyword": locations}},
                        {"terms": {"cts.data.additional.Location.keyword": locations}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    # Resolutions filter
    if resolutions and len(resolutions) > 0:
        filter_clauses.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"resolution": resolutions}},
                        {"terms": {"rms.data.default.Dimensions.keyword": resolutions}},
                        {"terms": {"cts.data.default.Dimensions.keyword": resolutions}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    # Orientation filter
    if orientation and len(orientation) > 0:
        filter_clauses.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"orientation": orientation}},
                        {"terms": {"rms.data.metadata.Orientation.keyword": orientation}},
                        {"terms": {"cts.data.metadata.Orientation.keyword": orientation}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    fquery = {
        "size": k,
        "query": {"bool": {"must": must_clauses, "filter": filter_clauses}},
    }
    sort_clause = _build_sort_clause(effective_sort_by, effective_sort_order)
    if sort_clause:
        fquery["sort"] = sort_clause

    print("OpenSearch Query:", fquery)
    response = opensearch_client.search(index=get_videos_read_index(), body=fquery)
    retrieval_ms = int(time.time() * 1000) - retrieval_started

    execution = {
        "normalize_ms": normalize_ms,
        "subquery_ms": 0,
        "retrieval_ms": retrieval_ms,
        "fusion_ms": 0,
        "rerank_ms": 0,
        "blend_ms": 0,
        "total_ms": int(time.time() * 1000) - total_started,
    }

    return {
        "status": "success",
        "mode": "vector" if vector is not None else "fallback_lexical",
        "documents": [hit["_source"] for hit in response["hits"]["hits"]],
        "execution": execution,
    }


def _normalize_sort_order(order: str) -> str:
    if isinstance(order, str) and order.lower() == "asc":
        return "asc"
    return "desc"


def _build_sort_clause(sort_by: str, sort_order: str):
    if not sort_by:
        return None

    sort_key = str(sort_by).strip().lower()
    if sort_key == "views":
        # Sort by the highest available views value from either RMS or CTS payloads.
        return [
            {
                "_script": {
                    "type": "number",
                    "script": {
                        "lang": "painless",
                        "source": (
                            "def r = (doc.containsKey('rms.data.views') && !doc['rms.data.views'].empty) "
                            "? doc['rms.data.views'].value : 0; "
                            "def c = (doc.containsKey('cts.data.views') && !doc['cts.data.views'].empty) "
                            "? doc['cts.data.views'].value : 0; "
                            "return r > c ? r : c;"
                        ),
                    },
                    "order": sort_order,
                }
            }
        ]
    if sort_key == "newest":
        return [{"created_at": {"order": "desc"}}]
    if sort_key == "oldest":
        return [{"created_at": {"order": "asc"}}]
    return None


def _has_ranking_intent(query: str) -> bool:
    if not isinstance(query, str):
        return False
    text = query.strip().lower()
    if not text:
        return False

    ranking_markers = ("trending", "top", "most viewed", "highest viewed", "viral", "popular")
    return any(marker in text for marker in ranking_markers)


def _extract_categories_from_query(query: str) -> list:
    if not isinstance(query, str):
        return []
    text = re.sub(r"[^a-z0-9\s/&-]+", " ", query.lower())
    found = []
    for alias, canonical in _CATEGORY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text):
            if canonical not in found:
                found.append(canonical)
    return found


def _extract_duration_max_from_query(query: str):
    if not isinstance(query, str):
        return None
    text = query.lower()
    patterns = (
        r"\bunder\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
        r"\bless than\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
        r"\bup to\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
        r"\bmax(?:imum)?\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
        r"\b(\d{1,4})\s*(?:s|sec|secs|second|seconds)\s*(?:max|maximum)?\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(int(match.group(1)))
    return None


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

    response = opensearch_client.search(index=get_videos_read_index(), body=query)
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
        index=get_videos_read_index(),
        size=0,
        body={
            "aggs": {
                "unique_categories_rms": {
                    "terms": {
                        "field": "rms.data.keyword.keyword",
                        "size": 1000,
                    }
                },
                "unique_categories_cts": {
                    "terms": {
                        "field": "cts.data.keyword.keyword",
                        "size": 1000,
                    }
                },
                "unique_categories_top_level": {
                    "terms": {
                        "field": "categories",
                        "size": 1000,
                    }
                },
            }
        },
    )

    rms_buckets = response["aggregations"].get("unique_categories_rms", {}).get(
        "buckets", []
    )
    cts_buckets = response["aggregations"].get("unique_categories_cts", {}).get(
        "buckets", []
    )
    top_level_buckets = response["aggregations"].get("unique_categories_top_level", {}).get(
        "buckets", []
    )

    merged_counts = {}
    for bucket in rms_buckets + cts_buckets + top_level_buckets:
        key = bucket.get("key")
        if not key:
            continue
        merged_counts[key] = merged_counts.get(key, 0) + int(bucket.get("doc_count", 0))

    buckets = [
        {"key": key, "doc_count": count}
        for key, count in sorted(merged_counts.items(), key=lambda item: item[1], reverse=True)
    ]
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

    response = opensearch_client.search(index=get_videos_read_index(), body=query)

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
    index_name = get_videos_read_index()

    body = {
        "size": 0,
        "aggs": {
            "locations": {
                "terms": {"field": "location", "size": 1000}
            },
            "durations": {
                "terms": {"field": "duration_sec", "size": 1000}
            },
            "resolutions": {
                "terms": {"field": "resolution", "size": 100}
            },
            "orientation": {
                "terms": {
                    "field": "orientation",
                    "size": 10,
                }
            },
            "tags": {"terms": {"field": "tags", "size": 1000}},
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
