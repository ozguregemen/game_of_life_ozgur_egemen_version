# Özgür Egemen Cellular Automata Lab

Pygame ile hazırlanmış, Conway's Game of Life ve farklı cellular automata
kurallarını çalıştıran etkileşimli bir simülasyon ve pattern editörü.

## Kurulum

Python 3.10 veya daha yeni bir sürüm önerilir.

```powershell
python -m pip install -r requirements.txt
python life.py
```

Python 3.14 kullanıyorsanız proje `pygame-ce` ile çalışır. Kod içindeki import
satırı yine `import pygame` olarak kalır.

## Ana özellikler

- Conway, HighLife, Day & Night ve Seeds kuralları
- İki türün Conway kurallarıyla rekabet ettiği Immigration Game modu
- Üç durumlu dalga ve parçacıklar üreten Brian's Brain modu
- Basit dönüş kurallarından karmaşık izler üreten Langton's Ant modu
- İletken hatlar üzerinde elektron sinyalleri çalıştıran Wireworld modu
- Sekiz rengin eşik tabanlı olarak birbirini tükettiği Cyclic Cellular Automaton modu
- Açıklamalı mod seçme paneli ve moda göre değişen bağlamsal sağ menü
- Hücre yaşı ve yaşa bağlı renkler
- Doğma/ölme geçiş animasyonları
- Aktivite heatmap'i ve ölü hücre izleri
- 50 nesillik geri alma geçmişi
- Her oyun moduna özel, durumları koruyan hazır ve kullanıcı patternleri
- Pattern döndürme, yatay/dikey çevirme ve yerleştirme önizlemesi
- Otomatik pattern recognition
- Classic, Neon ve Pastel temaları
- Zoom, pan, koordinat ve quadrant görünümü
- Yeniden boyutlandırıldığında simülasyonu koruyan sabit mantıksal grid

## Kontroller

| Kontrol | İşlev |
|---|---|
| Sol tık/sürükle | Hücre oluştur |
| Sağ tık/sürükle | Hücre sil |
| Orta tuş/sürükle | Görünümü taşı |
| Fare tekerleği | Zoom |
| Space | Başlat / durdur |
| M | Açıklamalı mod seçme panelini aç / kapat |
| T | Immigration türünü, Wireworld fırçasını veya Cyclic renk fırçasını değiştir; Langton karıncasını döndür |
| Shift + Sol tık | Langton karıncasını seçilen hücreye taşı |
| N | Simülasyon duraklatılmışken tek nesil ilerlet |
| Yukarı / Aşağı | Simülasyon hızını değiştir |
| G | Grid çizgilerini aç/kapat |
| H | Heatmap aç/kapat |
| A | Hücre yaşlarını aç/kapat |
| C | Görünümü ortala |
| R | Seçili patterni 90° döndür |
| F | Seçili patterni yatay çevir |
| V | Seçili patterni dikey çevir |
| Esc | Pattern seçimini iptal et |
| 1–9 | İlk hazır patternlerden birini seç |
| `[` / `]` | Zoom out / zoom in |

## Düzeltilen temel sorunlar

- Canlı hücre sayısı artık hücre yaşlarının toplamını değil gerçek hücre
  sayısını gösterir.
- Pattern recognition gerçek pattern boyutlarını kullanır ve hücre yaşlarını
  canlı/ölü değerlerine normalize eder.
- İstatistik çubuğu doğru çizim sırasına alındı.
- Pencere yeniden boyutlandırıldığında grid sıfırlanmaz.
- Heatmap, yaş sayıları, koordinatlar ve quadrant seçenekleri arayüze bağlandı.
- Pattern önizlemesi döndürme ve flip işlemlerini yansıtır.
- Kaydedilen özel pattern artık tüm grid yerine canlı hücrelerin bounding
  box'ını içerir.
- Simülasyon hızı, arayüzün render FPS'inden ayrıldı.
- Hücre geçişleri yalnızca doğma/ölme durumlarında başlatılır.
- Randomize ve Clear işlemleri ilgili yardımcı gridleri ve generation
  durumunu tutarlı biçimde sıfırlar.

## Dosyalar

- `life.py`: Güncel 2D uygulama
- `immigration.py`: İki tür ve çoğunluk kalıtımı kullanan Immigration Game çekirdeği
- `brians_brain.py`: Üç durumlu Brian's Brain kural çekirdeği
- `langtons_ant.py`: Langton karıncasının yön, renk çevirme ve hareket çekirdeği
- `wireworld.py`: Dört durumlu Wireworld kural ve istatistik çekirdeği
- `cyclic_automaton.py`: Çok renkli, eşik tabanlı Cyclic Cellular Automaton çekirdeği
- `mode_registry.py`: Mod adları, açıklamaları, renkleri ve bağlamsal kontrol tanımları
- `mode_patterns.py`: Life dışındaki modların hazır pattern ve başlangıç durumları
- `rules.py`: Kurallar ve pattern recognition
- `patterns.py`: Hazır ve özel pattern yönetimi
- `themes.py`: Temalar ve menü bileşenleri
- `visuals.py`: Animasyon ve görsel yardımcılar
- `life3d.py`: Deneysel 3D slice sürümü
- `life2d_backup.py`: Eski 2D sürüm yedeği

## Test

```powershell
python -m unittest discover -s tests
```

Test paketi Conway kurallarını, pattern tanıma/depolama davranışını, atomik
pattern yerleştirmeyi; moda özel pattern filtreleme ve çok durumlu pattern
depolamayı; Immigration, Brian's Brain, Langton's Ant, Wireworld ve Cyclic Automaton
kurallarını; mod registry ve bağlamsal menü davranışını; altı modun SDL dummy video driver ile
başlangıcını kapsar.

## Bağlamsal arayüz

`M` tuşu veya sağ menüdeki `Select Mode` düğmesi, altı simülasyonu açıklamalı
kartlar halinde gösterir. Kartlar fareyle ya da `1`–`6` tuşlarıyla seçilebilir.
Bir mod seçildiğinde çalışan simülasyon duraklatılır; diğer modların grid ve geri
alma geçmişleri korunur.

Sağ menünün ilk bölümü seçilen moda göre yeniden kurulur. Life-like modunda kural,
heatmap ve yaş kontrolleri; Immigration'da iki tür fırçası; Langton's Ant'te dönüş
kontrolü; Wireworld'de renkli iletken, elektron başı ve elektron kuyruğu fırçaları;
Cyclic Automaton'da renk fırçası ve temas eşiği
gösterilir. Seçili tür veya fırça renkli çerçeveyle belirtilir. Ortak temizleme,
randomize, geri alma, pattern, tema ve görünüm kontrolleri her modda erişilebilir
kalır.

## Moda özel patternler

`Show Patterns` yalnızca açık olan simülasyona uygun patternleri gösterir. Life-like
modu klasik block, blinker, glider ve benzeri Life patternlerini; Immigration iki
türün dağılımını koruyan renkli block, blinker ve glider örneklerini; Brian's Brain
ateşlenen ve ölmekte olan durumları birlikte kullanan osilatör ve wickstretcher
örneklerini gösterir. Langton patternleri siyah/beyaz hücrelere ek olarak karıncanın
göreli konumunu ve yönünü de saklar.

Wireworld menüsünde hareket eden düz sinyal, ileri/ters diyot çifti ve clocked XOR
devresi bulunur. Bu patternlerde iletken, elektron başı ve elektron kuyruğu ayrı
durumlar olarak korunur. Pattern döndürme ve çevirme işlemleri çok durumlu hücreleri;
Langton modunda ayrıca karıncanın konum ve yönünü dönüştürür.

Cyclic Automaton menüsü diagonal faz gradyanı, iç içe renk halkaları ve sekiz
durumlu renk çarkı başlangıçlarını içerir. Bu modda renk `0` boşluk değil gerçek bir
faz olduğu için pattern yerleştirilirken şeffaf sayılmaz.

Kaydedilen özel pattern JSON'ları seçili modun adını içerir ve yalnızca o modun
menüsünde görünür. Eski, `mode` alanı bulunmayan JSON dosyaları geriye uyumluluk için
Life-like patterni olarak yüklenir.

## Immigration Game

Immigration Game, Conway'in `B3/S23` doğum ve hayatta kalma kurallarını iki türe
uygular. Hayatta kalan hücre türünü korur. Ölü bir hücrenin tam üç canlı komşusu
varsa doğar ve bu üç ebeveyn arasındaki çoğunluk türünü alır.

Tür A mavi, Tür B turuncu çizilir. Sol tık aktif türü yerleştirir, sağ tık hücreyi
siler ve `T` aktif türü değiştirir. Randomize iki türü yaklaşık eşit dağıtır.
Life-like ve Immigration grid'leri ile geri alma geçmişleri ayrı tutulur; mod
değiştirmek diğer simülasyonun durumunu bozmaz.

## Brian's Brain

Brian's Brain üç hücre durumu kullanır: kapalı, ateşlenen ve ölmekte olan. Kapalı
bir hücre yalnızca tam iki ateşlenen komşusu varsa ateşlenir. Ateşlenen hücre bir
sonraki nesilde ölmekte olan duruma, ardından kapalı duruma geçer. Ölmekte olan
hücreler doğum hesabında komşu sayılmaz.

Ateşlenen hücreler açık camgöbeği, ölmekte olan hücreler koyu mor çizilir. Sol
tık ateşlenen hücre yerleştirir, sağ tık siler. Hazır patternler ateşlenen ve
ölmekte olan hücreleri birlikte içeren doğrulanmış başlangıç durumlarıdır. Brian's Brain de
kendi grid, generation ve geri alma geçmişini korur.

## Langton's Ant

Langton karıncası beyaz hücrede sağa döner ve hücreyi siyaha boyar; siyah hücrede
sola döner ve hücreyi beyaza boyar. Ardından yeni yönünde bir hücre ilerler. Bu
iki basit kural önce düzensiz izler, yeterince uzun koşularda ise düzenli bir
"otoyol" davranışı oluşturabilir.

Sol tık siyah, sağ tık beyaz hücre çizer. `T` karıncayı bulunduğu yerde saat
yönünde döndürür; `Shift + Sol tık` karıncayı yeni bir hücreye taşır. `Clear Grid`
beyaz bir tahta ve kuzeye bakan merkez karıncası oluşturur. Mevcut grid politikası
wrap kullanmadığı için karınca sınırdan çıkarsa simülasyon kontrollü biçimde durur.

## Wireworld

Wireworld dört hücre durumu kullanır: boş, elektron başı, elektron kuyruğu ve
iletken. Boş hücreler boş kalır. Elektron başı bir sonraki nesilde kuyruğa, kuyruk
ise iletkene dönüşür. Bir iletken, sekiz komşusu arasında tam bir veya iki elektron
başı varsa yeni elektron başına dönüşür; aksi halde iletken kalır.

Boş alan siyah, iletken sarı, elektron başı mavi ve elektron kuyruğu kırmızı
çizilir. Sol tık seçili durumu yerleştirir, sağ tık hücreyi siler. `T`, iletken,
elektron başı ve elektron kuyruğu fırçaları arasında geçer. Hazır devre patternleri
üç durumu da doğrudan yerleştirir. Elle bir devreyi çalıştırmak için iletken hat
üzerine en az bir elektron başı; yönlü bir başlangıç için başın arkasına bir
elektron kuyruğu çizilebilir.

## Cyclic Cellular Automaton

Cyclic Cellular Automaton sekiz renk durumu kullanır. `s` durumundaki bir hücre,
sekiz hücreli Moore komşuluğunda en az seçili eşik kadar `(s + 1) mod 8` rengi
bulunuyorsa bu sonraki renge geçer; aksi halde rengini korur. Tüm hücreler aynı
anda güncellenir ve grid sınırları diğer modlarda olduğu gibi sonludur. Bu temas
tabanlı renk ilerleme tanımı, Fisch, Gravner ve Griffeath'in
[CCA çerçevesini](https://arxiv.org/abs/patt-sol/9304001) izler.

`Randomize` sekiz rengi eşit olasılıkla dağıtarak dalga ve spiral oluşumu için
uygun bir başlangıç sağlar. Sol tık seçili rengi, sağ tık renk `0`'ı çizer; `T`
renk fırçasını ilerletir. Sağ menüdeki threshold düğmesi temas eşiğini `1`–`8`
arasında döndürür. Düşük eşikler hareketli renk cepheleri üretirken yüksek eşikler
daha kolay kilitlenen veya durağan düzenlere yol açabilir.
