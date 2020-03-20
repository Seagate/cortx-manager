from csm.core.blogic.models import CsmModel
from schematics.types import StringType, DateTimeType
from datetime import timezone


class CommentModel(CsmModel):
    comment_id = StringType()
    comment_text = StringType()
    created_time = DateTimeType()
    created_by = StringType()

    def to_primitive(self) -> dict:
        obj = super().to_primitive()

        if self.created_time:
            obj["created_time"] =\
                    int(self.created_time.replace(tzinfo=timezone.utc).timestamp())
        return obj

    def __hash__(self):
        return hash(self.comment_id)
