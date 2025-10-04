@echo off
REM Quick setup script for SharePoint to Azure AI Search Sync

echo SharePoint to Azure AI Search Sync - Quick Setup
echo ================================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo ✓ Python found

REM Check if pip is available
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pip is not available
    pause
    exit /b 1
)

echo ✓ pip found

REM Install requirements
echo.
echo Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo ✓ Dependencies installed

REM Check if .env exists
if not exist ".env" (
    echo.
    echo Creating .env configuration file...
    copy .env.template .env >nul
    echo ✓ Created .env file from template
    echo.
    echo IMPORTANT: Please edit .env file with your Azure and SharePoint configuration
    echo Required settings:
    echo   - TENANT_ID: Your Azure AD tenant ID
    echo   - CLIENT_ID: Your Azure AD app client ID  
    echo   - SITE_ID: Your SharePoint site ID
    echo   - DRIVE_ID: Your SharePoint drive ID
    echo   - FOLDER_PATH: SharePoint folder path to sync
    echo   - AZ_STORAGE_URL: Azure Storage account URL
    echo   - AZ_CONTAINER: Azure Storage container name
    echo   - Note: App registration needs Storage Blob Data Contributor role
    echo   - SEARCH_SERVICE_NAME: Azure AI Search service name
    echo   - SEARCH_API_KEY: Azure AI Search admin key
    echo   - SEARCH_ENDPOINT: Azure AI Search endpoint URL
    echo   - AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint (required)
    echo   - AZURE_OPENAI_API_KEY: Azure OpenAI API key (required)
    echo   - AZURE_OPENAI_EMBEDDING_MODEL: Embedding model name (default: text-embedding-3-small)
) else (
    echo ✓ .env file already exists
)

echo.
echo Setup complete! Next steps:
echo.
echo 1. Edit .env file with your configuration
echo 2. Check configuration: python main.py config-info
echo 3. Run full setup: python main.py full-setup
echo.
echo For help: python main.py --help
echo.
pause