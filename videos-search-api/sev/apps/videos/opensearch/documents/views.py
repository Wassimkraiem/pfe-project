from flask import Blueprint
from flask_restx import Api
from sev.apps.videos.opensearch.documents.resources import (
    FiltringDocs,
    VideoDocument,
    KeywordFilter,
    VideoFacets,
    VectorSearch,
    GetCategories,
    GetLatestVideos,
    getFacets,
)


blueprint = Blueprint("videos_blueprint", __name__, url_prefix="/api/videos")
api = Api(blueprint)

api.add_resource(FiltringDocs, "/query")
api.add_resource(VideoDocument, "/")
api.add_resource(KeywordFilter, "/search")
api.add_resource(VectorSearch, "/vsearch")
# api.add_resource(VideoFacets, "/facets")
api.add_resource(GetCategories, "/categories")
api.add_resource(GetLatestVideos, "/getlatest")
api.add_resource(getFacets, "/facets")
