from pydantic import BaseModel, ConfigDict


class ColorOut(BaseModel):
    # built from the Color model returned by the services
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
