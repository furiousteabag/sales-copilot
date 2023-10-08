from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, validator


class ProfileType(str, Enum):
    profile = "profile"
    company = "company"


class Experience(BaseModel):
    position: str
    company_name: Optional[str]
    company_url: Optional[str]
    summary: Optional[str]


class PersonProfile(BaseModel):
    fullName: str
    headline: Optional[str]
    about: Optional[str]
    location: Optional[str]
    experience: List[Experience]

    @validator("experience", pre=True)
    def drop_old_positions(cls, v):
        return [e for e in v][:3]


class CompanyProfile(BaseModel):
    company_name: str
    tagline: Optional[str]
    about: Optional[str]
    website: str
    headquarters: Optional[str]
