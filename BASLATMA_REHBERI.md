# 🚀 LinkedIn AI Agent Başlatma Rehberi
# (LinkedIn AI Agent Launch Guide)

## 🎯 Hızlı Başlangıç (Quick Start)

### Windows Kullanıcıları (Windows Users)
**En Kolay Yöntem:** 
1. `BASLAT_AI_AGENT.bat` dosyasına **çift tıklayın**
2. İşte bu kadar! Agent otomatik başlayacak.

### Linux/Mac Kullanıcıları (Linux/Mac Users)
**En Kolay Yöntem:**
1. Terminal'de: `python3 BASLAT_AI_AGENT.py`
2. veya dosyaya çift tıklayın
3. İşte bu kadar! Agent otomatik başlayacak.

---

## 📋 Launcher Ne Yapar? (What Does the Launcher Do?)

Launcher otomatik olarak:
1. ✅ Python versiyonunu kontrol eder (Python 3.8+ gerekli)
2. ✅ Sanal ortam (venv) oluşturur veya kullanır
3. ✅ Tüm bağımlılıkları yükler (requirements.txt)
4. ✅ .env dosyasını kontrol eder veya oluşturur
5. ✅ Veritabanını hazırlar
6. ✅ Varolan süreçleri temizler (port 8000)
7. ✅ AI Agent'ı başlatır ve tarayıcıyı açar

The launcher automatically:
1. ✅ Checks Python version (3.8+ required)
2. ✅ Creates or uses virtual environment (venv)
3. ✅ Installs all dependencies (requirements.txt)
4. ✅ Checks or creates .env file
5. ✅ Prepares database
6. ✅ Cleans existing processes (port 8000)
7. ✅ Starts AI Agent and opens browser

---

## 🔑 İlk Kurulum (First-Time Setup)

### 1. API Anahtarlarını Hazırlayın (Prepare API Keys)

Aşağıdaki API anahtarlarına ihtiyacınız var:

#### Gemini API Key
1. https://makersuite.google.com/app/apikey adresine gidin
2. Yeni bir API anahtarı oluşturun
3. Kopyalayın

#### LinkedIn OAuth Credentials
1. https://www.linkedin.com/developers/ adresine gidin
2. Yeni bir uygulama oluşturun
3. Client ID ve Client Secret'i kopyalayın
4. Redirect URI'yi ayarlayın: `http://localhost:8000/callback`

### 2. Launcher'ı Çalıştırın (Run the Launcher)

İlk çalıştırmada launcher:
- .env dosyası oluşturacak
- Dosyayı düzenleyici ile açacak
- API anahtarlarınızı girmenizi isteyecek

API anahtarlarını yapıştırın ve dosyayı kaydedin.

### 3. Launcher'ı Tekrar Çalıştırın (Run Launcher Again)

API anahtarlarını ekledikten sonra launcher'ı tekrar çalıştırın.
Bu sefer tüm kontroller geçecek ve agent başlayacak!

---

## 🌐 Web Arayüzü (Web Interface)

Agent başladığında tarayıcınızda otomatik açılacak:
- **URL:** http://localhost:8000

### İlk Giriş (First Login)
1. "Login with LinkedIn" butonuna tıklayın
2. LinkedIn ile giriş yapın
3. İzinleri onaylayın
4. Dashboard'a yönlendirileceksiniz

---

## 🤖 Otonom Özellikler (Autonomous Features)

Agent başladığında şu görevler otomatik çalışır:

### 📝 Gönderi Oluşturma (Post Creation)
- **Zamanlama:** Günde 3x (09:00, 14:00, 19:00)
- **Rastgele:** ±30 dakika
- **İşlem:** RSS'den makale bulur, AI ile gönderi yazar, paylaşır, 45 sn sonra beğenir, 90 sn sonra Türkçe özet ekler

### 💬 Proaktif Yorum (Proactive Commenting)
- **Zamanlama:** Her saat (07:00-21:00)
- **Rastgele:** ±15 dakika
- **Not:** LinkedIn arama API kullanımdan kalktı, manuel yorum hala mevcut

### 🤝 Bağlantı Davetleri (Connection Invitations)
- **Zamanlama:** Günde 7x (07:00, 09:00, 11:00, 14:00, 16:00, 19:00, 21:00)
- **Rastgele:** ±20 dakika
- **İşlem:** Profil bulur, davet gönderir

---

## 🛠️ Sorun Giderme (Troubleshooting)

### Python Bulunamadı (Python Not Found)
**Çözüm:** Python 3.8+ yükleyin
- https://www.python.org/downloads/

### Bağımlılıklar Yüklenemedi (Dependencies Failed)
**Çözüm:** Manuel yükleme
```bash
pip install -r requirements.txt
```

### Port 8000 Kullanımda (Port 8000 In Use)
**Çözüm:** Launcher otomatik temizler, manuel için:
- Windows: `netstat -ano | findstr :8000`
- Linux/Mac: `lsof -ti:8000 | xargs kill -9`

### .env Dosyası Sorunları (.env File Issues)
**Çözüm:** Manuel düzenleme
1. `.env.example`'i `.env` olarak kopyalayın
2. API anahtarlarınızı ekleyin
3. Dosyayı kaydedin

### Agent Başlamıyor (Agent Won't Start)
**Kontrol Listesi:**
1. ✅ Python 3.8+ yüklü mü?
2. ✅ .env dosyası var mı ve API anahtarları doğru mu?
3. ✅ Port 8000 boş mu?
4. ✅ İnternet bağlantısı var mı?

---

## 📊 Agent'ı Durdurmak (Stopping the Agent)

### Launcher Penceresinde (In Launcher Window)
- **Ctrl+C** tuşlarına basın

### Manuel (Manual)
- Windows: Task Manager'dan "python.exe" sürecini sonlandırın
- Linux/Mac: Terminal'de `Ctrl+C` veya `kill -9 <PID>`

---

## 📁 Dosya Yapısı (File Structure)

```
linkedin-agent/
├── BASLAT_AI_AGENT.py      # Ana launcher (Linux/Mac)
├── BASLAT_AI_AGENT.bat     # Windows launcher
├── BASLATMA_REHBERI.md     # Bu dosya (This file)
├── .env                    # API anahtarları (API keys)
├── .env.example            # Şablon (Template)
├── requirements.txt        # Python bağımlılıkları
├── src/                    # Kaynak kod (Source code)
│   ├── main.py            # FastAPI uygulaması
│   ├── worker.py          # İş mantığı
│   ├── scheduler.py       # Zamanlayıcı
│   └── ...
└── data/                   # Veritabanı ve loglar
    └── linkedin_agent.db
```

---

## ⚙️ Gelişmiş Ayarlar (Advanced Settings)

### Çalışma Saatlerini Değiştirme (Changing Operating Hours)

.env dosyasında:
```env
OPERATING_HOURS_START=7   # Başlangıç (Start)
OPERATING_HOURS_END=22    # Bitiş (End)
```

### Port Değiştirme (Changing Port)

Launcher'da varsayılan port 8000. Değiştirmek için:
1. `BASLAT_AI_AGENT.py` dosyasını düzenleyin
2. `--port 8000` değerini değiştirin
3. .env dosyasında `LINKEDIN_REDIRECT_URI`'yi güncelleyin

### Manuel Çalıştırma (Manual Run)

Launcher kullanmadan manuel başlatma:
```bash
# Sanal ortamı aktifleştir
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Agent'ı başlat
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📞 Destek (Support)

### Dokümantasyon (Documentation)
- README.md - İngilizce genel bakış
- README_TR.md - Türkçe genel bakış
- BASLATMA_KOMUTLARI.md - Detaylı komutlar

### İletişim (Contact)
- GitHub Issues: https://github.com/DevKursat/linkedinAgent/issues

---

## ✅ Kontrol Listesi (Checklist)

Agent'ınız çalışıyor mu? Kontrol edin:

- [ ] Python 3.8+ yüklü
- [ ] API anahtarları .env dosyasında
- [ ] Launcher başarıyla çalıştı
- [ ] Tarayıcıda http://localhost:8000 açıldı
- [ ] LinkedIn ile giriş yapıldı
- [ ] Dashboard'da loglar görünüyor
- [ ] Zamanlanmış görevler listelenmiş

Tüm maddeleri işaretlediyseniz, **TAM OTONOM AI AGENT'INIZ ÇALIŞIYOR!** 🎉

If you checked all items, **YOUR FULLY AUTONOMOUS AI AGENT IS RUNNING!** 🎉

---

*Son Güncelleme: 2025-10-29*
*Versiyon: 2.0*
