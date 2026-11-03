from pydantic import BaseModel, ConfigDict


class LocationOut(BaseModel):
    # built from the Location model returned by the services
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
