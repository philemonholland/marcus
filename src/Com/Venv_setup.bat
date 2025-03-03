@echo off

:: Step 1: Check if Python 3.12.8 is installed and set path
where python3.12 >nul 2>nul
if %errorlevel% neq 0 (
    echo Python 3.12.8 is not installed or not in your PATH.
    echo Please install Python 3.12.8 or update your PATH to include it.
    exit /b
)

:: Step 2: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment with Python 3.12.8...
    python3.12 -m venv venv
)

:: Step 3: Activate virtual environment
call venv\Scripts\activate

:: Step 4: Install dependencies if requirements.txt exists
if exist requirements.txt (
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    echo No requirements.txt found. Virtual environment is ready!
)

echo ✅ Virtual environment setup complete!
