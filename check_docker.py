#!/usr/bin/env python3
"""
Pre-flight check script to verify Docker is running before attempting build.
Run this script before running docker compose commands.

Usage:
    python check_docker.py
"""

import subprocess
import sys
import os
import platform

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_success(text):
    """Print success message"""
    print(f"✅ {text}")

def print_error(text):
    """Print error message"""
    print(f"❌ {text}")

def print_warning(text):
    """Print warning message"""
    print(f"⚠️  {text}")

def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")

def run_command(command, description):
    """Run a command and return success status"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_docker_installed():
    """Check if Docker is installed"""
    print_header("Checking Docker Installation")
    
    success, stdout, stderr = run_command("docker --version", "Check Docker version")
    
    if success:
        version = stdout.strip()
        print_success(f"Docker is installed: {version}")
        return True
    else:
        print_error("Docker is not installed or not in PATH")
        print_info("Install Docker Desktop from: https://www.docker.com/products/docker-desktop")
        return False

def check_docker_running():
    """Check if Docker daemon is running"""
    print_header("Checking Docker Daemon")
    
    success, stdout, stderr = run_command("docker info", "Check Docker daemon")
    
    if success:
        print_success("Docker daemon is running")
        return True
    else:
        print_error("Docker daemon is not running")
        
        if platform.system() == "Windows":
            print_info("On Windows:")
            print("  1. Open Docker Desktop from Start Menu")
            print("  2. Run it as Administrator (Right-click → Run as administrator)")
            print("  3. Wait for Docker Desktop to fully start (green icon in system tray)")
            print("  4. Run this script again")
            print("\n📖 For detailed help, see: WINDOWS_DOCKER_COZUM.md")
        elif platform.system() == "Darwin":
            print_info("On macOS:")
            print("  1. Open Docker Desktop from Applications")
            print("  2. Wait for Docker Desktop to fully start")
            print("  3. Run this script again")
        else:
            print_info("On Linux:")
            print("  sudo systemctl start docker")
        
        return False

def check_docker_compose():
    """Check if docker compose is available"""
    print_header("Checking Docker Compose")
    
    # Try docker compose (new version)
    success, stdout, stderr = run_command("docker compose version", "Check Docker Compose")
    
    if success:
        version = stdout.strip()
        print_success(f"Docker Compose is available: {version}")
        return True
    
    # Try docker-compose (old version)
    success, stdout, stderr = run_command("docker-compose version", "Check Docker Compose (legacy)")
    
    if success:
        version = stdout.strip()
        print_success(f"Docker Compose (legacy) is available: {version}")
        print_warning("Using legacy docker-compose. Consider using 'docker compose' instead.")
        return True
    
    print_error("Docker Compose is not available")
    print_info("Docker Compose should be included with Docker Desktop")
    return False

def check_env_file():
    """Check if .env file exists"""
    print_header("Checking Configuration")
    
    if os.path.exists(".env"):
        print_success(".env file exists")
        
        # Check if it has required variables
        with open(".env", "r") as f:
            content = f.read()
            required_vars = [
                "LINKEDIN_CLIENT_ID",
                "LINKEDIN_CLIENT_SECRET",
                "GEMINI_API_KEY"
            ]
            
            missing_vars = []
            for var in required_vars:
                if f"{var}=" not in content or f"{var}=your_" in content or f"{var}=\n" in content:
                    missing_vars.append(var)
            
            if missing_vars:
                print_warning(f"The following variables need to be configured in .env:")
                for var in missing_vars:
                    print(f"    - {var}")
                return False
            else:
                print_success("All required variables are configured in .env")
                return True
    else:
        print_error(".env file not found")
        print_info("Create .env file:")
        
        if platform.system() == "Windows":
            print("  copy .env.example .env")
        else:
            print("  cp .env.example .env")
        
        print("\nThen edit .env and fill in your credentials")
        return False

def check_port_available():
    """Check if port 5000 is available"""
    print_header("Checking Port Availability")
    
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()
        
        if result == 0:
            print_warning("Port 5000 is already in use")
            print_info("Stop any application using port 5000, or change the port in docker-compose.yml")
            return False
        else:
            print_success("Port 5000 is available")
            return True
    except Exception as e:
        print_warning(f"Could not check port availability: {e}")
        return True

def main():
    """Main function"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║          LinkedIn Agent - Docker Pre-flight Check        ║")
    print("║                                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    
    checks = [
        ("Docker Installation", check_docker_installed),
        ("Docker Daemon", check_docker_running),
        ("Docker Compose", check_docker_compose),
        ("Environment Configuration", check_env_file),
        ("Port Availability", check_port_available),
    ]
    
    results = {}
    
    for name, check_func in checks:
        results[name] = check_func()
    
    # Summary
    print_header("Summary")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total} checks")
    print()
    
    for name, result in results.items():
        if result:
            print_success(name)
        else:
            print_error(name)
    
    # Final message
    print("\n" + "=" * 60)
    
    if all(results.values()):
        print_success("All checks passed! You can now run:")
        print("\n    docker compose up -d --build")
        print("\nThen open: http://localhost:5000")
        print("\n" + "=" * 60)
        return 0
    else:
        print_error("Some checks failed. Please fix the issues above.")
        print("\n📖 For detailed troubleshooting:")
        
        if platform.system() == "Windows":
            print("   - See WINDOWS_DOCKER_COZUM.md for Windows-specific help")
        
        print("   - See BASLATMA_KOMUTLARI.md for general setup instructions")
        print("   - See README_TR.md for Turkish documentation")
        print("\n" + "=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
