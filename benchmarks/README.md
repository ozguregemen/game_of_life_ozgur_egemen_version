# Render benchmark

`render_benchmark.py`, bütün modları aynı pencere ve grid boyutunda, sabit random
seed'lerle ölçer. Süre yalnızca CPU tarafındaki `draw_scene()` çağrısını kapsar;
`pygame.display.flip()` ve gerçek ekran sürücüsünün maliyeti dahil değildir.

Normal cache reuse ölçümü:

```powershell
python benchmarks/render_benchmark.py --frames 240 --warmup 30
```

Her frame grid değişiyormuş gibi zorunlu rebuild ölçümü:

```powershell
python benchmarks/render_benchmark.py --frames 240 --warmup 30 `
  --invalidate-each-frame --simulate-running
```

Bir senaryonun profiler çıktısı:

```powershell
python benchmarks/render_benchmark.py --frames 160 --profile life_heatmap
```

## Referans sonuç

Aşağıdaki değerler Windows, Python 3.14.0, pygame-ce 2.5.7, SDL dummy video
driver, `1200x720` pencere ve `72x48` grid ile alınan median sürelerdir. Sonuçlar
makineye göre değişir; performans testi için sabit geçme/kalma eşiği değildir.

| Senaryo | Önce | Cache reuse | Azalma |
|---|---:|---:|---:|
| Life dense | 6.44 ms | 0.96 ms | %85.1 |
| Life heatmap/trail | 11.99 ms | 0.93 ms | %92.3 |
| Immigration | 5.98 ms | 0.94 ms | %84.2 |
| Brian's Brain | 4.52 ms | 0.92 ms | %79.6 |
| Langton's Ant | 5.27 ms | 0.94 ms | %82.2 |
| Wireworld | 5.21 ms | 1.00 ms | %80.8 |
| Cyclic Automaton | 5.95 ms | 0.95 ms | %84.0 |

Cache, grid nesiller arasında değişmediğinde aktif viewport piksellerini tekrar
kullanır ve bellekte aynı anda yalnızca bir viewport yüzeyi tutar.
Pattern önizlemesi ve diğer hareketli arayüz katmanları her frame çizilmeye devam
eder. Life doğum/ölüm geçişleri cache'i geçici olarak bypass eder. Aktif simülasyon
`60 gen/s` hızındaysa her frame değişeceği için viewport kopyası alınmaz; ölçülen
zorunlu rebuild medianleri önceki render yoluna yakın kalır.
