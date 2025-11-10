"""
Mobile Device Management Router.

Endpoints:
- POST / - Register device for push notifications
- GET / - List user's registered devices
- DELETE /{device_id} - Unregister device
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from ...database import get_db
from ...models.user import User
from ...models.mobile import MobileDevice
from .schemas import DeviceInfo, DeviceResponse, DeviceListResponse
from .responses import create_success_response, create_error_response, ErrorCode
from .dependencies import mobile_auth_required

devices_router = APIRouter()


@devices_router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_device(
    device_info: DeviceInfo,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Register device for push notifications.

    If device already exists, updates its information.
    """
    # Check if device already exists
    device = db.query(MobileDevice).filter(
        MobileDevice.device_id == device_info.device_id
    ).first()

    if device:
        # Update existing device
        device.user_id = user.id
        device.platform = device_info.platform.value
        device.push_token = device_info.push_token
        device.app_version = device_info.app_version
        device.os_version = device_info.os_version
        device.is_active = True
        device.last_active = datetime.utcnow()
        device.updated_at = datetime.utcnow()

        message = "Device updated successfully"
    else:
        # Create new device
        device = MobileDevice(
            user_id=user.id,
            device_id=device_info.device_id,
            platform=device_info.platform.value,
            push_token=device_info.push_token,
            app_version=device_info.app_version,
            os_version=device_info.os_version,
            is_active=True,
            last_active=datetime.utcnow()
        )
        db.add(device)
        message = "Device registered successfully"

    db.commit()
    db.refresh(device)

    device_response = DeviceResponse(
        id=device.id,
        device_id=device.device_id,
        platform=device.platform,
        app_version=device.app_version,
        is_active=device.is_active,
        last_active=device.last_active,
        created_at=device.created_at
    )

    return create_success_response(
        data=device_response.model_dump(),
        self_link=f"/api/v1/mobile/devices"
    )


@devices_router.get("/", response_model=dict)
async def list_devices(
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    List user's registered devices.

    Returns all devices associated with the authenticated user.
    """
    devices = db.query(MobileDevice).filter(
        MobileDevice.user_id == user.id
    ).order_by(MobileDevice.last_active.desc()).all()

    device_responses = [
        DeviceResponse(
            id=device.id,
            device_id=device.device_id,
            platform=device.platform,
            app_version=device.app_version,
            is_active=device.is_active,
            last_active=device.last_active,
            created_at=device.created_at
        )
        for device in devices
    ]

    return create_success_response(
        data=device_responses,
        self_link="/api/v1/mobile/devices"
    )


@devices_router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device(
    device_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Unregister device.

    Marks device as inactive and revokes associated refresh tokens.
    """
    # Find device
    device = db.query(MobileDevice).filter(
        MobileDevice.device_id == device_id,
        MobileDevice.user_id == user.id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                code=ErrorCode.NOT_FOUND,
                message="Device not found"
            )
        )

    # Mark device as inactive
    device.is_active = False
    device.updated_at = datetime.utcnow()

    # Revoke all refresh tokens for this device
    from ...models.mobile import RefreshToken
    tokens = db.query(RefreshToken).filter(
        RefreshToken.device_id == device_id,
        RefreshToken.is_revoked == False
    ).all()

    for token in tokens:
        token.is_revoked = True
        token.revoked_at = datetime.utcnow()

    db.commit()
    return None  # 204 No Content
