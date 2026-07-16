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

Gerçek 3D görünüm, `requirements.txt` ile kurulan ModernGL üzerinden OpenGL 3.3
core context kullanır. OpenGL 3.3 desteklemeyen bir ekran sürücüsünde 1D ve 2D
çalışmaya devam eder; 3D seçimi ise anlaşılır bir hata mesajıyla engellenir.

## Ana özellikler

- 1D / 2D / 3D çalışma alanlarını gösteren üst seviye boyut seçici
- Elementary, totalistic, çok durumlu, geniş komşuluklu, higher-order ve reversible
  kurallar için genelleştirilmiş 1D çalışma alanı
- B6/S567 ve B5/S45 spatial Life kurallarıyla çalışan, depth test ve ışıklandırmalı
  voxel görünümü, orbit kamera ve doğrudan voxel düzenleme sunan 3D çalışma alanı
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
- Sürüklenebilir generation timeline, doğrudan nesle gitme ve ileri/geri oynatma
- Tam grid kopyaları yerine periyodik checkpoint + hücre/satır deltaları kullanan geçmiş
- Population, density, entropy ve değişim oranı zaman serilerini gösteren bilimsel panel
- Periyot/stabilizasyon algılama ve ortak koşullarda 1D Wolfram rule karşılaştırması
- 1D space-time PNG, 2D grid PNG, timeline GIF/MP4, ölçüm CSV ve deney JSON dışa aktarma
- Katlanabilir sidebar, tooltip, bağlamsal F1 yardımı ve belirgin run/pause/araç rozetleri
- Aranabilir/favorilenebilir Elementary rule kataloğu ve son kullanılan deneyler
- Durumları yalnız renkle anlatmayan, renk körlüğüne uygun yüksek kontrastlı tema
- Her oyun moduna özel, durumları koruyan hazır ve kullanıcı patternleri
- Pattern döndürme, yatay/dikey çevirme ve yerleştirme önizlemesi
- Otomatik pattern recognition
- Classic, Neon, Pastel, Midnight, Paper ve renk-körü güvenli Colorblind temaları
- Zoom, pan, koordinat, quadrant ve 2D tahtayı pencereye sığdırma görünümü
- 1D'de tüm viewport'u kaplayan sanal grid ve Compact/Viewport/Wide seed genişlikleri
- Yeniden boyutlandırıldığında simülasyonu koruyan sabit mantıksal grid
- Tüm boyutları, modları ve kamera konumlarını içeren sürümlü JSON oturumları
- Rule, boundary ve seed'i yeniden kullanılabilir yapan 1D deney profilleri

## Kontroller

| Kontrol | İşlev |
|---|---|
| Sol tık/sürükle | Hücre oluştur |
| Sağ tık/sürükle | Hücre sil |
| Orta tuş/sürükle | Görünümü taşı |
| Fare tekerleği | Zoom |
| Space veya üstteki RUN/PAUSE rozeti | Başlat / durdur |
| F1 veya `?` | Bağlamsal klavye ve etkileşim yardımını aç / kapat |
| P | Session & Experiment Manager panelini aç / kapat |
| Ctrl + S | Tüm uygulama durumunu `Last Session` olarak hızlı kaydet |
| Ctrl + O | `Last Session` oturumunu yükle |
| Ctrl + 0 | Sonlu 2D tahtayı veya tam 3D volume'u pencereye sığdır |
| D | 1D / 2D / 3D boyut seçme panelini aç / kapat |
| M | 2D çalışma alanında açıklamalı mod seçme panelini aç / kapat |
| E | 1D çalışma alanında 0–255 rule kataloğunu aç / kapat |
| T | Immigration türünü, Wireworld fırçasını veya Cyclic renk fırçasını değiştir; Langton karıncasını döndür |
| Shift + Sol tık | Langton karıncasını seçilen hücreye taşı |
| N | Simülasyon duraklatılmışken tek nesil ilerlet |
| J | Timeline içinde kayıtlı bir generation'a doğrudan git |
| I | Bilimsel analiz ve 1D rule karşılaştırma panelini aç / kapat |
| X | Bağlamsal dışa aktarma panelini aç / kapat |
| Yukarı / Aşağı | Simülasyon hızını değiştir |
| G | Grid çizgilerini aç/kapat |
| H | Heatmap aç/kapat |
| A | Hücre yaşlarını aç/kapat |
| C | Görünümü ortala |
| R | Seçili patterni 90° döndür |
| F | Seçili patterni yatay çevir |
| V | Seçili patterni dikey çevir |
| Esc | Pattern seçimini iptal et |
| 1–9 | Pattern menüsünde görünen kategori veya patterni seç; gridde ilk hazır patternlerden birini seç |
| Backspace / Sol ok | Pattern alt menüsünden kategori listesine dön |
| `[` / `]` | Zoom out / zoom in |
| 3D'de sol sürükle | Orbit kamerayı volume çevresinde döndür |
| 3D'de orta sürükle | Kamera hedefini düzlem üzerinde taşı |
| 3D'de sol tık | İşaretlenen voxel'in yanına yeni voxel ekle |
| 3D'de sağ tık | İşaretlenen voxel'i sil |
| B | 3D çalışma alanında fixed / wrap / reflect sınırını değiştir |
| K | 3D çalışma alanında 26 komşulu Moore / 6 komşulu face ailesini değiştir |

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

- `life.py`: Uygulama kabuğu, pencere koordinasyonu ve mevcut 2D mod uygulamaları
- `workspaces/base.py`: Ortak workspace controller/renderer sözleşmesi ve registry
- `workspaces/elementary_1d.py`: 1D state, history, input, sidebar ve renderer
- `workspaces/two_dimensional.py`: Altı mevcut 2D modu ortak workspace akışına bağlayan adaptör
- `workspaces/three_dimensional.py`: 3D volume state, dünya-uzayı input, timeline, sidebar ve renderer
- `dimension_registry.py`: 1D / 2D / 3D çalışma alanı metadata tanımları
- `elementary_ca.py`: Wolfram elementary cellular automata kural çekirdeği
- `one_dimensional_ca.py`: Sonlu durumlu genel 1D rule-family motoru
- `three_dimensional_ca.py`: Sınırlı uint8 volume, 3D komşuluk ve slice çekirdeği
- `three_dimensional_rules.py`: Binary 3D Life-like kural tanımları ve toplu geçiş motoru
- `three_dimensional_rendering.py`: Orbit kamera, ray/voxel seçimi ve instanced cube renderer
- `three_dimensional_display.py`: Pygame yazılım ekranı ile ModernGL 3D ekranı arasında geçiş ve UI compositing
- `surface_rasterizer.py`: NumPy/surfarray tabanlı ortak 2D state-plane çizicisi
- `immigration.py`: İki tür ve çoğunluk kalıtımı kullanan Immigration Game çekirdeği
- `brians_brain.py`: Üç durumlu Brian's Brain kural çekirdeği
- `langtons_ant.py`: Langton karıncasının yön, renk çevirme ve hareket çekirdeği
- `wireworld.py`: Dört durumlu Wireworld kural ve istatistik çekirdeği
- `cyclic_automaton.py`: Çok renkli, eşik tabanlı Cyclic Cellular Automaton çekirdeği
- `mode_registry.py`: Mod adları, açıklamaları, renkleri ve bağlamsal kontrol tanımları
- `mode_patterns.py`: Life dışındaki modların hazır pattern ve başlangıç durumları
- `rules.py`: Kurallar ve pattern recognition
- `patterns.py`: Hazır ve özel pattern yönetimi
- `session_storage.py`: Sürümlü oturum/profile şeması, doğrulama ve güvenli JSON depolama
- `session_ui.py`: Oturum kataloğu, 1D profil menüsü ve modal input/render akışı
- `timeline_history.py`: Checkpoint/delta geçmiş motoru, dallanma ve doğrudan frame/nesil erişimi
- `timeline_ui.py`: Sürüklenebilir ortak timeline, ileri/geri oynatma ve checkpoint göstergeleri
- `scientific_analysis.py`: Normalize ölçümler, periyot/stabilizasyon algılama ve 1D karşılaştırma motoru
- `analysis_ui.py`: Canlı metrik grafikleri ve arka plan rule karşılaştırma paneli
- `help_ui.py`: F1 / `?` ile açılan bağlamsal kısayol ve etkileşim yardım paneli
- `ui_preferences.py`: Rule favorileri ve son kullanılan deneyler için yerel tercihler
- `exporting.py`: Güvenli raster, GIF/MP4, CSV/JSON kodlama ve arka plan export motoru
- `experiment_exports.py`: Workspace snapshot'larını bağlamsal çıktı formatlarına dönüştüren coordinator
- `export_ui.py`: Aktif workspace'e göre değişen dışa aktarma paneli
- `themes.py`: Temalar ve menü bileşenleri
- `visuals.py`: Animasyon ve görsel yardımcılar
- `life3d.py`: Deneysel 3D slice sürümü
- `life2d_backup.py`: Eski 2D sürüm yedeği
- `benchmarks/render_benchmark.py`: Mod bazında tekrar çalıştırılabilir render ölçümü

## Workspace mimarisi

Çalışan her boyut, `WorkspaceController` ve `WorkspaceRenderer` ikilisi olarak
`WorkspaceRegistry` içine kaydedilir. Controller; generation, history, input,
sidebar, clear/randomize ve görünüm komutlarını standartlaştırır. Renderer ise
viewport cache anahtarı, temel çizim, dinamik katmanlar, bilgi/istatistik barları ve
modal çizimini üstlenir. Ana event loop seçili boyutun ayrıntılarını bilmeden bu
ortak arayüzü çağırır.

Genelleştirilmiş 1D ve donanım hızlandırmalı 3D CA kendi state/controller/renderer modüllerinde
yaşar. Mevcut 2D modlar davranışları değiştirilmeden bir workspace adaptörüyle aynı
akışa bağlanmıştır. Ana event loop üç boyutta da aynı workspace sözleşmesini kullanır.

## UI'dan bağımsız 3D çekirdek

3D workspace'in state katmanı `three_dimensional_ca.py` içinde Pygame'den bağımsızdır.
`Volume3D`, hücreleri kanonik `(z, y, x)` / `(depth, rows, columns)`
sırasıyla C-contiguous NumPy `uint8` dizisinde tutar. İki ile 256 durum desteklenir;
dışarı verilen volume ve sıfır-kopya slice görünümleri salt okunurdur. Hücre ve plane
değişiklikleri state/shape doğrulaması yapan metotlardan geçer.

Sınır politikaları sabit dış durum (`fixed`), periyodik uzay (`wrap`) ve aynalı kenar
(`reflect`) seçeneklerini içerir. Sabit sınırın dış durumu ayrıca seçilebildiği için
rule katmanı ileride tekdüze dış arka planı nesiller arasında evrimleştirebilir.
Hazır komşuluklar radius-1 Moore (26 hücre) ve Von Neumann (6 hücre) tanımlarıdır;
özel, merkezsiz ve tekrarsız `(dz, dy, dx)` offset kümeleri de kabul edilir. Seçilen
durumların bütün volume için komşu sayısı NumPy ile toplu hesaplanır.

Varsayılan güvenlik bütçesi eksen başına 256 hücre, tek volume için 16.777.216 hücre
/ 16 MiB ve komşu hesabı geçici dizileri için 128 MiB'dir. Daha küçük limit profili
enjekte edilebilir; allocation gerçekleşmeden önce axis, cell, byte ve çalışma seti
kontrol edilir. `extract_slice()` Z için `(rows, columns)`, Y için
`(depth, columns)`, X için `(depth, rows)` düzlemi verir. Bu 2D `uint8` plane'ler
doğrudan ortak `StateGridRasterizer` ile çizilebilir.

Ana uygulamadaki 3D kartı bu çekirdeği kullanan ayrı bir controller/renderer açar.
Varsayılan 24×32×32 binary volume, Carter Bays'in 26-komşulu B6/S567 kuralıyla başlar;
B5/S45 alternatifi ve altı yüz komşulu deneysel B3/S23 seçeneği sidebar'dan
değiştirilebilir. Canlı hücreler ModernGL ile tek tek draw call yerine instanced cube
olarak, perspektif projection, depth test ve yönlü ışıkla çizilir. Sol sürükleme orbit,
orta sürükleme pan, tekerlek zoom yapar. İmlecin ışını 3D DDA ile volume içinde gezerek
ilk canlı voxel'i bulur; sol tık önündeki boş komşuya ekler, sağ tık seçili voxel'i
siler. Kamera hedefi, açıları, uzaklığı ve görüş alanı tam oturum JSON'unda saklanır.

Pygame sidebar, timeline, analiz ve modal bileşenleri yeniden yazılmamıştır: şeffaf
bir Pygame surface'e çizilip her frame OpenGL sahnesinin üstüne tek texture olarak
bindirilir. 1D/2D'ye dönüldüğünde OpenGL kaynakları bırakılır ve mevcut resizable
yazılım surface'i geri kurulur. SDL dummy sürücüsü gerçek GL context sunmadığı için
otomatik testlerde X/Y/Z slice rasterizer yalnız teknik smoke-test fallback'i olarak
kalır; normal kullanıcı görünümü değildir. Kullanıcı fixed/wrap/reflect sınırlarını
seçebilir, simülasyonu çalıştırabilir ve ortak timeline üzerinden geri/ileri gidebilir.
Varsayılan iki Bays kuralının kaynağı:
[Carter Bays, “A Note About the Discovery of Many New Rules for the Game of
Three-Dimensional Life”](https://doi.org/10.25088/complexsystems.16.4.381).

`life3d.py` önceki deneysel prototip olarak korunur; ana uygulamanın 3D state kaynağı
değildir.

## Timeline ve gelişmiş geçmiş

Viewport ile istatistik çubuğu arasındaki ortak timeline, 1D ve 3D çalışma alanları ile
altı 2D modun tamamında aynı kontrolleri sunar. Tek oklar bir frame geri/ileri gider;
çift oklar kayıtlı geçmişi iki yönde oynatır, orta düğme oynatmayı durdurur. Çubuk
sürüklenerek herhangi bir kronolojik frame'e gidilebilir. Dikey işaretler tam-state
checkpoint'lerini gösterir. `J` veya `Go to gen`, timeline içinde bulunan kesin bir
generation numarasına gider; clear/randomize nedeniyle aynı numara birden çok kez
bulunuyorsa en yeni kayıt seçilir.

Geçmiş motoru her adımda bütün grid'i kopyalamaz. Periyodik checkpoint'ler arasında
yalnızca değişen hücreler; 1D diyagramlarda ise eklenen/kısaltılan satırlar delta
olarak tutulur. Bir checkpoint'e atlamak en yakın önceki checkpoint'ten sınırlı sayıda
delta uygulayarak gerçekleştirilir. 1D/2D için varsayılan üst sınır workspace/mod
başına 2000 frame'dir. 3D timeline, Python hücre nesneleri üretmek yerine C-order
volume byte snapshot'ları kullanır ve bellek kontrolü için son 300 frame'i tutar.
Kullanıcı geçmişteki bir frame'e dönüp düzenleme yaparsa yalnız o
workspace'in ileri dalı atılır; diğer boyut ve 2D mod timeline'ları korunur.

## Bilimsel analiz paneli

Sağ menüdeki `Scientific Analysis` düğmesi veya `I`, simülasyonu durdurmadan çalışan
iki sekmeli analiz panelini açar. `Live Metrics`; population, density, normalize
Shannon entropy ve bir önceki nesle göre değişen hücre yüzdesini dört zaman serisi
olarak gösterir. Aynı tam durum tekrar görüldüğünde periyot ve döngünün başladığı
stabilizasyon generation'ı raporlanır; periyot `1` sabit noktayı ifade eder.

Ölçümler modların gerçek durum uzayına göre normalize edilir. Life hücre yaşları
canlı/ölü, Immigration yaşları boş/Tür A/Tür B olarak ölçülür. Langton's Ant periyot
imzasına karıncanın konumunu, yönünü ve aktifliğini; Cyclic Automaton ise state count
ve threshold'u dahil eder. Böylece görsel yaş sayaçları veya farklı deney parametreleri
yanlış değişim ve periyot sonucu üretmez. Clear, randomize, rule/threshold değişimi ya
da aynı generation'da elle müdahale yeni bir ölçüm koşusu başlatır. Seriler mod ve
workspace başına bağımsız tutulur ve en fazla 2000 örnek saklar. 3D çalışma alanında
population ve density bütün volume, değişim/periyot imzası da tüm voxel dizisi üzerinden
hesaplanır.

`1D Rule Comparison` sekmesi, seçili Elementary rule ile 30, 54, 90, 110 ve 184
referans kurallarını arayüzü dondurmayan bir arka plan işinde karşılaştırır. Her rule
aynı merkezî tek-hücre seed'i, 160 generation ve kenara ulaşılmayan eşit 321 hücrelik
sonsuz-arka-plan penceresini kullanır. Tablo ortalama/final population, ortalama
density, entropy, değişim oranı, periyot ve stabilizasyon generation'ını birlikte
gösterir.

## Dışa aktarma

1D ve 2D sağ menülerindeki `Export Results` düğmesi veya `X`, aktif workspace'i
duraklatıp güncel düzenlemeyi timeline'a işler ve beş bağlamsal çıktı sunar. 3D volume
export henüz etkin değildir; tam volume oturum JSON'u içinde güvenle saklanır.

- `PNG Diagram`: 1D'de tüm space-time diyagramını, 2D'de güncel durum grid'ini
  kayıpsız ve nearest-neighbor ölçeklemeyle yazar.
- `Animated GIF`: Timeline'ın ilk ve son frame'i dahil en fazla 120 eşit aralıklı
  frame'ini döngüsel animasyon olarak üretir.
- `MP4 Video`: Aynı timeline örneklerini 20 FPS H.264 video olarak yazar.
- `Generation Metrics CSV`: Population, density, normalize entropy, değişim oranı,
  algılanan periyot ve stabilizasyon generation'ını UTF-8 CSV olarak verir.
- `Shareable Experiment JSON`: Bütün 1D/2D/3D durumlarını taşıyan yüklenebilir session
  belgesine aktif timeline ve bilimsel ölçüm metadatasını ekler.

Kodlama işlemleri Pygame event thread'i dışında sırayla çalışır; tamamlanma veya hata
durumu alt barda gösterilir. Uzun timeline'larda kontrollü dosya boyutu için animasyon
örneklenir, fakat ilk ve son kayıt daima korunur. 1D satırları genişlik değiştiğinde
merkez hizalıdır; Life ve Immigration yaş sayaçları gerçek hücre durumlarına normalize
edilir ve Langton karıncası frame üzerinde ayrıca işaretlenir.

Dosyalar otomatik, güvenli ve zaman damgalı adlarla `exports/` klasörüne atomik olarak
yazılır. Bu klasör Git tarafından izlenmez. Paylaşılabilir JSON, `sessions/` klasörüne
kopyalandığında mevcut `Browse Saved Sessions` ekranından yüklenebilir.

## Test

```powershell
python -m unittest discover -s tests
```

Test paketi Conway kurallarını, pattern tanıma/depolama davranışını, atomik
pattern yerleştirmeyi; moda özel pattern filtreleme ve çok durumlu pattern
depolamayı; Immigration, Brian's Brain, Langton's Ant, Wireworld ve Cyclic Automaton
kurallarını; 256 elementary CA kuralının kodlama mantığını; boyut/mod registry ve
bağlamsal menü davranışını; workspace registry/controller/renderer sözleşmesini;
checkpoint/delta round-trip, timeline dallanması, ileri/geri gezinme ve sürükleme davranışını;
bilimsel metrikleri, periyot/stabilizasyon algılamayı ve 1D rule karşılaştırmasını;
PNG/GIF/MP4 raster kodlamayı, CSV/JSON güvenliğini ve export menü entegrasyonunu;
oturum/profile güvenliğini ve tam-state round-trip davranışını; 3D volume/rule,
orbit kamera, ray seçimi ve voxel geometri çekirdeğini; üç workspace'in SDL dummy
video driver ile başlangıcını kapsar. Ayrıca gerçek OpenGL smoke testi instanced
renderer'ın bir volume frame'i üretebildiğini doğrulamak için elle çalıştırılabilir.

## Tam oturum kaydetme ve yükleme

Sağ menüdeki `Session & Profiles` düğmesi veya `P`, oturum yöneticisini açar.
`Quick Save` / `Ctrl+S`, mevcut durumu `sessions/last_session.json` dosyasına
kontrollü olarak yazar; `Quick Load` / `Ctrl+O` aynı kurtarma noktasını yükler.
İsimlendirilmiş oturumlar ayrıca kaydedilebilir ve yöneticideki katalogdan seçilebilir.

Bir oturum; aktif dimension ve 2D mode bilgisinin yanında tema, hız, görünüm
seçenekleri, 1D/2D/3D kamera konumları, hücre boyutları, bütün altı 2D modun grid ve
generation değerleri, Life rule'u, moda özel fırçalar, 1D alanının rule family/spec,
boundary, seed, tam diyagram, second-order hafıza ve karşılaştırma durumu ile 3D
volume'un hücreleri, kuralı, sınırı, inceleme dilimi ve orbit kamerasını içerir. Yükleme simülasyonu
güvenli biçimde duraklatır ve her workspace için yüklenen durumu yeni timeline
başlangıç checkpoint'i yapar. Dosya tamamen doğrulanmadan
canlı uygulama state'i değiştirilmez.
Bilimsel zaman serileri türetilmiş veri oldukları için JSON'a eklenmez; yüklenen
workspace durumları her mod için yeni bir analiz başlangıç örneği oluşturur.

1D çalışma alanında oturum yöneticisi ayrıca `Save 1D Experiment Profile` ve
`Browse 1D Experiment Profiles` seçeneklerini gösterir. Bir profil mevcut rule,
family, state count, radius, boundary, background, karşılaştırma rule'u ve güncel
satırı yeniden kullanılabilir seed olarak saklar.
Profil yüklendiğinde deney generation `0` noktasından yeniden başlatılır.

Oturum ve profil dosyaları UTF-8 JSON kullanır, sürüm numarası taşır, güvenli dosya
adlarına dönüştürülür ve geçici dosya üzerinden atomik olarak yazılır. Bozuk JSON,
uyumsuz sürüm, geçersiz hücre durumu veya farklı grid boyutu kontrollü hata üretir;
`sessions/` kullanıcı verisi olduğu için Git tarafından izlenmez.

## Render performansı

Grid viewport'u, ilgili modun hücreleri veya görsel ayarları değişene kadar bellekte
cache'lenir. Pattern önizlemesi, durum mesajları ve menüler cache dışında çizildiği
için etkileşimli kalır. Life geçiş animasyonları devam ederken cache kullanılmaz;
`60 gen/s` çalışan ve her frame değişen simülasyonda gereksiz viewport kopyası
alınmaz. Mod istatistikleri de yalnızca ilgili grid değiştiğinde yeniden hesaplanır.

Büyük 1D space-time diyagramlarının görünür hücreleri NumPy ile tek bir durum
matrisine dönüştürülür, palet topluca uygulanır ve Pygame surfarray üzerinden bir
yüzeye aktarılır. Ölçeklenmiş scratch yüzeyleri yeniden kullanıldığı için hücre
başına `pygame.draw.rect` çağrısı ve frame başına gereksiz yüzey tahsisi yapılmaz.
Toplu yol 4.096 veya daha fazla görünür hücrede otomatik seçilir; küçük veya
yarım-hücre hizalı özel diyagramlarda eski çizim yolu güvenli fallback olarak
korunur. 3D çalışma alanı ise yalnız canlı voxel'ler için kompakt bir instance
buffer günceller ve bütün küpleri tek instanced draw call ile çizer. X/Y/Z slice
rasterizer yalnız OpenGL'siz SDL dummy smoke test yolunda kullanılır.

Tekrarlanabilir ölçüm komutları, profiler kullanımı ve referans önce/sonra sonuçları
[`benchmarks/README.md`](benchmarks/README.md) dosyasındadır.

## Boyut seçimi ve genelleştirilmiş 1D CA

`D` tuşu veya sağ menüdeki `Select Dimension` düğmesi üç üst seviye çalışma alanını
gösterir. `1D`, Wolfram'ın genel 1D cellular automata alanını; `2D`, mevcut altı modu
açar; `3D` ise oynanabilir spatial Life volume'unu açar. Boyutlar arasında geçiş
yapmak gridleri, volume'u ve geçmişleri sıfırlamaz.

Elementary CA, iki hücre durumu ve sol/merkez/sağ üçlüsünden oluşan sekiz olası
komşuluk kullanır. 0–255 kural numarası, `111` ile `000` arasındaki bu komşulukların
sekiz çıktısını kodlar. Örneğin Rule 30, `00011110` ikili çıktısına sahiptir. Bu
numaralandırma [Wolfram Elementary Cellular Automaton açıklaması](https://mathworld.wolfram.com/ElementaryCellularAutomaton.html)
ve [Wolfram Language CellularAutomaton dokümantasyonu](https://reference.wolfram.com/language/ref/CellularAutomaton.html)
ile aynı sırayı kullanır.

Sağ menüdeki `Family` denetimi altı 1D aile arasında geçiş yapar:

- `Elementary`: İki durumlu, radius-1 ve 0–255 Wolfram kuralları.
- `Totalistic`: Komşuluk toplamının çıktıyı seçtiği 2–4 durumlu, radius 1–3 kurallar.
- `Multi-state`: Üç veya dört durumlu tam radius-1 lookup tablosu.
- `Extended Radius`: Beş veya yedi hücrelik binary komşuluklar (radius 2–3).
- `Higher-order`: Sonraki satırın hem güncel hem bir önceki nesle bağlı olduğu kurallar.
- `Reversible`: Önceki satırın iki ardışık satırdan tam geri kazanılabildiği
  second-order kurallar.

Family değişiminde görsel olarak yararlı, deterministik bir başlangıç kuralı seçilir.
Uygun ailelerde `States` ve `Radius` ayrı ayrı değiştirilebilir. Büyük lookup uzaylarının
rule code'ları arayüzde kısaltılarak gösterilir, fakat hesaplama ve JSON içinde tam
tamsayı korunur. Çok durumlu ailelerde `Brush State`, sol tıklamanın yazacağı durumu
seçer; sağ tıklama her zaman `0` yazar.

`Compare`, aynı seed, boundary, hız ve generation akışını paylaşan ikinci bir rule'u
yan yana açar. `Compare −/+` yalnız ikinci rule code'unu değiştirir. Böylece farklı
kuralların space-time diyagramları aynı deney koşullarında gözle karşılaştırılabilir;
karşılaştırma durumu timeline, session, profil ve PNG/GIF/MP4 dışa aktarmalarında da
korunur.

1D alanında üstte sabit bir güncel-satır editörü, altta ise nesillerin aşağı doğru
aktığı space-time diyagramı bulunur. Sol tık seçili durumu, sağ tık sıfırı yazar.
`Browse Rules 0–255` veya `E`, 16×16 rule kataloğunu açar; bir rule tıklanabilir ya da
numarası yazılıp Enter'a basılabilir. `Previous Rule` ve `Next Rule` düğmeleri hedef
numarayı açıkça gösterir; 0 ile 255 arasında sarar. 30, 54, 90, 110 ve 184 ayrıca
featured rule olarak işaretlenir.

Varsayılan `Canonical Reset` davranışı her rule değişiminde MathWorld kataloğundaki
gibi ortada tek aktif hücreye ve sıfır durumundaki sonsuz arka plana döner. Böylece
Rule 4, Rule 30 veya Rule 110 karşılaştırılırken ayrıca seed ve boundary ayarlamak
gerekmez. `Rule Change` düğmesi `Keep Current Row` seçeneğine alınırsa deneysel
karşılaştırmalar için son satır korunur.

`Infinite Background`, görünür alanın dışındaki tekdüze arka planı rule'a göre zamanla
evrimleştirir ve referans katalog için varsayılandır. Aktivite görünür kenara
ulaştığında çalışma alanı iki yana otomatik genişler; uzun koşularda pattern kesilmez.
`Fixed Zero`, görünür alanın dışını her nesilde zorla 0 tutar; `Wrap` ise satırın iki
ucunu komşu yapar. Rule 4 gibi değişmeyen satırlar artık simülasyonu durdurmaz: her
zaman adımı diyagrama eklenir ve referanstaki dikey zaman izi oluşur.

Grid çizgileri gerçek satırın bittiği yerde kesilmez; görünür space-time alanındaki
sanal hücrelerde aynı origin'e hizalı biçimde devam eder. `Infinite Background`
0 dışında bir duruma evrildiğinde bu sanal hücreler de ilgili neslin durum rengiyle
çizilir. `Seed Width`, yeni deneyin
başlangıç satırını `Compact` (121), pencereye göre hesaplanan `Viewport` veya onun
yaklaşık iki katı `Wide` seçeneğiyle kurar. Bu seçim session, timeline ve 1D deney
profillerinde korunur; pencere yeniden boyutlandığında çalışan deney kendiliğinden
değiştirilmez. Geniş başlangıçlar 801 hücreyle sınırlandırılır; saklanan space-time
satır sayısı yaklaşık 64.000 hücrelik bütçeye göre dinamik ayarlanır ve kayan satırlar
timeline'da tek delta olarak tutulur. Otomatik yatay büyüme 4.095 hücrelik güvenlik
sınırına erişirse simülasyon veriyi kırpmak yerine kontrollü biçimde durur.

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

Altı 2D mod ortak, sonlu `72 × 48` (3.456 hücre) tahta kullanır. Bu boyut varsayılan
pencere, timeline belleği ve yüksek generation hızları arasında dengeli tutulur;
eski session'ların grid şekli de değişmez. `Fit Board to Window` veya `Ctrl+0`, mantıksal
hücre sayısını ya da simülasyonu değiştirmeden en büyük tam hücre zoom'unu seçer.
`Center View` ise mevcut zoom'u koruyarak yalnız kamerayı ortalar.

### Arayüz erişilebilirliği ve gezinme

Sidebar kontrolleri `Workspace`, `Mode & Active Tool` / `Rule & Comparison`,
`Experiment` / `Seed & Boundary` ve `View` başlıkları altında toplanır. Başlığa
tıklamak bölümü açar veya kapatır; seçim aynı uygulama çalışması boyunca korunur.
Bir kontrolün üzerinde kısa süre beklemek, işlevi ve etkisini açıklayan tooltip'i
gösterir. `F1` veya `?`, aktif dimension ve moda göre değişen klavye/etkileşim yardım
panelini açar; `Esc`, `F1` veya `?` paneli kapatır.

Üst bilgi çubuğundaki yüksek kontrastlı `RUNNING` / `PAUSED` rozeti yalnız renge
dayanmaz; simge ve metin de kullanır. Rozete tıklamak Space ile aynı run/pause
komutunu çalıştırır. Sağındaki `TOOL` rozeti aktif species, Wireworld state'i,
Cyclic state'i, 1D fırça state'i veya seçili pattern adını sürekli görünür tutar.

Elementary rule kataloğunda sayı yazmak sonuçları anında filtreler; tam sayı ve
`Enter` doğrudan seçer. Bir karta sağ tıklamak rule'u favorilere ekler/çıkarır,
`F` yalnız favorileri gösterir. Favoriler yerel tercih dosyasında saklanır.
`Session & Profiles` giriş ekranı ayrıca en son kullanılan session ve 1D profillerini
tek tıklamayla yeniden açılabilen `Recent` satırları olarak gösterir.

`Colorblind` teması ayrıştırılabilir renkleri yüksek kontrast, metinsel state etiketleri
ve mümkün olan yerlerde şekil işaretleriyle birlikte kullanır. Immigration'da A koyu
mavi, B sarıdır; B hücrelerinde renk dışında bir iç işaret de çizilir. Langton
karıncası yön üçgenini ve durmuşken `X` işaretini korur; Wireworld kuyruğu magenta
çizilir. Ekran ve dışa aktarma paletleri ortak semantik renkleri kullanır. Tema,
diğer temalar gibi sidebar'daki `Theme` düğmesiyle seçilir. `Midnight` düşük ışıkta
rahat koyu bir seçenek, `Paper` ise açık ve baskı benzeri bir arayüz sunar.

## Moda özel patternler

`Show Patterns` yalnızca açık olan simülasyona uygun patternleri gösterir. Menü önce
modun kategori listesini, ardından seçilen kategorinin patternlerini açar. `All
Patterns` bütün aktif katalog için düz listeyi korur; `Backspace`, sol ok veya başlığa
tıklama kategori seviyesine döner. Kullanıcının kaydettiği örnekler otomatik `Custom
Patterns` kategorisinde görünür. Hazır kataloglar mod başına en fazla 20 pattern ile
sınırlıdır.

Life-like kataloğundaki mevcut 20 örnek korunur ve still life, oscillator, spaceship,
methuselah ile gun/puffer başlıklarına ayrılır. Immigration kataloğu; üç sabit form,
üç osilatör, iki spaceship ve iki uzun rekabet seed'i olmak üzere 10 iki-türlü örnek
içerir. Brian's Brain, doğrulanmış period-3/period-4 osilatörleri, genişleyen dalga
seed'ini ve iki wickstretcher'ı gösterir. Langton patternleri siyah/beyaz hücrelere ek
olarak karıncanın göreli konumunu ve yönünü de saklar.

Wireworld kataloğunda 15 doğrulanmış örnek bulunur. Öğretici sinyal, köşe, paralel
bus, collision, splitter ve clock loop örneklerine ek olarak klasik diode, OR, AND,
exclusive-OR, AND-NOT/clocked NOT, set-reset flip-flop ve 68×15 hücrelik bit-serial
binary adder yer alır. CellPyLib'in ileri/ters diyot ve clocked XOR örnekleri de
korunur. Mantık, bellek ve arithmetic devreleri ayrı kategorilerde gösterilir.
Bu patternlerde iletken, elektron başı ve elektron kuyruğu ayrı durumlar olarak
korunur. Pattern döndürme ve çevirme işlemleri çok durumlu hücreleri; Langton modunda
ayrıca karıncanın konum ve yönünü dönüştürür.

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

Varsayılan paletlerde Tür A mavi, Tür B turuncu çizilir; Colorblind temasında koyu
mavi/sarı ve B için ek iç işaret kullanılır. Sol tık aktif türü yerleştirir, sağ tık
hücreyi siler ve `T` aktif türü değiştirir. Randomize iki türü yaklaşık eşit dağıtır.
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
çizilir; Colorblind temasında kuyruk magentadır. Sol tık seçili durumu yerleştirir,
sağ tık hücreyi siler. `T`, iletken,
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
