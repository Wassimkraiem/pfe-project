from marshmallow import Schema, fields


class VideoSchema(Schema):
    video_id = fields.Str(required=True)
    service_identifier = fields.Str(required=True)
    video_data = fields.Dict()


class ExpectedIndexSchema(Schema):
    index_name = fields.Str(required=True)


class DeleteSchema(Schema):

    video_id = fields.Str(required=True)
