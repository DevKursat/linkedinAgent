# LinkedIn Agent - Tam Otonom Sistem Kurulum Rehberi

Bu rehber, LinkedIn Agent'ı tam otonom bir sistem olarak GitHub Actions ve GitHub Container Registry (GHCR) kullanarak nasıl kuracağınızı adım adım açıklar.

## Genel Bakış

Sistem otomatik olarak:
- Günlük teknoloji haberlerini yoğun saatlerde paylaşır (09:30-11:00, 17:30-19:30)
- Yorumları izler ve yanıtlar
- İlgili gönderilerle proaktif olarak etkileşime geçer
- İstanbul saatine göre sabah 7'den gece 10'a kadar otonom çalışır

## Kurulum Yöntemleri

### Yöntem 1: GitHub Container Registry ile Dağıtım (Önerilen)

Bu yöntem, GitHub Actions'dan önceden oluşturulmuş Docker imajlarını kullanarak üretim ortamına dağıtım yapar.

#### Gereksinimler

1. Bu repository'ye sahip **GitHub Hesabı**
2. Aşağıdaki özelliklere sahip **Sunucu/VPS** (Linux önerilir):
   - Docker ve Docker Compose kurulu
   - Minimum 1GB RAM, 10GB depolama
   - Sürekli internet bağlantısı
3. **LinkedIn Developer App** kimlik bilgileri
4. **Google Gemini API** anahtarı

#### Adım 1: Sunucunuzu Hazırlayın

```bash
# Docker'ı Kurun (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose'u Kurun
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Kurulumu Doğrulayın
docker --version
docker compose version
```

#### Adım 2: Repository'yi Klonlayın ve Yapılandırın

```bash
# Repository'yi klonlayın
git clone https://github.com/DevKursat/linkedinAgent.git
cd linkedinAgent

# Ortam değişkenleri şablonunu kopyalayın
cp .env.example .env

# .env dosyasını kimlik bilgilerinizle düzenleyin
nano .env
```

**Gerekli Ortam Değişkenleri:**

```env
# LinkedIn API Yapılandırması
LINKEDIN_CLIENT_ID=buraya_client_id_girin
LINKEDIN_CLIENT_SECRET=buraya_client_secret_girin
LINKEDIN_REDIRECT_URI=http://sunucu-ip-adresi:5000/callback

# Google Gemini API
GEMINI_API_KEY=buraya_gemini_api_key_girin

# Flask Secret (rastgele bir dize oluşturun)
FLASK_SECRET_KEY=buraya_rastgele_gizli_anahtar_girin

# Üretim için dry run'ı devre dışı bırakın
DRY_RUN=false

# İsteğe bağlı: İlgi alanlarınızı özelleştirin
INTERESTS=ai,llm,product,saas,startup,founder,ux,devtools,infra
```

#### Adım 3: Data Dizinini Oluşturun

```bash
# Kalıcı depolama için data dizini oluşturun
mkdir -p data

# Gerekli stil dosyalarını oluşturun
cat > data/about_me.md << 'EOF'
# Hakkımda
Kişisel biyografinizi buraya yazın...
EOF

cat > data/style.md << 'EOF'
# Gönderi Stili
Gönderi stili yönergelerinizi buraya yazın...
EOF

cat > data/style_comment.md << 'EOF'
# Yorum Stili
Yorum stili yönergelerinizi buraya yazın...
EOF
```

#### Adım 4: Otomatik Dağıtım Scripti ile Başlatın

```bash
# Otomatik dağıtım scriptini çalıştırın
./deploy.sh prod
```

**Alternatif: Manuel Dağıtım**

```bash
# GHCR'dan en son imajı çekin
docker compose -f docker-compose.prod.yml pull

# Servisleri başlatın
docker compose -f docker-compose.prod.yml up -d

# Durumu kontrol edin
docker compose -f docker-compose.prod.yml ps
```

#### Adım 5: LinkedIn ile Kimlik Doğrulama

1. Tarayıcınızda şu adresi açın: `http://sunucu-ip-adresi:5000`
2. "Login with LinkedIn" butonuna tıklayın
3. OAuth akışını tamamlayın
4. Kimlik doğrulamanın başarılı olduğunu doğrulayın

#### Adım 6: Otonom Çalışmayı Doğrulayın

```bash
# Logları kontrol edin
docker compose -f docker-compose.prod.yml logs -f

# Worker'ın çalıştığını doğrulayın
docker compose -f docker-compose.prod.yml logs worker

# Web servisini kontrol edin
curl http://localhost:5000/health
```

### Yöntem 2: Yerel Olarak Derleme ve Dağıtım

Docker imajlarını kendiniz derlemek istiyorsanız bu yöntemi kullanın.

```bash
# Servisleri derleyin ve başlatın
docker compose up -d --build

# Durumu kontrol edin
docker compose ps

# Logları görüntüleyin
docker compose logs -f
```

## GitHub Actions CI/CD

Repository, aşağıdaki otomatik CI/CD'yi içerir:

1. **Pull Request'te:**
   - Sözdizimi kontrolleri çalıştırır
   - Tüm testleri çalıştırır
   - Kod kalitesini doğrular

2. **Main'e Push'ta:**
   - Tüm testleri çalıştırır
   - Docker imajı derler
   - GitHub Container Registry'ye (ghcr.io) push eder
   - Branch adı ve commit SHA ile etiketler

### Workflow Dosyası: `.github/workflows/ci.yml`

Workflow, main branch'e her push'ta otomatik olarak Docker imajları derler ve yayınlar.

## İzleme ve Bakım

### Sağlık Kontrolleri

```bash
# Sistem sağlığını kontrol edin
./healthcheck.sh

# Manuel kontrol
curl http://localhost:5000/health
```

### Log İzleme

```bash
# Tüm logları görüntüleyin
docker compose -f docker-compose.prod.yml logs -f

# Sadece worker loglarını görüntüleyin
docker compose -f docker-compose.prod.yml logs -f worker

# Sadece web loglarını görüntüleyin
docker compose -f docker-compose.prod.yml logs -f web

# Son 100 satırı görüntüleyin
docker compose -f docker-compose.prod.yml logs --tail=100
```

### Veritabanı Yedekleme

```bash
# Veritabanını yedekleyin
cp data/bot.db data/bot.db.backup.$(date +%Y%m%d_%H%M%S)

# Yedekten geri yükleyin
cp data/bot.db.backup.YYYYMMDD_HHMMSS data/bot.db
docker compose -f docker-compose.prod.yml restart
```

## En Son Sürüme Güncelleme

```bash
# En son kodu çekin
git pull origin main

# En son Docker imajını çekin
docker compose -f docker-compose.prod.yml pull

# Servisleri yeniden başlatın
docker compose -f docker-compose.prod.yml up -d

# Güncellemeyi doğrulayın
docker compose -f docker-compose.prod.yml logs --tail=50
```

## Sorun Giderme

### Container Başlamıyor

```bash
# Container loglarını kontrol edin
docker compose -f docker-compose.prod.yml logs

# Container durumunu kontrol edin
docker compose -f docker-compose.prod.yml ps -a

# Servisleri yeniden başlatın
docker compose -f docker-compose.prod.yml restart
```

### Kimlik Doğrulama Sorunları

1. `LINKEDIN_REDIRECT_URI`'nin LinkedIn app ayarlarınızla eşleştiğini doğrulayın
2. `LINKEDIN_CLIENT_ID` ve `LINKEDIN_CLIENT_SECRET`'in doğru olduğundan emin olun
3. LinkedIn app'inizdeki redirect URI'nin sunucunuzun public IP/domain'ini içerdiğini kontrol edin

### Worker Gönderi Yapmıyor

1. .env dosyasında `DRY_RUN`'ın `false` olarak ayarlandığını kontrol edin
2. `GEMINI_API_KEY`'in geçerli olduğunu doğrulayın
3. Çalışma saatlerini kontrol edin (İstanbul saatiyle 7-22 arası)
4. Worker loglarını inceleyin: `docker compose logs worker`

### Yüksek Bellek Kullanımı

```bash
# Kaynak kullanımını kontrol edin
docker stats

# Gerekirse servisleri yeniden başlatın
docker compose -f docker-compose.prod.yml restart
```

## Sürekli Çalışma için Sunucu Kurulumu

### systemd Kullanımı (Linux Sunucular için Önerilen)

systemd servis dosyası oluşturun:

```bash
sudo nano /etc/systemd/system/linkedinagent.service
```

Bu içeriği ekleyin:

```ini
[Unit]
Description=LinkedIn Agent
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/linkedinAgent/klasor/yolu
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Etkinleştirin ve başlatın:

```bash
sudo systemctl daemon-reload
sudo systemctl enable linkedinagent
sudo systemctl start linkedinagent

# Durumu kontrol edin
sudo systemctl status linkedinagent
```

## Güvenlik En İyi Uygulamaları

1. **Güçlü Gizli Anahtarlar Kullanın:**
   ```bash
   # Rastgele gizli anahtar oluşturun
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Ağ Erişimini Sınırlayın:**
   - Port 5000'i güvenilir IP'lerle sınırlamak için firewall kullanın
   - SSL ile reverse proxy (nginx) kullanmayı düşünün

3. **Düzenli Güncellemeler:**
   ```bash
   # Haftalık güncelleme programı
   git pull && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d
   ```

4. **Logları İzleyin:**
   - Log rotasyonu ayarlayın
   - Hatalar ve olağandışı aktiviteler için izleyin

5. **Veriyi Yedekleyin:**
   - Veritabanı yedeklemelerini otomatikleştirin
   - Yedekleri güvenli bir konumda saklayın

## Destek

- **Sorunlar:** https://github.com/DevKursat/linkedinAgent/issues
- **Dokümantasyon:** Repository'deki README.md ve diğer dokümanları kontrol edin
- **Loglar:** Her zaman önce logları kontrol edin: `docker compose logs`

📖 **Detaylı İngilizce dokümantasyon için [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) dosyasına bakın**

## Lisans

MIT - Detaylar için LICENSE dosyasına bakın
