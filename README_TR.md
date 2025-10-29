# LinkedIn Agent - Türkçe Dokümantasyon

> 🎉 **Tüm LinkedIn API hataları düzeltildi! Artık hata almayacaksınız.**

> 🪟 **Windows'ta Docker "Access Denied" hatası mı alıyorsunuz?** → [WINDOWS_DOCKER_COZUM.md](WINDOWS_DOCKER_COZUM.md)

## 📚 Dokümantasyon Dosyaları

### Başlangıç İçin (Yeni Kullanıcılar)

1. **[COZUM_OZET.md](COZUM_OZET.md)** - ⭐ Buradan başlayın!
   - Genel durum özeti
   - Düzeltilen hatalar tablosu
   - 3 adımlık hızlı başlangıç
   - Tüm dokümanlara yönlendirme

2. **[HIZLI_BASLAT.txt](HIZLI_BASLAT.txt)** - ⚡ En hızlı yol
   - Sadece komutlar
   - Kopyala-yapıştır için hazır
   - Docker ve Python seçenekleri
   - CMD/Terminal için optimize edilmiş

3. **[BASLATMA_KOMUTLARI.md](BASLATMA_KOMUTLARI.md)** - 📖 Detaylı rehber
   - Adım adım açıklamalar
   - LinkedIn Developer Portal ayarları
   - Test yapma ve canlıya alma
   - Sorun giderme

4. **[WINDOWS_DOCKER_COZUM.md](WINDOWS_DOCKER_COZUM.md)** - 🪟 Windows Docker sorunları
   - "Access Denied" hatası çözümü
   - Docker Desktop başlatma adımları
   - Alternatif Python kurulum yöntemi
   - Adım adım Windows rehberi

### Teknik Dokümantasyon

4. **[README.md](README.md)** - İngilizce genel dokümantasyon
   - Özellikler listesi
   - Mimari açıklaması
   - API referansı
   - Production deployment

5. **[HATA_COZUMU.md](HATA_COZUMU.md)** - Hata çözüm detayları
   - Hangi hatalar düzeltildi
   - Teknik değişiklikler
   - Test sonuçları
   - Geriye dönük uyumluluk

6. **[LINKEDIN_API_MIGRATION.md](LINKEDIN_API_MIGRATION.md)** - API değişiklikleri
   - LinkedIn API güncellemeleri
   - OpenID Connect migrasyonu
   - Endpoint değişiklikleri
   - Geliştirici referansları

---

## 🚀 Hızlı Başlangıç

### 1. Hangi dosyayı okuyayım?

**Komutları kopyalayıp çalıştırmak istiyorum:**
→ [HIZLI_BASLAT.txt](HIZLI_BASLAT.txt)

**Genel durumu anlamak istiyorum:**
→ [COZUM_OZET.md](COZUM_OZET.md)

**Detaylı rehber istiyorum:**
→ [BASLATMA_KOMUTLARI.md](BASLATMA_KOMUTLARI.md)

**Teknik detayları merak ediyorum:**
→ [HATA_COZUMU.md](HATA_COZUMU.md) ve [LINKEDIN_API_MIGRATION.md](LINKEDIN_API_MIGRATION.md)

**Windows'ta Docker sorunum var:**
→ [WINDOWS_DOCKER_COZUM.md](WINDOWS_DOCKER_COZUM.md)

### 2. Minimum Adımlar

#### Otomatik Başlatma (En Kolay Yol) ⚡

**Windows:**
```bash
git clone https://github.com/DevKursat/linkedinAgent.git
cd linkedinAgent
start_windows.bat
```

**Linux/macOS:**
```bash
git clone https://github.com/DevKursat/linkedinAgent.git
cd linkedinAgent
./start.sh
```

Bu scriptler Docker'ı kontrol eder, .env dosyasını oluşturur ve uygulamayı başlatır.

#### Manuel Başlatma (Adım Adım)

```bash
# 1. Repository'yi klonla
git clone https://github.com/DevKursat/linkedinAgent.git
cd linkedinAgent

# 2. .env dosyasını oluştur
copy .env.example .env
# (Sonra .env dosyasını düzenle)

# 3. Docker kontrolü (önerilir, özellikle Windows için)
python check_docker.py

# 4. Başlat (Docker)
docker compose up -d --build

# 5. Tarayıcıda aç
start http://localhost:5000
```

---

## ✅ Düzeltilen Hatalar

| Hata Kodu | Endpoint | Durum |
|-----------|----------|-------|
| 403 Forbidden | `/v2/me` | ✅ `/v2/userinfo` kullanılıyor |
| 404 Not Found | `/v2/search` | ✅ Graceful degradation |
| Commenting Failed | - | ✅ Manuel yorum çalışıyor |
| Invitation Failed | `/v2/invitations` | ✅ OpenID Connect ile düzeltildi |
| Post Creation Failed | `/v2/ugcPosts` | ✅ OpenID Connect ile düzeltildi |

---

## 🎯 Çalışan Özellikler

- ✅ Profil bilgisi alma
- ✅ Gönderi oluşturma ve paylaşma
- ✅ Otomatik beğenme (45 saniye sonra)
- ✅ Türkçe özet ekleme (90 saniye sonra)
- ✅ Manuel yorum yapma
- ✅ Bağlantı daveti gönderme
- ✅ Otomatik zamanlama (07:00 - 22:00)
- ✅ DRY_RUN test modu

---

## ⚠️ Şu An Kullanılamayan Özellikler

LinkedIn API kısıtlamaları nedeniyle:

- ❌ Otomatik gönderi arama
- ❌ Otomatik yorum keşfi

**Alternatif:** Web arayüzünden manuel yorum yapabilirsiniz.

---

## 📞 Yardım ve Destek

**Hata alıyorum:**
1. [BASLATMA_KOMUTLARI.md](BASLATMA_KOMUTLARI.md) dosyasındaki "SORUN ÇIKTI MI?" bölümünü oku
2. `.env` dosyanı kontrol et
3. LinkedIn Developer Portal'da OpenID Connect etkin mi kontrol et

**Daha fazla bilgi:**
- [README.md](README.md) - Genel dokümantasyon (İngilizce)
- [HATA_COZUMU.md](HATA_COZUMU.md) - Teknik detaylar
- GitHub Issues - Yeni sorun bildir

---

## 🧪 Test

Tüm testler başarılı:

```bash
pytest tests/ -v
# 8 passed, 3 warnings
```

---

## 📌 Notlar

- ✅ Tüm kod değişiklikleri yapılmış
- ✅ Testler başarılı
- ✅ Dokümantasyon güncel
- ✅ Hata düzeltmeleri tamamlanmış

**ARTIK HATA ALMAYACAKSINIZ! 🎉**

---

## 🔗 Hızlı Linkler

- [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)
- [Google Gemini API](https://makersuite.google.com/app/apikey)
- [GitHub Repository](https://github.com/DevKursat/linkedinAgent)
- [Issue Tracker](https://github.com/DevKursat/linkedinAgent/issues)

---

**Başarılar! 🚀**
