from enum import Enum


class AccountType(str, Enum):
    INDIVIDUAL = "individual"
    BUSINESS = "business"
