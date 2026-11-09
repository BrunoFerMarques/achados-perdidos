from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    # built from the Category model returned by the services
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
