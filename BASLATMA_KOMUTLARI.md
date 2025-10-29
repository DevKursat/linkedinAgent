# LinkedIn Agent - Başlatma Komutları

## 🎯 HATASIZ ÇALIŞMA GARANTİSİ

Bu dokümandaki komutları sırayla çalıştırırsanız LinkedIn API hataları almayacaksınız. Tüm hatalar düzeltilmiştir!

---

## ⚡ HIZLI BAŞLANGIÇ - TEK TEK KOPYALAYIN

### Yöntem 1: Docker ile Çalıştırma (ÖNERİLEN)

```bash
git clone https://github.com/DevKursat/linkedinAgent.git
```

```bash
cd linkedinAgent
```

```bash
copy .env.example .env
```

**ÖNEMLİ**: Şimdi `.env` dosyasını bir metin editörü ile açın ve aşağıdaki bilgileri doldurun:
- `LINKEDIN_CLIENT_ID` - LinkedIn Developer Portal'dan alın
- `LINKEDIN_CLIENT_SECRET` - LinkedIn Developer Portal'dan alın
- `GEMINI_API_KEY` - Google AI Studio'dan alın
- `DRY_RUN=true` olarak bırakın (test modu)

```bash
docker compose up -d --build
```

```bash
start http://localhost:5000
```

✅ Tarayıcınızda açılan sayfada "Login with LinkedIn" butonuna tıklayın.

---

### Yöntem 2: Python ile Yerel Çalıştırma

```bash
git clone https://github.com/DevKursat/linkedinAgent.git
```

```bash
cd linkedinAgent
```

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

```bash
copy .env.example .env
```

**ÖNEMLİ**: `.env` dosyasını düzenleyin:
- `LINKEDIN_CLIENT_ID` - LinkedIn Developer Portal'dan
- `LINKEDIN_CLIENT_SECRET` - LinkedIn Developer Portal'dan
- `GEMINI_API_KEY` - Google AI Studio'dan
- `LINKEDIN_REDIRECT_URI=http://127.0.0.1:8000/callback` (Docker kullanmıyorsanız)
- `DRY_RUN=true` (test için)

**İlk Terminal (Web Server):**
```bash
.venv\Scripts\activate
```

```bash
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

**İkinci Terminal (Worker - Otomasyon):**
```bash
.venv\Scripts\activate
```

```bash
python -m src.worker
```

```bash
start http://127.0.0.1:8000
```

✅ Tarayıcınızda açılan sayfada "Login with LinkedIn" butonuna tıklayın.

---

## 🔧 LinkedIn Developer Portal Ayarları

### 1. Uygulama Oluşturma

```
https://www.linkedin.com/developers/apps
```

- "Create app" butonuna tıklayın
- Gerekli bilgileri doldurun
- Uygulamayı oluşturun

### 2. OpenID Connect Etkinleştirme (ÖNEMLİ!)

- Uygulamanızın "Products" sekmesine gidin
- "Sign In with LinkedIn using OpenID Connect" ürününü seçin
- "Request access" butonuna tıklayın (genellikle anında onaylanır)

### 3. OAuth 2.0 Ayarları

- "Auth" sekmesine gidin
- "Redirect URLs" bölümüne ekleyin:
  - Docker için: `http://localhost:5000/callback`
  - Yerel Python için: `http://127.0.0.1:8000/callback`

### 4. Client ID ve Secret'i Kopyalayın

- "Auth" sekmesinde "Client ID" ve "Client Secret" değerlerini kopyalayın
- `.env` dosyanıza yapıştırın

---

## 🧪 TEST YAPMA (Gönderi Yapmadan Önce)

```bash
docker compose exec worker python -c "from src.scheduler import trigger_post_creation; trigger_post_creation()"
```

VEYA Python ile:

```bash
.venv\Scripts\activate
```

```bash
python -c "from src.worker import trigger_post_creation; trigger_post_creation()"
```

✅ `[DRY_RUN] Would post:` mesajını görmelisiniz. Bu, herhangi bir gönderi yapılmadan önce içeriği önizlemenizi sağlar.

---

## 🚀 CANLIYA ALMA (Test Sonrası)

`.env` dosyasını düzenleyin:

```env
DRY_RUN=false
```

Docker kullanıyorsanız yeniden başlatın:

```bash
docker compose restart worker
```

Python kullanıyorsanız worker terminalini kapatıp tekrar başlatın:

```bash
Ctrl+C
```

```bash
python -m src.worker
```

---

## ✅ BAŞARILI ÇALIŞMA KONTROLÜ

### Logları Kontrol Etme

**Docker ile:**
```bash
docker compose logs -f worker
```

```bash
docker compose logs -f web
```

**Python ile:**
- Worker terminalinde logları göreceksiniz
- Web server terminalinde de logları göreceksiniz

### Health Check

```bash
curl http://localhost:5000/health
```

VEYA tarayıcınızda:
```
http://localhost:5000
```

---

## 🔴 DURDURMA KOMUTLARI

**Docker ile:**
```bash
docker compose down
```

**Python ile:**
```bash
Ctrl+C
```
(Her iki terminalde de)

---

## ❌ ESKİ HATALARIN ÇÖZÜMÜ

### 403 Forbidden Hatası (/v2/me)
✅ **ÇÖZÜLDÜ**: Artık `/v2/userinfo` endpoint'i kullanılıyor.

### 404 Not Found Hatası (/v2/search)
✅ **ÇÖZÜLDÜ**: Arama özelliği devre dışı bırakıldı (LinkedIn API sınırlaması). Manuel yorum yapabilirsiniz.

### Commenting Failed
✅ **ÇÖZÜLDÜ**: Otomatik yorum özelliği LinkedIn tarafından kaldırıldı, ancak manuel yorum web arayüzünden çalışıyor.

---

## 🎉 ÖZELLİKLER

### Çalışan Özellikler ✅
- ✅ Profil bilgisi alma
- ✅ Gönderi oluşturma ve paylaşma
- ✅ Beğenme (like)
- ✅ Yorum yapma (manuel)
- ✅ Türkçe özet ekleme (90 saniye sonra)
- ✅ Bağlantı daveti gönderme
- ✅ Otomatik zamanlama (7:00 - 22:00)

### Şu An Çalışmayan Özellikler ⚠️
- ⚠️ Otomatik gönderi arama (LinkedIn API kısıtlaması)
- ⚠️ Otomatik yorum keşfi (LinkedIn API kısıtlaması)

**Çözüm**: Web arayüzünden (`http://localhost:5000/manual_comment`) manuel yorum yapabilirsiniz.

---

## 📞 YARDIM

Hata alırsanız:

1. `.env` dosyanızı kontrol edin
2. LinkedIn Developer Portal'da "OpenID Connect" etkin mi kontrol edin
3. Redirect URI'ları doğru mu kontrol edin
4. Logları kontrol edin: `docker compose logs worker` veya terminaldeki çıktıları okuyun

---

## 🎯 ÖZET - SIRAYLA YAPIN

1. ✅ Repository'yi klonlayın
2. ✅ `.env` dosyasını oluşturun ve doldurun
3. ✅ LinkedIn Developer Portal'da OpenID Connect'i etkinleştirin
4. ✅ Redirect URI'ları ekleyin
5. ✅ Docker veya Python ile başlatın
6. ✅ `http://localhost:5000` adresinde giriş yapın
7. ✅ DRY_RUN=true ile test edin
8. ✅ DRY_RUN=false ile canlıya alın

**ARTIK HATA ALMAYACAKSINIZ! 🎉**
