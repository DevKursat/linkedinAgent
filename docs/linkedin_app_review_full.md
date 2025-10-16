# LinkedIn App Review Package (Invites-ready)

Bu belge LinkedIn App Review başvurusu için kullanılabilecek eksiksiz bir paket içerir. Amaç: `linkedinAgent` uygulamasının sunucu tarafından bağlantı daveti (invite) gönderebilmesi için gerekli izinlerin (invitations.CREATE veya LinkedIn'in uygun eşdeğeri) talep edilmesi ve doğrulanması.

İçerik
- Kısa açıklama ve kullanım senaryosu
- Teknik örnek istek/cevap (curl)
- Ekran görüntüsü talimatları
- Test adımları
- Güvenlik önlemleri

---

## 1) Kısa açıklama (What & Why)

linkedinAgent, kullanıcı adına profesyonel ağ kurmaya yardımcı olan bir ajan uygulamasıdır. Uygulama, operatör onayı veya önceden tanımlanmış kampanya kuralları çerçevesinde önerilen kişiler için bağlantı daveti gönderebilir. Bu özellik yalnızca LinkedIn tarafından uygulamaya davet oluşturma yetkisi verildiğinde etkinleştirilecektir.

Kullanım örneği:
- Operatör uygulamada hedef kişileri onaylar veya öneri listesi oluşturulur.
- Sunucu, yetkili OAuth token ile LinkedIn'in invitations endpoint'ine POST gönderir.
- Başarılı gönderim sonrası uygulama DB'yi günceller ve istatistikleri gösterir.

## 2) Teknik örnekler

Örnek: legacy/v2 tarzı (App Review sırasında LinkedIn hangi path'ı kabul ediyorsa ona göre uyarlayın)

İstek:

```bash
curl -X POST 'https://api.linkedin.com/v2/invitations' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
    "invitee": {"com.linkedin.voyager.growth.invitation.InviteeProfile": {"profileUrn": "urn:li:person:TARGET_ID"}},
    "message": "Merhaba, sizi profesyonel ağımda görmek isterim. Selamlar, Kürşat."
  }'
```

Başarılı cevap (örnek):

```json
HTTP/1.1 201 Created
{
  "id": "urn:li:invitation:1234567890",
  "status": "SENT"
}
```

Hatalı cevap örnekleri (izin yok):

```json
HTTP/1.1 403 Forbidden
{"status":403,"serviceErrorCode":100,"code":"ACCESS_DENIED","message":"Not enough permissions to access: invitations.CREATE.NO_VERSION"}

HTTP/1.1 404 Not Found
{"status":404,"code":"RESOURCE_NOT_FOUND","message":"No virtual resource found"}
```

Bu hata örnekleri App Review başvurusuna eklenecektir (LinkedIn'in neden iznin gerektiğini ve şu anki hatayı görmesi için).

## 3) Ekran görüntüleri (Screenshots)

App Review sırasında sunulacak ekran görüntüleri:
- `/invites` sayfasının tamamı (davet listesi ve "Sunucudan Gönder" butonu görülecek).
- Network panelinden örnek POST isteği (curl benzeri) ve dönen hata (403/404) görüntüsü.
- `data/manual_invites.html` veya Tampermonkey akışının çalıştığını gösteren browser görüntüsü (opsiyonel).

## 4) Test adımları (local)

1. `.env` içinde LinkedIn client id/secret set edin.
2. `INVITES_ENABLED=true`, `DRY_RUN=false` olarak ayarlayın ve uygulamaya login olun.
3. `/invites` sayfasından bir invite seçip "Sunucudan Gönder" butonuna basın.
4. Eğer izin yoksa 403/404 alınacaktır — bu ekran görüntülerini App Review paketine ekleyin.

## 5) Güvenlik & Mitigasyon

- `INVITES_ENABLED` default `false` (güvenlik). Başvuru onaylanana kadar üretimde açmayın.
- Rate limiting: uygulama `INVITES_PER_HOUR`, `INVITES_MAX_PER_DAY`, `INVITES_BATCH_SIZE` ile sınırlar.
- Manual fallback: başarısız server-side davetlerde `data/manual_invites.html` oluşturulur ve Tampermonkey ile insan-onaylı gönderim yapılır.

## 6) Başvuru metni (örnek)

Title: "Requesting invitations.CREATE permission for linkedinAgent"

Description:
"linkedinAgent is a personal assistant for professional networking. It needs the ability to send connection invitations on behalf of authenticated users as part of an explicit and consented workflow. The feature is disabled by default and can be enabled only after app review. The app enforces rate limits and manual approval paths. We will provide demo steps and a test LinkedIn account to validate the behavior."

---

Dosyalar ve ekler: README, screenshots, example curl.txt, short demo video (opsiyonel).

İsterseniz ben bu paketi zip'leyip GitHub Release'e eklerim. Eğer onay verirseniz devam ediyorum.
