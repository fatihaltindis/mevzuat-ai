# ⚖️ Mevzuat AI — Kurulum Kılavuzu

Türk mevzuatında yapay zekâ destekli arama ve analiz aracı.
Hâkimler, avukatlar ve hukuk araştırmacıları için tasarlanmıştır.

**💰 Tamamen ücretsiz — Google Gemini ile çalışır.**

---

## Bu Uygulama Ne Yapar?

Sorunuzu doğal Türkçe ile yazarsınız, yapay zekâ sizin için:

- **mevzuat.gov.tr** üzerinde otomatik arama yapar
- İlgili kanun, yönetmelik veya KHK metnini bulur ve okur
- Belirli maddeleri tespit eder
- Sorunuza anlaşılır bir Türkçe ile yanıt verir

Örnek sorular:
- "Türk Ceza Kanunu'nun 141. maddesi ne diyor?"
- "İş Kanunu'na göre yıllık izin hakkı kaç gündür?"
- "KVKK'ya göre veri sorumlusunun yükümlülükleri nelerdir?"

---

## Kurulum (Tek Seferlik, ~5 dakika)

### Adım 1: Python Yükleyin

Bilgisayarınızda Python yoksa:

1. **https://www.python.org/downloads/** adresine gidin
2. "Download Python 3.x" butonuna tıklayın
3. Kurulumda **"Add Python to PATH"** kutucuğunu mutlaka işaretleyin ✅
4. "Install Now" ile kurulumu tamamlayın

### Adım 2: Ücretsiz API Anahtarı Alın

Bu uygulama, Google'ın Gemini yapay zekâsını kullanır. API anahtarı ücretsizdir:

1. **https://aistudio.google.com/apikey** adresine gidin
2. Google hesabınızla giriş yapın
3. "Create API key" butonuna tıklayın
4. Anahtarı kopyalayın

> ✅ **Tamamen ücretsiz.** Kredi kartı gerekmez. Günlük ~1500 istek hakkınız var.

### Adım 3: Uygulamayı Başlatın

#### Windows:
`baslat.bat` dosyasına çift tıklayın. İlk çalıştırmada gerekli paketler otomatik yüklenir.

#### Mac / Linux:
Terminal açın ve şu komutları çalıştırın:
```
cd mevzuat-ai
chmod +x baslat.sh
./baslat.sh
```

Tarayıcınızda otomatik olarak uygulama açılacaktır (genellikle http://localhost:8501).

### Adım 4: API Anahtarını Girin

Uygulama açıldığında sol panelde "Google Gemini API Anahtarı" alanına anahtarınızı yapıştırın.

---

## Kullanım

1. Sol panelden örnek bir soru seçin veya alt kısımdaki metin alanına sorunuzu yazın
2. Enter'a basın
3. Yapay zekâ mevzuat.gov.tr'de arama yapacak ve yanıtını verecektir
4. Sohbet devam eder — takip soruları sorabilirsiniz

---

## Sık Sorulan Sorular

**S: İnternet bağlantısı gerekli mi?**
C: Evet. Uygulama hem mevzuat.gov.tr'ye hem de Google Gemini API'sine bağlanır.

**S: Gerçekten ücretsiz mi?**
C: Evet. Google Gemini'nin ücretsiz katmanı günde yaklaşık 1500 istek sunar. Normal kullanımda bu fazlasıyla yeterlidir.

**S: Verilerim güvende mi?**
C: Sorularınız yalnızca Google Gemini API'sine gönderilir. Başka hiçbir yere kaydedilmez.

**S: Hukuki danışmanlık yerine geçer mi?**
C: Hayır. Bu araç bilgi amaçlıdır ve doğrudan mevzuat metinlerini sunar. Nihai hukuki değerlendirme her zaman uzman kişiye aittir.

**S: "Günlük limit" hatası alıyorsam?**
C: Ücretsiz katmanın günlük sınırına ulaşılmış olabilir. Birkaç saat bekleyip tekrar deneyin.

**S: Uygulama açılmıyorsa ne yapmalıyım?**
C: Terminal/komut istemcisinde şu komutu deneyin:
```
pip install streamlit google-genai requests
streamlit run app.py
```

---

## Dosya Yapısı

```
mevzuat-ai/
├── app.py              ← Ana uygulama (Streamlit arayüzü)
├── ai_agent.py         ← Yapay zekâ motoru (Gemini function calling)
├── mevzuat_client.py   ← mevzuat.gov.tr API bağlantısı
├── requirements.txt    ← Python paket listesi
├── baslat.bat          ← Windows başlatıcı
├── baslat.sh           ← Mac/Linux başlatıcı
└── KURULUM.md          ← Bu dosya
```
