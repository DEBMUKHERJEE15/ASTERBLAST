@echo off
echo Setting up Cosmic Watch Backend on Windows...

REM Create virtual environment
python -m venv venv
echo Virtual environment created.

REM Activate virtual environment
call venv\Scripts\activate.bat
echo Virtual environment activated.

REM Install dependencies
pip install -r requirements.txt
echo Dependencies installed.

REM Create .env file if it doesn't exist
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env
        echo .env file created from .env.example
        echo Please edit .env file with your configuration.
    ) else (
        echo .env.example not found. Creating basic .env...
        echo # Basic Configuration > .env
        echo NASA_API_KEY=DEMO_KEY >> .env
        echo SECRET_KEY=your-secret-key-change-in-production >> .env
        echo DATABASE_URL=postgresql://user:password@localhost/cosmicwatch >> .env
        echo REDIS_URL=redis://localhost:6379/0 >> .env
    )
)

echo.
echo Setup complete!
echo To run the application:
echo 1. Activate virtual environment: venv\Scripts\activate.bat
echo 2. Run: python run.py
echo.
pause