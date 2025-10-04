# Azure App Registration Setup for Device Code Flow

## Problem
The current app registration is configured as a confidential client (web app) which requires client credentials. For device code flow with delegated permissions, we need a public client configuration.

## Solution: Configure as Mobile and Desktop Application

### Steps to Fix in Azure Portal

1. **Go to Azure Portal** → Azure Active Directory → App registrations → Your app (Client ID: 3ee58bdc-e823-462b-af45-65f0ec932645)

2. **Navigate to Authentication**:
   - Click on "Authentication" in the left menu

3. **Add Platform**:
   - Click "Add a platform"
   - Select "Mobile and desktop applications"
   - Check the box for: `https://login.microsoftonline.com/common/oauth2/nativeclient`
   - Click "Configure"

4. **Advanced Settings**:
   - In the "Advanced settings" section of Authentication
   - Find "Allow public client flows"
   - Set it to "Yes"

5. **API Permissions** (should already be configured):
   - Microsoft Graph → Delegated permissions:
     - Files.Read.All
     - Sites.Read.All
   - Click "Grant admin consent" if available (or request admin to do this)

### Alternative: Create New App Registration

If you can't modify the existing app registration, create a new one:

1. **Create New App Registration**:
   - Name: "SharePoint AI Search Sync - Device Flow"
   - Supported account types: "Accounts in this organizational directory only"
   - Redirect URI: Select "Public client/native (mobile & desktop)" 
   - URI: `https://login.microsoftonline.com/common/oauth2/nativeclient`

2. **Configure API Permissions**:
   - Microsoft Graph → Delegated permissions:
     - Files.Read.All
     - Sites.Read.All

3. **Update .env file** with new Client ID

## Testing After Configuration

Once the app registration is properly configured as a public client, the device code flow should work without requiring client secrets.

## Current Error Analysis

Error: `AADSTS7000218: The request body must contain the following parameter: 'client_assertion' or 'client_secret'`

This confirms that Azure AD is treating our app as a confidential client that requires credentials, when it should be a public client for device code flow.