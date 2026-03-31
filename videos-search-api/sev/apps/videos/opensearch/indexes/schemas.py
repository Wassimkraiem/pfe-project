from marshmallow import Schema, fields, ValidationError, validates


class FieldSchema(Schema):
    field_name = fields.Str(required=True)
    field_type = fields.Str(required=True)

    @validates("field_type")
    def validate_field_type(self, value):
        if value not in ["keyword", "text", "date", "integer", "nested"]:
            raise ValidationError(
                "Invalid field type. Allowed types: 'keyword', 'text', 'date', 'integer', 'nested'"
            )


class IndexSchema(Schema):
    index_name = fields.Str(required=True)
    new_index_name = fields.Str(required=True)
    fields = fields.List(fields.Nested(FieldSchema), required=True)


class ExpectedIndexSchema(Schema):
    index_name = fields.Str(required=True)
