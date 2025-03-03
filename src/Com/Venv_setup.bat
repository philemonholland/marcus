@echo off

:: Step 1: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Step 2: Activate virtual environment
call venv\Scripts\activate

:: Step 3: Install dependencies if requirements.txt exists
if exist requirements.txt (
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    echo No requirements.txt found. Virtual environment is ready!
)

echo ✅ Virtual environment setup complete!
