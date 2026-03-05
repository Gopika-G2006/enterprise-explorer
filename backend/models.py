from pydantic import BaseModel
from typing import Optional, List


class ActivityOut(BaseModel):
    id: int
    nic_code: str
    nic_description: str


class EnterpriseListItem(BaseModel):
    id: int
    enterprise_name: str
    state: Optional[str]
    district: Optional[str]
    pincode: Optional[str]
    description: Optional[str]
    sector: Optional[str]
    categories: Optional[str]


class EnterpriseDetail(BaseModel):
    id: int
    enterprise_name: str
    state: Optional[str]
    district: Optional[str]
    pincode: Optional[str]
    registration_date: Optional[str]
    address: Optional[str]
    description: Optional[str]
    sector: Optional[str]
    categories: Optional[str]
    activities: List[ActivityOut] = []


class PaginatedEnterprises(BaseModel):
    total: int
    page: int
    limit: int
    pages: int
    data: List[EnterpriseListItem]


class StatsResponse(BaseModel):
    total_enterprises: int
    total_districts: int
    total_pincodes: int
    total_nic_codes: int
    by_category: dict
    by_district: dict
    by_pincode: dict
    by_sector: dict


class FiltersResponse(BaseModel):
    districts: List[str]
    pincodes: List[str]
    categories: List[str]
    nic_codes: List[str]


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    data_count: Optional[int] = None
