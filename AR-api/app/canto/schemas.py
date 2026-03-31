from pydantic import BaseModel, EmailStr


class CantoBasicGroupRemovalRequest(BaseModel):
    email: EmailStr
