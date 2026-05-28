from typing import TypedDict, Any, Optional
from bson import ObjectId
from datetime import datetime

class UserSchema(TypedDict):
    """
    Schema for the 'users' collection.
    """
    _id: ObjectId          # PK: Primary Key
    name: str              # User's full name
    phone: str             # User's phone number
    locale: str            # Locale (e.g., 'es-AR', 'en-US')
    created_at: datetime   # Timestamp when the user was created

class PropertySchema(TypedDict):
    """
    Schema for the 'properties' collection.
    Each property belongs to a user (1-to-many relationship).
    """
    _id: ObjectId          # PK: Primary Key
    user_id: UserSchema['_id']  # FK: Bound to UserSchema._id type
    name: str              # Name of the property (e.g., 'Departamento Palermo', 'Oficina')
    type: str              # Type of property (e.g., 'apartment', 'house', 'commercial')
    address: str           # Street address
    city: str              # City
    active: bool           # Is the property currently active/tracked?

class ServiceSchema(TypedDict):
    """
    Schema for the 'services' collection.
    Services are configured by a user and optionally tied to a property.
    """
    _id: ObjectId          # PK: Primary Key
    user_id: UserSchema['_id']      # FK: Bound to UserSchema._id type
    name: str              # Name of the service (e.g., 'Luz', 'Expensas', 'Abl')
    category: str          # Service category (e.g., 'utilities', 'taxes', 'maintenance')
    provider: str          # Provider name (e.g., 'Edesur', 'Metrogas')
    property_id: PropertySchema['_id']  # FK: Bound to PropertySchema._id type
    account_number: str    # Customer or account number with the provider
    default_due_day: int   # Day of month when payment is usually due (e.g., 10)
    active: bool           # Is the service active?

class PaymentSchema(TypedDict):
    """
    Schema for the 'payments' collection.
    Tracks each individual expense/payment, linked to a user, service, and property.
    """
    _id: ObjectId          # PK: Primary Key
    user_id: UserSchema['_id']      # FK: Bound to UserSchema._id type
    service_id: ServiceSchema['_id']   # FK: Bound to ServiceSchema._id type
    property_id: PropertySchema['_id']  # FK: Bound to PropertySchema._id type
    amount: float          # Amount to pay / paid (supports int/float)
    currency: str          # Currency code (e.g., 'ARS', 'USD')
    payment_date: Optional[datetime]  # Date when the payment was actually made
    due_date: datetime     # Due date of the payment
    status: str            # Current status (e.g., 'pending', 'paid', 'overdue')
    period: str            # Billing period (e.g., '2026-05', 'May 2026')
    input_method: str      # How the payment was loaded (e.g., 'whatsapp', 'manual', 'email')
    notes: Optional[str]   # Any extra user notes
    metadata: dict[str, Any]      # Extra system/integrations metadata
    ai_extracted: dict[str, Any]  # Key-value pairs extracted by the AI agent
    created_at: datetime   # Timestamp of creation in the system