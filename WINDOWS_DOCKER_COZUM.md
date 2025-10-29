# Windows Docker Sorunları ve Çözümleri / Windows Docker Issues and Solutions

## 🔴 Yaşanan Hata / Error You're Seeing

```
unable to get image 'linkedinagent-worker': error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/images/linkedinagent-worker/json": open //./pipe/dockerDesktopLinuxEngine: Access is denied.
```

## ❓ Bu Hata Ne Anlama Geliyor? / What Does This Error Mean?

Bu hata, Docker Desktop'ın Windows'ta düzgün çalışmadığını gösterir. Üç ana nedeni vardır:

1. **Docker Desktop çalışmıyor** - En yaygın neden
2. **İzin sorunu** - Docker Desktop'a erişim izniniz yok
3. **Docker Desktop henüz başlamadı** - Arka planda başlatılıyor

---

## ✅ ÇÖZÜM ADIMLARI / SOLUTION STEPS

### Adım 1: Docker Desktop'ı Kontrol Edin / Check Docker Desktop

#### Windows Taskbar'ına Bakın:
- Sağ alttaki sistem tepsisinde (system tray) Docker simgesini arayın
- **Docker simgesi varsa ve sabit ise**: Docker çalışıyor ✅
- **Docker simgesi animasyon gösteriyorsa**: Docker başlatılıyor, bekleyin ⏳
- **Docker simgesi yoksa**: Docker çalışmıyor ❌

#### Docker Desktop'ı Başlatın:
1. Windows Başlat menüsünü açın
2. "Docker Desktop" yazın
3. **Sağ tıklayın** ve "Run as administrator" (Yönetici olarak çalıştır) seçin
4. Docker Desktop'ın tamamen başlamasını bekleyin (1-2 dakika)
5. Sağ alttaki Docker simgesinin yeşil olmasını bekleyin

### Adım 2: Docker'ın Çalıştığını Doğrulayın / Verify Docker is Running

PowerShell veya CMD'yi **Yönetici olarak** açın ve test edin:

```bash
docker version
```

**Başarılı çıktı örneği:**
```
Client: Docker Engine - Community
 Version:           24.0.x
 ...
Server: Docker Desktop
 Version:           24.0.x
 ...
```

**EĞER HATA ALIRSAN**: Docker çalışmıyor, Adım 1'i tekrarla.

### Adım 3: Eski Container'ları Temizleyin / Clean Up Old Containers

```bash
docker compose down
```

```bash
docker system prune -f
```

### Adım 4: Projeyi Tekrar Başlatın / Restart the Project

```bash
docker compose up -d --build
```

**ÖNEMLİ**: `--build` parametresi image'ları yeniden oluşturur.

### Adım 5: Container'ların Çalıştığını Kontrol Edin / Check Containers Are Running

```bash
docker compose ps
```

**Başarılı çıktı:**
```
NAME                    IMAGE                  STATUS
linkedinagent-web       linkedinagent-web      Up X seconds
linkedinagent-worker    linkedinagent-worker   Up X seconds
```

### Adım 6: Uygulamayı Açın / Open the Application

```bash
start http://localhost:5000
```

---

## 🔧 DİĞER YAKIN SORUNLAR / OTHER COMMON ISSUES

### Sorun 1: "Docker daemon is not running"

**Çözüm:**
1. Docker Desktop'ı kapat
2. Windows'u yeniden başlat
3. Docker Desktop'ı yönetici olarak çalıştır

### Sorun 2: "Error response from daemon: open \\.\pipe\docker_engine: Access is denied"

**Çözüm:**
1. PowerShell'i yönetici olarak aç
2. Şu komutu çalıştır:
```powershell
icacls "\\.\pipe\docker_engine" /grant "Users":F
```
3. Docker Desktop'ı yeniden başlat

### Sorun 3: "Port 5000 is already in use"

**Çözüm:**
```bash
# Hangi programın port 5000'i kullandığını öğren
netstat -ano | findstr :5000

# O programı Task Manager'dan kapat VEYA
# docker-compose.yml dosyasında portu değiştir (örn: "5001:5000")
```

### Sorun 4: Docker Desktop başlamıyor / won't start

**Çözüm:**
1. WSL2'nin kurulu ve güncel olduğundan emin olun:
```bash
wsl --update
```

2. Windows özelliklerinde "Virtual Machine Platform" ve "Windows Subsystem for Linux" etkin olmalı:
   - Windows Başlat → "Turn Windows features on or off" ara
   - ✅ Virtual Machine Platform
   - ✅ Windows Subsystem for Linux
   - Bilgisayarı yeniden başlat

3. BIOS'ta virtualization (sanallaştırma) etkin olmalı:
   - Bilgisayarı yeniden başlat
   - BIOS/UEFI'ye gir (genellikle F2, F10, Del tuşları)
   - "Intel VT-x" veya "AMD-V" ayarını ENABLE yap
   - Kaydet ve çık

---

## 🚀 ÖNERİLEN BAŞLATMA SIRALAMASI / RECOMMENDED STARTUP ORDER

Windows'ta Docker ile çalışırken bu sırayı izleyin:

### 1. Docker Desktop'ı Başlat
```
Windows Başlat → Docker Desktop (Yönetici olarak çalıştır)
```

### 2. Docker'ın Hazır Olmasını Bekle
- Sağ alttaki Docker simgesi yeşil olmalı
- "Docker Desktop is running" mesajı görülmeli

### 3. Terminal'i Yönetici Olarak Aç
```
CMD veya PowerShell → Sağ tık → Run as administrator
```

### 4. Proje Dizinine Git
```bash
cd C:\Users\kürşat\linkedinAgent
```

### 5. .env Dosyasını Kontrol Et
```bash
notepad .env
```
- Tüm gerekli değişkenlerin dolu olduğundan emin ol

### 6. Docker Compose ile Başlat
```bash
docker compose down
docker compose up -d --build
```

### 7. Logları Kontrol Et
```bash
docker compose logs -f
```

### 8. Uygulamayı Aç
```bash
start http://localhost:5000
```

---

## 📋 KONTROL LİSTESİ / CHECKLIST

Başlatmadan önce kontrol edin:

- [ ] Docker Desktop kurulu mu?
- [ ] Docker Desktop yönetici olarak çalışıyor mu?
- [ ] Docker simgesi yeşil mi?
- [ ] `docker version` komutu çalışıyor mu?
- [ ] `.env` dosyası var mı ve dolu mu?
- [ ] Port 5000 boş mu?
- [ ] WSL2 kurulu ve güncel mi?
- [ ] Virtualization BIOS'ta etkin mi?

---

## 🆘 HÂLÂ ÇALIŞMIYOR? / STILL NOT WORKING?

### Hızlı Çözüm: Python ile Çalıştır

Docker sorunlarını atla ve doğrudan Python ile çalıştır:

```bash
# 1. Virtual environment oluştur
python -m venv .venv

# 2. Aktif et
.venv\Scripts\activate

# 3. Bağımlılıkları kur
pip install -r requirements.txt

# 4. .env dosyasını düzenle
notepad .env
# LINKEDIN_REDIRECT_URI=http://127.0.0.1:8000/callback olarak değiştir

# 5. İlk terminal - Web server
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

# 6. İkinci terminal - Worker (yeni bir terminal aç)
.venv\Scripts\activate
python -m src.worker

# 7. Tarayıcıda aç
start http://127.0.0.1:8000
```

### Daha Fazla Yardım

1. **Logları paylaş:**
```bash
docker compose logs > logs.txt
```
Ardından `logs.txt` dosyasını GitHub Issue'da paylaş

2. **Sistem bilgilerini paylaş:**
```bash
docker version > system_info.txt
docker info >> system_info.txt
wsl --version >> system_info.txt
```

3. **GitHub Issue aç:**
- https://github.com/DevKursat/linkedinAgent/issues
- "Windows Docker Access Denied" başlığıyla
- Yukarıdaki dosyaları ekle

---

## 📚 İLGİLİ DOKÜMANTASYON / RELATED DOCUMENTATION

- [BASLATMA_KOMUTLARI.md](BASLATMA_KOMUTLARI.md) - Genel başlatma rehberi
- [README_TR.md](README_TR.md) - Türkçe genel dokümantasyon
- [HIZLI_BASLAT.txt](HIZLI_BASLAT.txt) - Hızlı komutlar

---

## ✅ ÖZET / SUMMARY

**En Yaygın Çözüm:**
1. Docker Desktop'ı yönetici olarak çalıştır
2. Tamamen başlamasını bekle (yeşil simge)
3. CMD/PowerShell'i yönetici olarak aç
4. `docker compose up -d --build` komutunu çalıştır

**Alternatif:**
- Docker sorunlarını atla, Python ile çalıştır (yukarıdaki adımlar)

**Başarılar! 🚀**
