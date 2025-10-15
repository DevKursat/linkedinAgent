# Simüle Gelen Yorum (Webhook) — Kurulum ve Test

Bu belge, LinkedIn web arayüzünde yaptığınız bir yorumu ajan sunucusuna otomatik olarak iletmek için hızlı bir yol sunar.

Özet: bir Tampermonkey userscript kurup tarayıcıda çalıştırdığınızda, her yorum gönderildiğinde script otomatik olarak `/incoming_comment` endpoint'ine JSON POST gönderir. Sunucu `handle_incoming_comment` ile yanıt üretecek ve eğer `DRY_RUN=false` ise gerçek bir LinkedIn reply denemesi yapar.

Önemli güvenlik notu
- Bu script tarayıcınızdan LinkedIn DOM'u okur ve yerel makinanıza istek gönderir. Sadece güvenilir makinelerde ve güvenli ağlarda kullanın.
- `AGENT_ENDPOINT` ayarını eğer ajan farklı bir makinede çalışıyorsa değiştirin (ör. `http://192.168.1.10:5000/incoming_comment`).

Kurulum
1. Tarayıcınıza Tampermonkey veya benzeri bir userscript yöneticisi kurun.
2. Yeni bir script oluşturun ve `scripts/tampermonkey/linkedin-forward-comment.user.js` içeriğini yapıştırın.
3. Script etkinleştirildikten sonra LinkedIn'de oturum açın.

Test etme
- Basit test: Sunucunuz çalışıyorsa (`python3 src/main.py` veya docker-compose`), LinkedIn'de bir gönderiye yorum yazın. Script ilgili DOM düğümünü algılarsa, yerel sunucuya bir POST gönderir.
- Sunucu tarafı manuel test: UI içindeki "Simüle Gelen Yorum" formunu kullanın (`/` ana sayfasında) veya curl ile test edin:

```bash
curl -X POST http://localhost:5000/incoming_comment \
  -H 'Content-Type: application/json' \
  -d '{"post_urn":"urn:li:share:7383065061520490496","comment_id":"sim-12345","actor":"urn:li:person:me","text":"Test yorum, lütfen cevapla","reply_as_user":true}'
```

DRY_RUN önerisi
- İlk testlerde `.env` içindeki `DRY_RUN=true` bırakmanızı öneririz, böylece ajan gerçek LinkedIn'e yazmaz. `manage.py set-dry-run false` komutu ile canlı moda geçebilirsiniz.

Sorun giderme
- Eğer yorum gönderimi yapılmıyorsa, sunucunun loglarına bakın (`docker-compose logs` veya terminal çıktısı). Ayrıca `data/alerts.log` dosyası hataları içerir.

