# GitHub Codespaces'te LinkedIn Agent'ı Çalıştırma Talimatları

Bu dosya, projeyi GitHub Codespaces ortamında sıfırdan kurup çalıştırmak için gereken tüm adımları içerir. Lütfen adımları sırasıyla takip et.

---

### **Adım 1: Gerekli Paketleri Yükle**

Codespace terminaline aşağıdaki komutu kopyalayıp yapıştır ve `Enter`'a bas. Bu komut, projenin çalışması için gereken tüm Python kütüphanelerini yükleyecektir.

```bash
pip install -r requirements.txt
```

---

### **Adım 2: `.env` Yapılandırma Dosyasını Oluştur**

Bu en önemli adımdır. API anahtarın gibi hassas bilgileri bu dosyada saklayacağız.

1.  Terminal'e aşağıdaki komutu yazarak `nano` metin editörünü aç:
    ```bash
    nano .env
    ```

2.  Açılan boş editör ekranına aşağıdaki metnin tamamını kopyalayıp yapıştır:
    ```
    # LinkedIn Credentials
    LINKEDIN_EMAIL="ykursat054@gmail.com"
    LINKEDIN_PASSWORD="34iKYaRt"

    # Google Gemini API Key - ÖNEMLİ: Yapay zekanın çalışması için bu satırı kendi anahtarınla değiştirmelisin.
    GEMINI_API_KEY="SENIN_API_ANAHTARIN_BURAYA_GELECEK"

    # Application Settings
    DATABASE_URL="sqlite:///./linkedin_agent.db"
    ```

3.  **ÇOK ÖNEMLİ:** `SENIN_API_ANAHTARIN_BURAYA_GELECEK` yazan kısmı silip kendi **Google Gemini API** anahtarını bu satıra yapıştır.

4.  Dosyayı kaydetmek için klavyeden **`Ctrl + O`** tuş kombinasyonuna bas ve ardından onaylamak için **`Enter`**'a bas.

5.  Editörden çıkmak için **`Ctrl + X`** tuşuna bas.

---

### **Adım 3: Uygulamayı (Sunucuyu) Başlat**

Artık her şey hazır. Uygulamayı başlatmak için terminale aşağıdaki komutu yapıştır ve `Enter`'a bas:

```bash
uvicorn src.main:app --reload --host 0.0.0.0
```

---

### **Adım 4: Uygulamayı Tarayıcıda Görüntüle**

Sunucu başarıyla başladığında, Codespaces bunu otomatik olarak algılayacaktır.

*   Sağ altta **"Your application running on port 8000 is available."** şeklinde bir bildirim göreceksin. Bu bildirimdeki **"Open in Browser"** düğmesine tıkla.
*   Eğer bildirim çıkmazsa, arayüzün sol tarafındaki menüden **PORTS** sekmesine git. Orada `8000` portunun listelendiğini ve yanında "Forwarded Address" (Yönlendirilen Adres) olarak bir link olduğunu göreceksin. Bu linke tıklayarak uygulamayı açabilirsin.

Bu adımları tamamladıktan sonra LinkedIn Agent'ın kontrol paneli tarayıcında açılacaktır.
