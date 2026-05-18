from flask_restx import Resource
from flask import request
from sev.apps.videos.opensearch.indexes.services import (
    bootstrap_videos_v2_aliases,
    create_mapping_index,
    delete_index,
    get_mapping,
)
from sev.apps.videos.opensearch.indexes.schemas import (
    BootstrapVideosV2Schema,
    ExpectedIndexSchema,
)

from sev.response import SevResponse


class MappingIndex(Resource):

    def put(self):
        """Create or update the mapping index."""
        schema = ExpectedIndexSchema()
        fields = schema.load(request.get_json())
        index_name = fields["index_name"]
        response = create_mapping_index(index_name)
        return SevResponse(response)


class DeleteIndex(Resource):
    def post(self):
        """Delete the specified index."""
        schema = ExpectedIndexSchema()
        fields = schema.load(request.get_json())
        index_name = fields["index_name"]
        result = delete_index(index_name)
        return SevResponse(result)


class GetIndex(Resource):

    def post(self):
        """Get the mapping of a specific index."""
        schema = ExpectedIndexSchema()
        fields = schema.load(request.get_json())
        index_name = fields["index_name"]
        mapping = get_mapping(index_name)
        return SevResponse(mapping)


class BootstrapVideosV2(Resource):
    def put(self):
        """Create videos_v2 and assign read/write aliases."""
        schema = BootstrapVideosV2Schema()
        payload = schema.load(request.get_json() or {})
        response = bootstrap_videos_v2_aliases(
            index_name=payload["index_name"],
            read_alias=payload["read_alias"],
            write_alias=payload["write_alias"],
            embedding_dimension=payload["embedding_dimension"],
        )
        return SevResponse(response)
