# Implementation Plan — Google Authentication & User Preferences

This plan outlines the steps to add Google OAuth2 authentication and migrate from global settings to per-user settings stored in S3.

## 1. Prerequisites (User Action)
To enable Google Login, you will need to:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project called `Market Analyser`.
3. Go to **APIs & Services > OAuth consent screen** and configure it for "External".
4. Go to **Credentials > Create Credentials > OAuth client ID**.
   - **Application type**: Web application.
   - **Authorized redirect URIs**: `http://localhost:4200` (for local dev) and your CloudFront/S3 URL.
5. Save the **Client ID** and **Client Secret**.

## 2. Backend Changes (FastAPI)
- **Dependencies**: Add `authlib`, `python-jose`, and `python-multipart` to `requirements.txt`.
- **Environment Variables**: Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to Lambda configuration.
- **Auth Module**: 
  - Create `auth.py` to handle JWT generation and Google token verification.
  - Implement a `get_current_user` dependency for protected routes.
- **Config Loader Refactor**:
  - Update `load_config`, `save_instruments`, and `save_settings` to accept a `user_id`.
  - Storage path in S3 will change from `instruments.yaml` to `users/{user_id}/config.yaml`.
- **Endpoints**:
  - Add `/api/auth/token` for exchanging Google auth tokens for our local JWT.

## 3. Frontend Changes (Angular)
- **Authentication**:
  - Install `@abacritt/angularx-social-login`.
  - Add a `Login` component with a Google login button.
  - Create an `AuthInterceptor` to automatically add the JWT Bearer token to all API requests.
- **State Management**:
  - Store user info in a `UserService` to update the UI (show user profile pic/name).
- **User Experience**:
  - Show a "Please login" overlay if trying to access settings while signed out.

## 4. Infrastructure Changes (Terraform)
- Update `lambda.tf` to include Google OAuth environment variables.

## 5. How to Deploy with Secrets (IMPORTANT)
Once you have your credentials from the Google Cloud Console, you need to pass them to Terraform when you apply. Run this command:

```powershell
.\terraform.exe apply -auto-approve `
  -var="aws_account_id=614686365382" `
  -var="backend_image=614686365382.dkr.ecr.ap-southeast-1.amazonaws.com/market-analyser-backend:latest" `
  -var="google_client_id=YOUR_GOOGLE_CLIENT_ID" `
  -var="google_client_secret=YOUR_GOOGLE_CLIENT_SECRET"
```

*Note: The `jwt_secret_key` has a default value, but you can also override it for extra security using `-var="jwt_secret_key=YOUR_RANDOM_LONG_STRING"`. If you ever change this, all users will be logged out.*

## 6. Timeline
1. **Phase 1**: S3 Multi-user refactor (COMPLETED).
2. **Phase 2**: Backend Google Auth integration (COMPLETED).
3. **Phase 3**: Frontend Login implementation (COMPLETED).
4. **Phase 4**: Terraform Infrastructure update (COMPLETED).
5. **Phase 5**: Verification & Cleanup (Ready for your secrets!).
