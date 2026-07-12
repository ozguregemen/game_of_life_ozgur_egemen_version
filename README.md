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
- Hücre yaşı ve yaşa bağlı renkler
- Doğma/ölme geçiş animasyonları
- Aktivite heatmap'i ve ölü hücre izleri
- 50 nesillik geri alma geçmişi
- Hazır ve kullanıcı tarafından kaydedilmiş patternler
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
pattern yerleştirmeyi ve SDL dummy video driver ile uygulama başlangıcını kapsar.
