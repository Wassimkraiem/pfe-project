from flask_restx import Resource
from flask import request, abort
from sev.apps.videos.opensearch.documents.services import (
    create_doc,
    search_videos,
    update_document,
    delete_document,
    vector_search,
    get_dynamic_facets,
    keyword_search,
    get_categories,
    get_latest_videos,
    get_facets,
)
from sev.apps.videos.opensearch.documents.schemas import VideoSchema, DeleteSchema
from datetime import datetime
from sev.response import SevResponse
import os
from functools import wraps

API_KEYS = set(filter(None, os.environ.get("API_KEYS", "").split(",")))


def require_api_key():
    key = request.headers.get("X-API-KEY")
    if API_KEYS and (not key or key not in API_KEYS):
        abort(401, description="Invalid or missing API key")


def api_key_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        require_api_key()
        return f(*args, **kwargs)

    return decorated


class VideoDocument(Resource):
    method_decorators = [api_key_required]

    def post(self):
        """Create a new video if it does not exist."""
        video_data = request.get_json()
        schema = VideoSchema()
        validated_data = schema.load(video_data)
        validated_data["timestamp"] = (
            datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        )
        video_id = validated_data["video_id"]
        service_identifier = validated_data["service_identifier"]
        response = create_doc(
            video_id, service_identifier, validated_data["video_data"]
        )
        return SevResponse(response)

    def put(self):
        video_data = request.get_json()
        schema = VideoSchema()
        validated_data = schema.load(video_data)
        video_id = validated_data.get("video_id")
        response = update_document(video_id, validated_data["video_data"])
        return SevResponse(response)

    def delete(self):
        video_data = request.get_json()
        schema = DeleteSchema()
        validated_data = schema.load(video_data)
        video_id = validated_data.get("video_id")
        response = delete_document(video_id)
        return SevResponse(response)


class FiltringDocs(Resource):
    method_decorators = [api_key_required]

    def post(self):
        """Search videos based on query parameters."""
        payload = request.get_json()
        print(f"Payload: {payload}")

        query_params = {}

        for field, value in payload.items():
            if value:
                query_params[field] = value

        print(f"Query parameters: {query_params}")

        query_params = {key: value for key, value in query_params.items() if value}
        offset = request.args.get("offset", default=0, type=int)
        limit = request.args.get("limit", default=10, type=int)
        response = search_videos(query_params, offset, limit)
        return SevResponse(response)


class KeywordFilter(Resource):
    method_decorators = [api_key_required]

    def post(self):
        "keyword based search"
        query = request.get_json()
        keyword = query.get("query")

        results = keyword_search(keyword)

        return SevResponse(results)


class VideoFacets(Resource):
    method_decorators = [api_key_required]

    def get(self):
        """Get facets for video search."""
        facets = get_dynamic_facets()
        return SevResponse(facets)


class VectorSearch(Resource):
    method_decorators = [api_key_required]

    def post(self):
        """Vector + filter-based search"""
        payload = request.get_json()

        query = payload.get("query")
        k = payload.get("k", 5)
        categories = payload.get("categories")
        tags = payload.get("tags")
        duration_min = payload.get("duration_min")
        duration_max = payload.get("duration_max")
        created_date_start = payload.get("created_date_start")  # Changed
        created_date_end = payload.get("created_date_end")  # Changed
        locations = payload.get("locations")
        resolutions = payload.get("resolutions")
        orientation = payload.get("orientation")

        results = vector_search(
            query=query,
            k=k,
            categories=categories,
            tags=tags,
            duration_min=duration_min,
            duration_max=duration_max,
            created_date_start=created_date_start,  # Changed
            created_date_end=created_date_end,  # Changed
            locations=locations,
            resolutions=resolutions,
            orientation=orientation,
        )

        return SevResponse(results)


class GetCategories(Resource):
    method_decorators = [api_key_required]

    def get(self):
        res = get_categories()
        return SevResponse(res)


class GetLatestVideos(Resource):
    method_decorators = [api_key_required]

    def get(self):
        res = get_latest_videos()
        return SevResponse(res)


class getFacets(Resource):
    method_decorators = [api_key_required]

    def get(self):

        res = get_facets()
        return SevResponse(res)
