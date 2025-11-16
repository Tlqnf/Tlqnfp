from pydantic import BaseModel


class PurchaseVerificationRequest(BaseModel):
    purchase_token: str
    product_id: str
    package_name: str
