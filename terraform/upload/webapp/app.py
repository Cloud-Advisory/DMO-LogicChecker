"""
Flask application for medical documentation analysis using Azure Foundry LLM.
Provides endpoints for analyzing clinical text with role-based access control.
"""

from fileinput import filename
import logging
import json
import base64
from functools import wraps

from flask import Flask, jsonify, render_template, request, make_response, abort
from flask_cors import CORS
from pydantic import BaseModel, Field, ValidationError

from config import settings
from dependencies import get_llm_client, get_registry_repository, get_secret_provider
from routers import admin as admin_routes 
from services.llm_client import AzureFoundryClient
from services.registry import AzureTableStorageRepository
from services.secret_provider import SecretProvider

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config["APPLICATION_ROOT"] = "/"

# Register admin blueprint
try:
    app.register_blueprint(admin_routes.router)
    logger.info("Admin blueprint registered successfully")
except Exception as e:
    logger.debug("No admin blueprint registered: %s", str(e))

# Configure CORS
allowed_origins = settings.allowed_origins or []
if not allowed_origins:
    logger.warning("No ALLOWED_ORIGINS configured; defaulting to fail-closed CORS policy")
else:
    logger.info("Allowing CORS from: %s", allowed_origins)
CORS(app, origins=allowed_origins, supports_credentials=settings.cors_allow_credentials)

# Security headers
SECURITY_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
}


@app.after_request
def apply_security_headers(response):
    """Apply security headers to all responses."""
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response


class AnalyzeRequest(BaseModel):
    """Request model for text analysis endpoint."""
    text: str = Field(..., min_length=1, max_length=8000)
    action: str = Field(..., min_length=1, max_length=128)
    fairytale: bool = Field(default=False)


class AnalyzeResponse(BaseModel):
    """Response model for analysis results."""
    analysis: str


# Prompt templates
DEFAULT_PROMPT = (
    "You are a medical documentation assistant supporting clinicians. "
    "Return well-structured German text, preserve clinical accuracy, and never invent data."
)

FAIRYTALE_TRIGGER = "show me the fairytale"
FAIRYTALE_PROMPT = (
    "You are a creative medical storyteller. Detect the user's language and respond in that language. "
    "Write a short, uplifting fairytale inspired by the provided clinical text. Mention relevant medical themes "
    "without exposing personal data, keep the tone hopeful, and conclude with a reassuring sentence."
)


def _extract_bearer_token(authorization_header: str | None) -> str:
    """
    Extract and validate Bearer token from Authorization header.
    
    Args:
        authorization_header: The Authorization header value
        
    Returns:
        Validated token string or Flask error response
        
    Raises:
        Returns 401 response if header missing or invalid
    """
    if not authorization_header:
        logger.warning("Missing Authorization header")
        return make_response(jsonify({"error": "Missing Authorization header"}), 401)

    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        logger.warning("Invalid Authorization header format")
        return make_response(jsonify({"error": "Invalid Authorization header"}), 401)
    
    return token.strip()


def _require_admin_role(f):
    """
    Decorator to enforce DMO.Admin role requirement.
    Extracts roles from X-MS-CLIENT-PRINCIPAL header.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_principal = request.headers.get("X-MS-CLIENT-PRINCIPAL")
            if not auth_principal:
                logger.warning("Missing X-MS-CLIENT-PRINCIPAL header")
                abort(401, description="Unable to retrieve user roles")
            
            decoded_principal = json.loads(base64.b64decode(auth_principal))
            roles = [claim["val"] for claim in decoded_principal.get("claims", []) 
                    if claim.get("typ") == "roles"]
            
            if "DMO.Admin" not in roles:
                logger.warning("User lacks DMO.Admin role. Available roles: %s", roles)
                abort(403, description="User does not have Admin role")
            
            logger.info("Admin authorization successful")
        except Exception as e:
            logger.exception("Token verification failed: %s", str(e))
            abort(401, description="Invalid token or unable to verify roles")
        
        return f(*args, **kwargs)
    return decorated_function


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "region": settings.app_region})


@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
def index():
    """Render main index page."""
    return render_template("index.html")


@app.route("/admin", methods=["GET"])
@_require_admin_role
def admin():
    """Render admin page (requires DMO.Admin role)."""
    return render_template("admin.html")


@app.route("/runtime.config.json", methods=["GET"])
def runtime_config():
    """Serve runtime configuration."""
    try:
        with open("runtime.config.json", "r") as f:
            config_data = f.read()
        logger.debug("Runtime config served successfully")
        return jsonify(json.loads(config_data))
    except FileNotFoundError:
        logger.error("runtime.config.json not found")
        return make_response(jsonify({"error": "Configuration not found"}), 404)
    except json.JSONDecodeError:
        logger.error("runtime.config.json is invalid JSON")
        return make_response(jsonify({"error": "Invalid configuration"}), 500)


@app.route("/metadata", methods=["GET"])
def metadata():
    """Serve application metadata."""
    return jsonify(
        {
            "region": settings.app_region,
            "identityMode": settings.identity_mode,
            "staticBaseUrl": settings.static_base_url,
        }
    )


@app.route("/api/v1/analyze", methods=["POST"])
def analyze():
    """
    Analyze clinical text using Azure Foundry LLM.
    
    Requires:
        - Valid Bearer token in Authorization header
        - JSON payload with text, action, and optional fairytale fields
        
    Returns:
        JSON response with analysis result or error
    """
    try:
        payload_dict = request.get_json(force=True)
        logger.debug("Received analysis request")
    except Exception as e:
        logger.warning("Invalid JSON payload: %s", str(e))
        return make_response(jsonify({"error": "Invalid JSON payload"}), 400)

    try:
        payload = AnalyzeRequest.model_validate(payload_dict)
    except ValidationError as ve:
        logger.warning("Validation error: %s", ve.errors())
        return make_response(jsonify({"error": ve.errors()}), 400)

    # Extract and validate bearer token
    auth_header = request.headers.get("Authorization")
    token_or_response = _extract_bearer_token(auth_header)
    if isinstance(token_or_response, tuple) or hasattr(token_or_response, "status_code"):
        return token_or_response
    token = token_or_response

    # Resolve dependencies per-request
    registry: AzureTableStorageRepository = get_registry_repository()
    llm_client: AzureFoundryClient = get_llm_client()
    secrets: SecretProvider = get_secret_provider()

    # Authenticate token/action combination
    route = registry.fetch_route(token, payload.action)
    if not route:
        logger.warning("Unauthorized token/action combination: action=%s", payload.action)
        return make_response(jsonify({"error": "Token/action combination is not authorized"}), 403)

    # Determine prompt and prepare request
    prompt = route.get("prompt") or secrets.get_secret(
        settings.prompt_secret_name,
        fallback_env="PROMPT_TEMPLATE",
        default=DEFAULT_PROMPT,
    )

    fairytale_requested = payload.fairytale or (FAIRYTALE_TRIGGER in payload.text.lower())
    active_prompt = FAIRYTALE_PROMPT if fairytale_requested else (prompt or DEFAULT_PROMPT)
    user_text = payload.text.replace(FAIRYTALE_TRIGGER, "").strip()
    
    api_key_override = route.get("api_key")
    if isinstance(api_key_override, bytes):
        api_key_override = api_key_override.decode("utf-8")
    endpoint_override = route.get("endpoint")

    # Call LLM
    try:
        logger.info("Invoking LLM for action: %s", payload.action)
        analysis = llm_client.run_completion(
            prompt=active_prompt,
            user_text=user_text or payload.text,
            endpoint_override=endpoint_override,
            api_key_override=api_key_override,
        )
        logger.info("LLM analysis completed successfully")
    except Exception as e:
        logger.exception("Azure Foundry call failed: %s", str(e))
        return make_response(jsonify({"error": "LLM processing failed"}), 502)

    response_model = AnalyzeResponse(analysis=analysis)
    return jsonify(response_model.model_dump())

@app.route("/api/v1/upload", methods=["POST"])
def upload_file():
    # open the uploaded file and read its contents

    print(request.files)
    payload = request.form.to_dict()
    if 'file' not in request.files:
        logger.warning("No file part in the request")
        return make_response(jsonify({"error": "No file part in the request"}), 400)
    file = request.files['file']
    if file.filename == '':
        logger.warning("No selected file")
        return make_response(jsonify({"error": "No selected file"}), 400)
    
    file_contents = ""
    if file.filename.endswith('.txt'):
        file_contents = file.read().decode('utf-8')
    elif file.filename.endswith('.pdf'):
        # Parse PDF files using PyPDF2
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(file)
            file_contents = "\n".join([page.extract_text() for page in reader.pages])
        except ImportError:
            logger.error("PyPDF2 library is not installed. PDF parsing will not work.")
            file_contents = "PDF content parsing not implemented (missing PyPDF2 library)."
    elif file.filename.endswith('.docx'):
        #  Parse DOCX files using python-docx
        try:
            from docx import Document
            document = Document(file)
            file_contents = "\n".join([para.text for para in document.paragraphs])
        except ImportError:
            logger.error("python-docx library is not installed. DOCX parsing will not work.")
            file_contents = "DOCX content parsing not implemented (missing python-docx library)."
    
    else:
        logger.warning("Unsupported file type: %s", file.filename)
        return make_response(jsonify({"error": "Unsupported file type"}), 400)

    print("Received file: %s (%d bytes)" % (file.filename, len(file_contents)))
    print("File contents (first 500 chars): %s" % file_contents[:500])

    # Extract and validate bearer token
    auth_header = request.headers.get("Authorization")
    print("Authorization header: %s" % auth_header)
    token_or_response = _extract_bearer_token(auth_header)
    if isinstance(token_or_response, tuple) or hasattr(token_or_response, "status_code"):
        return token_or_response
    token = token_or_response

    # Resolve dependencies per-request
    registry: AzureTableStorageRepository = get_registry_repository()
    llm_client: AzureFoundryClient = get_llm_client()
    secrets: SecretProvider = get_secret_provider()

    # Authenticate token/action combination
    route = registry.fetch_route(token, payload.get('action'))
    if not route:
        logger.warning("Unauthorized token/action combination: action=%s", payload.get('action'))
        return make_response(jsonify({"error": "Token/action combination is not authorized"}), 403)

    # Determine prompt and prepare request
    prompt = route.get("prompt") or secrets.get_secret(
        settings.prompt_secret_name,
        fallback_env="PROMPT_TEMPLATE",
        default=DEFAULT_PROMPT,
    )

    fairytale_requested = False
    active_prompt = FAIRYTALE_PROMPT if fairytale_requested else (prompt or DEFAULT_PROMPT)
    user_text = file_contents

    api_key_override = route.get("api_key")
    if isinstance(api_key_override, bytes):
        api_key_override = api_key_override.decode("utf-8")
    endpoint_override = route.get("endpoint")

    # Call LLM
    try:
        logger.info("Invoking LLM for action: %s", payload.action)
        analysis = llm_client.run_completion(
            prompt=active_prompt,
            user_text=user_text or payload.text,
            endpoint_override=endpoint_override,
            api_key_override=api_key_override,
        )
        logger.info("LLM analysis completed successfully")
    except Exception as e:
        logger.exception("Azure Foundry call failed: %s", str(e))
        return make_response(jsonify({"error": "LLM processing failed"}), 502)

    response_model = AnalyzeResponse(analysis=analysis)
    return jsonify(response_model.model_dump())


if __name__ == "__main__":
    logger.info("Starting Flask application on 0.0.0.0:8000")
    app.run(host="0.0.0.0", debug=True, port=8000)
