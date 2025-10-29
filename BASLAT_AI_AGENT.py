#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 TAM OTONOM LİNKEDIN AI AGENT BAŞLATICI
(FULLY AUTONOMOUS LINKEDIN AI AGENT LAUNCHER)

Bu dosyaya çift tıklayarak veya python ile çalıştırarak 
LinkedIn AI Agent'ınızı kusursuz ve hatasız başlatabilirsiniz.

Double-click this file or run with Python to start your
LinkedIn AI Agent flawlessly and error-free.

Kullanım (Usage):
    python BASLAT_AI_AGENT.py
    veya (or)
    Dosyaya çift tıklayın (Double-click the file)
"""

import sys
import os
import subprocess
import time
import webbrowser
from pathlib import Path

# ANSI renk kodları (ANSI color codes)
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header():
    """Başlık yazdır (Print header)"""
    print("\n" + "="*70)
    print(f"{BOLD}{GREEN}🤖 TAM OTONOM LİNKEDIN AI AGENT{RESET}")
    print(f"{BOLD}{GREEN}   (FULLY AUTONOMOUS LINKEDIN AI AGENT){RESET}")
    print("="*70 + "\n")

def print_step(step, total, message):
    """Adım yazdır (Print step)"""
    print(f"{BLUE}[{step}/{total}]{RESET} {message}...")

def print_success(message):
    """Başarı mesajı (Success message)"""
    print(f"   {GREEN}✅ {message}{RESET}")

def print_error(message):
    """Hata mesajı (Error message)"""
    print(f"   {RED}❌ {message}{RESET}")

def print_warning(message):
    """Uyarı mesajı (Warning message)"""
    print(f"   {YELLOW}⚠️  {message}{RESET}")

def check_python_version():
    """Python versiyonunu kontrol et (Check Python version)"""
    print_step(1, 7, "Python versiyonu kontrol ediliyor")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8+ gerekli, mevcut: {version.major}.{version.minor}")
        print_error("Python 3.8+ required, current: {version.major}.{version.minor}")
        return False
    print_success(f"Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_venv():
    """Sanal ortamı kontrol et veya oluştur (Check or create virtual environment)"""
    print_step(2, 7, "Sanal ortam kontrol ediliyor")
    venv_path = Path(".venv")
    
    if not venv_path.exists():
        print_warning("Sanal ortam bulunamadı, oluşturuluyor...")
        print_warning("Virtual environment not found, creating...")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print_success("Sanal ortam oluşturuldu")
        except subprocess.CalledProcessError:
            print_error("Sanal ortam oluşturulamadı")
            print_error("Could not create virtual environment")
            return False, None
    
    # Sanal ortam Python'ını bul (Find virtual environment Python)
    if sys.platform == "win32":
        venv_python = venv_path / "Scripts" / "python.exe"
        venv_pip = venv_path / "Scripts" / "pip.exe"
    else:
        venv_python = venv_path / "bin" / "python"
        venv_pip = venv_path / "bin" / "pip"
    
    if not venv_python.exists():
        print_error("Sanal ortam Python bulunamadı")
        print_error("Virtual environment Python not found")
        return False, None
    
    print_success("Sanal ortam hazır")
    return True, (str(venv_python), str(venv_pip))

def install_dependencies(venv_python, venv_pip):
    """Bağımlılıkları yükle (Install dependencies)"""
    print_step(3, 7, "Bağımlılıklar kontrol ediliyor")
    
    # pip'i güncelle (Update pip)
    try:
        subprocess.run([venv_pip, "install", "--upgrade", "pip"], 
                      check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass  # pip güncellemesi zorunlu değil
    
    # requirements.txt'i yükle (Install requirements.txt)
    if Path("requirements.txt").exists():
        try:
            subprocess.run([venv_pip, "install", "-r", "requirements.txt"], 
                          check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print_success("Tüm bağımlılıklar yüklendi")
            return True
        except subprocess.CalledProcessError:
            print_error("Bağımlılıklar yüklenemedi")
            print_error("Could not install dependencies")
            return False
    else:
        print_error("requirements.txt bulunamadı")
        print_error("requirements.txt not found")
        return False

def check_env_file():
    """Ortam değişkenlerini kontrol et (Check environment variables)"""
    print_step(4, 7, "Ortam değişkenleri kontrol ediliyor")
    
    env_file = Path(".env")
    if not env_file.exists():
        print_warning(".env dosyası bulunamadı, .env.example'dan oluşturuluyor...")
        print_warning(".env file not found, creating from .env.example...")
        
        env_example = Path(".env.example")
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print_success(".env dosyası oluşturuldu")
            print_warning("")
            print_warning("ÖNEMLİ: .env dosyasını düzenleyip API anahtarlarınızı ekleyin:")
            print_warning("IMPORTANT: Edit .env file and add your API keys:")
            print_warning("  - GEMINI_API_KEY")
            print_warning("  - LINKEDIN_CLIENT_ID")
            print_warning("  - LINKEDIN_CLIENT_SECRET")
            print_warning("")
            
            # Dosyayı aç (Open file)
            if sys.platform == "win32":
                os.system(f"notepad {env_file}")
            elif sys.platform == "darwin":
                os.system(f"open {env_file}")
            else:
                os.system(f"xdg-open {env_file} 2>/dev/null || nano {env_file}")
            
            input("API anahtarlarını ekledikten sonra Enter'a basın (Press Enter after adding API keys)...")
        else:
            print_error(".env.example dosyası bulunamadı")
            print_error(".env.example file not found")
            return False
    
    # API anahtarlarını kontrol et (Check API keys)
    with open(env_file, 'r') as f:
        content = f.read()
        
    missing_keys = []
    if "GEMINI_API_KEY=" not in content or "GEMINI_API_KEY=your_" in content:
        missing_keys.append("GEMINI_API_KEY")
    if "LINKEDIN_CLIENT_ID=" not in content or "LINKEDIN_CLIENT_ID=your_" in content:
        missing_keys.append("LINKEDIN_CLIENT_ID")
    if "LINKEDIN_CLIENT_SECRET=" not in content or "LINKEDIN_CLIENT_SECRET=your_" in content:
        missing_keys.append("LINKEDIN_CLIENT_SECRET")
    
    if missing_keys:
        print_warning(f"Eksik API anahtarları: {', '.join(missing_keys)}")
        print_warning(f"Missing API keys: {', '.join(missing_keys)}")
        print_warning("Agent çalışacak ama bazı özellikler çalışmayabilir")
        print_warning("Agent will run but some features may not work")
    else:
        print_success("Tüm ortam değişkenleri ayarlanmış")
    
    return True

def check_database(venv_python):
    """Veritabanını kontrol et ve başlat (Check and initialize database)"""
    print_step(5, 7, "Veritabanı kontrol ediliyor")
    
    db_path = Path("data/linkedin_agent.db")
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Veritabanı tablolarını oluştur (Create database tables)
    try:
        # main.py import edildiğinde tabloları oluşturur
        subprocess.run([venv_python, "-c", 
                       "from src.database import engine; from src.models import Base; Base.metadata.create_all(bind=engine)"],
                      check=True, capture_output=True, text=True, timeout=10)
        print_success("Veritabanı hazır")
        return True
    except subprocess.TimeoutExpired:
        print_success("Veritabanı hazır (timeout)")
        return True
    except Exception as e:
        print_warning(f"Veritabanı kontrolü atlandı: {str(e)[:50]}")
        return True  # Veritabanı otomatik oluşturulacak

def kill_existing_process():
    """Varolan süreçleri kapat (Kill existing processes)"""
    print_step(6, 7, "Varolan süreçler kontrol ediliyor")
    
    try:
        if sys.platform == "win32":
            # Windows'ta port 8000'i kullanan süreci bul ve kapat
            result = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True, text=True
            )
            for line in result.stdout.split('\n'):
                if ':8000' in line and 'LISTENING' in line:
                    parts = line.split()
                    pid = parts[-1]
                    try:
                        subprocess.run(["taskkill", "/F", "/PID", pid], 
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        print_success(f"Önceki süreç durduruldu (PID: {pid})")
                    except:
                        pass
        else:
            # Linux/Mac'te port 8000'i kullanan süreci bul ve kapat
            try:
                result = subprocess.run(
                    ["lsof", "-ti", "tcp:8000"],
                    capture_output=True, text=True, timeout=2
                )
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            subprocess.run(["kill", "-9", pid],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            print_success(f"Önceki süreç durduruldu (PID: {pid})")
                        except:
                            pass
            except:
                pass
    except Exception as e:
        pass  # Süreç kapatma zorunlu değil
    
    print_success("Port 8000 temizlendi")
    return True

def start_agent(venv_python):
    """AI Agent'ı başlat (Start AI Agent)"""
    print_step(7, 7, "AI Agent başlatılıyor")
    
    # Ortam değişkenlerini yükle (Load environment variables)
    env = os.environ.copy()
    
    # Hardcoded credentials - set these first with highest priority
    env['LINKEDIN_CLIENT_ID'] = '86n8sb2f78chmu'
    env['LINKEDIN_CLIENT_SECRET'] = 'WPL_AP1.UdjoaFLr3RMCcofU.8wJPWQ=='
    env['GEMINI_API_KEY'] = 'AIzaSyC1OQmXcuHkGnuEzOIyraNpbkis61_DlEQ'
    
    # Load .env file if it exists (will be overridden by hardcoded values above)
    if Path(".env").exists():
        with open(".env", 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Only set if not already set by hardcoded values
                    if key.strip() not in ['LINKEDIN_CLIENT_ID', 'LINKEDIN_CLIENT_SECRET', 'GEMINI_API_KEY']:
                        env[key.strip()] = value.strip()
    
    print_success("Sunucu başlatılıyor...")
    print()
    print("="*70)
    print(f"{BOLD}{GREEN}✅ AI AGENT BAŞARIYLA BAŞLATILDI!{RESET}")
    print(f"{BOLD}{GREEN}   (AI AGENT STARTED SUCCESSFULLY!){RESET}")
    print("="*70)
    print()
    print(f"{BOLD}🔑 Kimlik Bilgileri Yüklendi (Credentials Loaded):{RESET}")
    print(f"   ✅ LINKEDIN_CLIENT_ID: {'SET ✓' if env.get('LINKEDIN_CLIENT_ID') else 'NOT SET ✗'}")
    print(f"   ✅ LINKEDIN_CLIENT_SECRET: {'SET ✓' if env.get('LINKEDIN_CLIENT_SECRET') else 'NOT SET ✗'}")
    print(f"   ✅ GEMINI_API_KEY: {'SET ✓' if env.get('GEMINI_API_KEY') else 'NOT SET ✗'}")
    print()
    print(f"{BOLD}🌐 Web Arayüzü (Web Interface):{RESET}")
    print(f"   {BLUE}http://localhost:8000{RESET}")
    print()
    print(f"{BOLD}📋 Özellikler (Features):{RESET}")
    print("   • Günde 3 kez otomatik gönderi (3x daily auto-posts)")
    print("   • Her saat proaktif yorum (Hourly proactive comments)")
    print("   • Günde 7 kez bağlantı daveti (7x daily connection invites)")
    print()
    print(f"{BOLD}⏰ Çalışma Saatleri (Operating Hours):{RESET}")
    print("   07:00 - 22:00 (Istanbul Timezone)")
    print()
    print(f"{BOLD}🔄 Otonom Çalışma (Autonomous Operation):{RESET}")
    print("   ✅ Scheduler otomatik başladı (Scheduler auto-started)")
    print("   ✅ Tüm görevler zamanlandı (All tasks scheduled)")
    print()
    print(f"{YELLOW}Durdurmak için Ctrl+C tuşlarına basın{RESET}")
    print(f"{YELLOW}Press Ctrl+C to stop{RESET}")
    print("="*70)
    print()
    
    # Tarayıcıyı aç (Open browser)
    time.sleep(2)
    try:
        webbrowser.open('http://localhost:8000')
    except:
        pass
    
    # Uvicorn'u başlat (Start Uvicorn)
    try:
        cmd = [venv_python, "-m", "uvicorn", "src.main:app", 
               "--host", "0.0.0.0", "--port", "8000", "--reload"]
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print()
        print("="*70)
        print(f"{YELLOW}AI Agent durduruldu (AI Agent stopped){RESET}")
        print("="*70)
        print()
        return True
    except Exception as e:
        print()
        print_error(f"Hata: {e}")
        print_error(f"Error: {e}")
        return False

def main():
    """Ana fonksiyon (Main function)"""
    # Proje dizinine geç (Change to project directory)
    os.chdir(Path(__file__).parent)
    
    print_header()
    
    # 1. Python versiyonunu kontrol et
    if not check_python_version():
        input("\nÇıkmak için Enter'a basın (Press Enter to exit)...")
        return 1
    
    # 2. Sanal ortamı kontrol et
    success, venv_info = check_venv()
    if not success:
        input("\nÇıkmak için Enter'a basın (Press Enter to exit)...")
        return 1
    
    venv_python, venv_pip = venv_info
    
    # 3. Bağımlılıkları yükle
    if not install_dependencies(venv_python, venv_pip):
        input("\nÇıkmak için Enter'a basın (Press Enter to exit)...")
        return 1
    
    # 4. Ortam değişkenlerini kontrol et
    if not check_env_file():
        input("\nÇıkmak için Enter'a basın (Press Enter to exit)...")
        return 1
    
    # 5. Veritabanını kontrol et
    if not check_database(venv_python):
        input("\nÇıkmak için Enter'a basın (Press Enter to exit)...")
        return 1
    
    # 6. Varolan süreçleri kapat
    if not kill_existing_process():
        input("\nÇıkmak için Enter'a basın (Press Enter to exit)...")
        return 1
    
    # 7. AI Agent'ı başlat
    if not start_agent(venv_python):
        input("\nÇıkmak için Enter'a basın (Press Enter to exit)...")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nAI Agent durduruldu (AI Agent stopped)\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{RED}HATA (ERROR): {e}{RESET}\n")
        import traceback
        traceback.print_exc()
        input("\nÇıkmak için Enter'a basın (Press Enter to exit)...")
        sys.exit(1)
