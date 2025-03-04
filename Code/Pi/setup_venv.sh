#!/bin/bash

VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"

# Function to update system packages
update_system_packages() {
    echo "Updating system packages..."
    sudo apt update
    sudo apt upgrade -y
}

# Function to create the virtual environment
create_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        python3 -m venv $VENV_DIR --system-site-packages
    else
        echo "Virtual environment already exists."
    fi
}

# Function to install/update dependencies inside the virtual environment
install_requirements() {
    # Activate the virtual environment
    source $VENV_DIR/bin/activate

    # Check if requirements.txt exists
    if [ -f "$REQUIREMENTS_FILE" ]; then
        echo "Installing/updating requirements from $REQUIREMENTS_FILE..."
        pip install --upgrade -r $REQUIREMENTS_FILE  # Force update installed packages
    else
        echo "No requirements.txt found. Skipping package installation."
    fi
}

# Main execution flow
update_system_packages
create_venv
install_requirements


echo "Setup complete."
echo "To activate the virtual environment, run:"
echo "source $VENV_DIR/bin/activate"