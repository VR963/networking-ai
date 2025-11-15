"""
Company Admin User Model.

Admin users who manage company account.
NOT hiring managers - pure administrators.
NOT in AI network - backend management only.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from ..database import Base


class CompanyAdminUser(Base):
    """
    Company Admin User model.

    Separate account for company administration.
    - NOT in AI network
    - NOT talent or hiring manager
    - Pure management role
    - Unique login key
    - Unique UI

    Example: Sarah can be:
    - sarah@company.com (Hiring Manager) - Key: HM_xyz123
    - sarah@company.com (Admin) - Key: ADMIN_abc456
    """
    __tablename__ = "company_admin_users"
    __table_args__ = {'extend_existing': True}

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Links
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Can reuse email
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    # Admin identity
    admin_key = Column(String(255), unique=True, nullable=False, index=True)  # Unique login key
    admin_name = Column(String(255))  # Display name for admin role

    # Permissions
    permissions = Column(JSON)  # {"manage_seats": true, "view_analytics": true, ...}
    """
    Permissions:
    - manage_seats: Allocate/deallocate seats
    - view_analytics: View company metrics
    - manage_billing: Handle subscription payments
    - manage_hiring_managers: Add/remove hiring managers
    - export_data: Export company data
    """

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)

    # Relationships
    user = relationship("User")
    company = relationship("Company", back_populates="admin_users", overlaps="admin_users,company")

    def __repr__(self):
        return f"<CompanyAdminUser(id={self.id}, company_id={self.company_id}, key={self.admin_key})>"

    def has_permission(self, permission: str) -> bool:
        """Check if admin has specific permission."""
        if not self.permissions:
            return False
        return self.permissions.get(permission, False)

    def grant_permission(self, permission: str):
        """Grant a permission to admin."""
        if not self.permissions:
            self.permissions = {}
        self.permissions[permission] = True

    def revoke_permission(self, permission: str):
        """Revoke a permission from admin."""
        if self.permissions and permission in self.permissions:
            self.permissions[permission] = False

    def record_login(self):
        """Record admin login."""
        self.last_login_at = datetime.utcnow()
