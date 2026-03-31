from typing import List
from functools import wraps
from flask import Blueprint, request, abort, jsonify
from pydantic import BaseModel, Field, ValidationError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import jwt
import logging
import base64
import json

from config import settings
from dependencies import get_registry_repository
from services.registry import AzureTableStorageRepository

# Configure logging
logger = logging.getLogger(__name__)

router = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


class RouteRecord(BaseModel):
    """Data model for a route record."""
    token: str = Field(..., min_length=1, max_length=256)
    action: str = Field(..., min_length=1, max_length=256)
    prompt: str | None = Field(default=None, max_length=8000)
    endpoint: str | None = Field(default=None, max_length=512)
    api_key: str | None = Field(default=None, max_length=512)


class UpsertRouteRequest(RouteRecord):
    """Request model for upserting a route."""
    pass


def _require_admin_role(f):
    """Decorator to enforce admin role authorization on endpoints.
    
    Checks the X-MS-CLIENT-PRINCIPAL header for user roles and verifies
    that the user has the 'DMO.Admin' role.
    
    Returns:
        401: If principal header is missing or token is invalid
        403: If user lacks the required DMO.Admin role
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Extract base64-encoded principal from request headers
            auth_me_response = request.headers.get("X-MS-CLIENT-PRINCIPAL")
            if not auth_me_response:
                logger.warning("Admin endpoint accessed without principal header")
                abort(401, description="Unable to retrieve user roles")
            
            # Decode principal and extract roles
            decoded_principal = json.loads(base64.b64decode(auth_me_response))
            roles = [claim["val"] for claim in decoded_principal.get("claims", []) 
                    if claim.get("typ") == "roles"]
            
            # Verify admin role
            if "DMO.Admin" not in roles:
                logger.warning(f"Unauthorized admin access attempt with roles: {roles}")
                abort(403, description="User does not have Admin role")
            
            logger.info("Admin authorization successful")
        except Exception as e:
            logger.error(f"Authorization validation failed: {str(e)}")
            abort(401, description="Invalid token or unable to verify roles")
        
        return f(*args, **kwargs)
    return decorated_function


@router.route("/routes", methods=["GET"])
@_require_admin_role
def list_routes():
    """Retrieve all routes with a limit of 500 items.
    
    Returns:
        list: JSON list of RouteRecord objects
    """
    logger.debug("Fetching all routes")
    registry: AzureTableStorageRepository = get_registry_repository()
    items = registry.list_routes(limit=500)
    logger.info(f"Retrieved {len(items)} routes")
    return jsonify([RouteRecord(**item).model_dump() for item in items])


@router.route("/routes", methods=["POST"])
@_require_admin_role
def upsert_route():
    """Create or update a route.
    
    Returns:
        RouteRecord: The created/updated route
        400: If JSON body is invalid or validation fails
    """
    # Validate request JSON
    payload = request.get_json(silent=True)
    if payload is None:
        logger.warning("Upsert route request with invalid/missing JSON body")
        abort(400, description="Invalid or missing JSON body")

    # Parse and validate request
    try:
        req = UpsertRouteRequest.model_validate(payload)
    except ValidationError as e:
        logger.warning(f"Route validation failed: {e.errors()}")
        return jsonify({"detail": e.errors()}), 400

    # Upsert route in registry
    registry: AzureTableStorageRepository = get_registry_repository()
    record = registry.upsert_route(
        token=req.token.strip(),
        action=req.action.strip(),
        prompt=(req.prompt or "").strip() or None,
        endpoint=(req.endpoint or "").strip() or None,
        api_key=(req.api_key or "").strip() or None,
    )
    logger.info(f"Route upserted: token={req.token}, action={req.action}")
    return jsonify(RouteRecord(**record).model_dump())


@router.route("/routes/<token>/<action>", methods=["DELETE"])
@_require_admin_role
def delete_route(token: str, action: str):
    """Delete a route by token and action.
    
    Args:
        token: Route token identifier
        action: Route action name
        
    Returns:
        dict: Confirmation message
        404: If route not found
    """
    logger.debug(f"Deleting route: token={token}, action={action}")
    registry: AzureTableStorageRepository = get_registry_repository()
    deleted = registry.delete_route(token=token, action=action)
    
    if not deleted:
        logger.warning(f"Delete route not found: token={token}, action={action}")
        abort(404, description="Route not found")
    
    logger.info(f"Route deleted: token={token}, action={action}")
    return jsonify({"deleted": True})


@router.route("/test", methods=["GET"])
@_require_admin_role
def test_response():
    """Health check endpoint for admin API.
    
    Returns:
        dict: Simple confirmation message
    """
    logger.debug("Admin API test endpoint called")
    return {"message": "Admin API is working!"}
