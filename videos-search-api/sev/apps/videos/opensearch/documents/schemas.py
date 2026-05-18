from marshmallow import Schema, fields


class VideoSchema(Schema):
    video_id = fields.Str(required=True)
    service_identifier = fields.Str(required=True)
    video_data = fields.Dict()


class ExpectedIndexSchema(Schema):
    index_name = fields.Str(required=True)


class DeleteSchema(Schema):

    video_id = fields.Str(required=True)


class AdvancedSearchFiltersSchema(Schema):
    categories = fields.List(fields.Str(), load_default=list)
    tags = fields.List(fields.Str(), load_default=list)
    locations = fields.List(fields.Str(), load_default=list)
    resolutions = fields.List(fields.Str(), load_default=list)
    orientation = fields.List(fields.Str(), load_default=list)
    duration_min = fields.Float(load_default=None, allow_none=True)
    duration_max = fields.Float(load_default=None, allow_none=True)
    created_date_start = fields.Int(load_default=None, allow_none=True)
    created_date_end = fields.Int(load_default=None, allow_none=True)


class AdvancedSearchSortSchema(Schema):
    by = fields.Str(load_default="relevance")
    order = fields.Str(load_default="desc")


class AdvancedSearchPaginationSchema(Schema):
    offset = fields.Int(load_default=0)
    limit = fields.Int(load_default=20)


class AdvancedSearchStrategySchema(Schema):
    lex_k = fields.Int(load_default=120)
    vec_k = fields.Int(load_default=120)
    fuse_k = fields.Int(load_default=150)
    rerank_top_n = fields.Int(load_default=40)
    rrf_k = fields.Int(load_default=60)
    top_rank_bonus = fields.Float(load_default=0.10)


class AdvancedSearchRequestSchema(Schema):
    query = fields.Str(load_default="")
    filters = fields.Nested(AdvancedSearchFiltersSchema, load_default=dict)
    sort = fields.Nested(AdvancedSearchSortSchema, load_default=dict)
    pagination = fields.Nested(AdvancedSearchPaginationSchema, load_default=dict)
    strategy = fields.Nested(AdvancedSearchStrategySchema, load_default=dict)
    debug = fields.Bool(load_default=False)
