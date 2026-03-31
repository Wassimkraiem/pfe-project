from flask import Blueprint
from flask_restx import Api
from sev.apps.videos.opensearch.indexes.resources import (
    MappingIndex,
    DeleteIndex,
    GetIndex,
)


blueprint = Blueprint("indexes_blueprint", __name__, url_prefix="/indexes")
api = Api(blueprint)


api.add_resource(MappingIndex, "/")
api.add_resource(DeleteIndex, "/delete")
api.add_resource(GetIndex, "/index")
