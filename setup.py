import subprocess
import sys
import os

def install_packages(requirements_file='requirements.txt'):
    """
    Install packages listed in the specified requirements file.

    Args:
        requirements_file (str): Path to the requirements.txt file.
    """
    if not os.path.exists(requirements_file):
        print(f"Error: '{requirements_file}' does not exist.")
        sys.exit(1)

    print(f"Reading requirements from '{requirements_file}'...\n")

    with open(requirements_file, 'r') as file:
        lines = file.readlines()

    # Filter out comments and empty lines
    packages = [line.strip() for line in lines if line.strip() and not line.startswith('#')]

    if not packages:
        print("No packages to install.")
        return

    print(f"Found {len(packages)} package(s) to install.\n")

    for package in packages:
        print(f"Installing '{package}'...")
        try:
            # Call pip as a subprocess:
            # -m ensures that the correct pip associated with the current Python interpreter is used
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"Successfully installed '{package}'.\n")
        except subprocess.CalledProcessError as error:
            print(f"Failed to install '{package}'. Error: {error}\n")

    print("Installation process completed.")

if __name__ == "__main__":
    # Optionally, allow the user to specify a different requirements file via command-line arguments
    if len(sys.argv) > 1:
        req_file = sys.argv[1]
    else:
        req_file = 'requirements.txt'

    install_packages(req_file)
