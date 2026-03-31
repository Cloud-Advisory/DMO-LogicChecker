resource "random_uuid" "app_id_user" {}
resource "random_uuid" "app_id_admin" {}

resource "azuread_application" "this" {
  display_name = "appreg-${var.name_prefix}"
  owners       = [data.azuread_client_config.current.object_id]
  app_role {
    allowed_member_types = ["User"]
    description          = "Admins have also access to UI and Admin Portal"
    display_name         = "Admin"
    enabled              = true
    id                   = random_uuid.app_id_user.id
    value                = "DMO.Admin"
  }

  app_role {
    allowed_member_types = ["User"]
    description          = "User have access to UI"
    display_name         = "User"
    enabled              = true
    id                   = random_uuid.app_id_admin.id
    value                = "DMO.User"
  }
  web {
    redirect_uris = ["https://${local.web_app_name}.azurewebsites.net/.auth/login/aad/callback"]
    homepage_url  = "https://${local.web_app_name}.azurewebsites.net/"
    implicit_grant {
      access_token_issuance_enabled = false
      id_token_issuance_enabled     = true
    }
  }
  api {
    oauth2_permission_scope {
      admin_consent_description  = "Allow the application to access example on behalf of the signed-in user."
      admin_consent_display_name = "Access example"
      enabled                    = true
      id                         = "96183846-204b-4b43-82e1-5d2222eb4b9b"
      type                       = "User"
      user_consent_description   = "Allow the application to access example on your behalf."
      user_consent_display_name  = "Access example"
      value                      = "user_impersonation"
    }
  }
}

# add secret in appreg
resource "azuread_application_password" "this" {
  application_id = azuread_application.this.id
  display_name   = "WebApp-${local.web_app_name}"
}

# Enterprise Application (Service Principal)
resource "azuread_service_principal" "this" {
  client_id    = azuread_application.this.client_id
  use_existing = true

  app_role_assignment_required = true # Assignment required = yes
}


# Create groups for role assignment
resource "azuread_group" "users" {
  display_name     = "DMO-TF-Users"
  security_enabled = true
}

resource "azuread_group" "admins" {
  display_name     = "DMO-TF-Admins"
  security_enabled = true
}

# Add Groups with App Roles to Enterprise Application
resource "azuread_app_role_assignment" "user" {
  app_role_id         = azuread_service_principal.this.app_role_ids["DMO.User"]
  principal_object_id = azuread_group.users.object_id
  resource_object_id  = azuread_service_principal.this.object_id
}

resource "azuread_app_role_assignment" "admin" {
  app_role_id         = azuread_service_principal.this.app_role_ids["DMO.Admin"]
  principal_object_id = azuread_group.admins.object_id
  resource_object_id  = azuread_service_principal.this.object_id
}

# Assign deploying principal to admin group so that they have access to the web app
resource "azuread_group_member" "deploying_principal" {
  group_object_id  = azuread_group.admins.object_id
  member_object_id = var.deploying_principal_object_id
}
