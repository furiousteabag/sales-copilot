from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class ProfileType(str, Enum):
    person = "person"
    company = "company"


class CurrentCompany(BaseModel):
    name: Optional[str]
    link: Optional[str]


class Experience(BaseModel):
    title: Optional[str]
    subtitle: Optional[str]
    subtitleURL: Optional[str]
    location: Optional[str]
    description: Optional[str]
    duration: str
    start_date: Optional[str]
    end_date: Optional[str]
    duration_short: Optional[str]


class Education(BaseModel):
    title: Optional[str]
    degree: Optional[str]
    field: Optional[str]
    meta: Optional[str]
    url: str
    start_year: Optional[str]
    end_year: Optional[str]


class Activity(BaseModel):
    title: str
    attribution: str
    img: str
    link: str


class PersonProfile(BaseModel):
    name: str
    position: Optional[str]
    current_company: CurrentCompany
    avatar: str
    about: Optional[str]
    city: str
    educations_details: Optional[str]
    posts: List
    experience: List[Experience]
    education: List[Education]
    activities: List[Activity]


class CompanyProfile(BaseModel):
    url: str
    name: str
    slogan: Optional[str]
    about: Optional[str]
    website: str
    Headquarters: Optional[str]
