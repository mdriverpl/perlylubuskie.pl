# Łagów — noclegi i gastronomia

Snapshot źródeł z 30.10.2026. Zakres: miejscowość Łagów w województwie lubuskim, bez pozostałych miejscowości gminy.

`source-records.json` zawiera 133 nowe miejsca i uzupełnienie istniejącego zamku (ID 1). Identyfikatory są trwałe; nie należy ich numerować od nowa przy aktualizacjach, ponieważ wiążą się z trasami i aktywnością użytkowników.

`coverage.json` przypisuje wszystkie 108 wierszy sekcji Łagów [wykazu powiatu](https://samorzad.gov.pl/web/powiat-swiebodzinski/gmina-lagow-pozostale-obiekty-hotelowe) do miejsc. Połączono dwa powtórzenia: Forte Studio i W Lawendach. Pozostałe źródła: [rejestr hoteli](https://samorzad.gov.pl/web/powiat-swiebodzinski/hotele), strony obiektów i OpenStreetMap. Podwójne punkty OSM tej samej gastronomii połączono; różne apartamenty pod jednym numerem budynku pozostają odrębne.

115 miejsc oferuje noclegi, 24 gastronomię; pięć oferuje obie usługi. Kategoria główna pozostaje jedna, dodatkowe role w `details.categories` umożliwiają oba filtry bez duplikowania miejsc. Liczby obejmują istniejący zamek.

21 lokalizacji określono tylko do ulicy (`coordinate_accuracy: street`); interfejs oznacza je jako przybliżone, a Google Maps wyszukuje adres zamiast kierować do punktu ulicy. Inne punkty odpowiadają obiektowi lub adresowi budynku, niekoniecznie wejściu. Nie potwierdzano rezerwacji, godzin, cen ani dostępności. Rejestr nie gwarantuje aktualnej działalności każdej firmy. Brak fotografii oznaczono ilustracją zastępczą.

Generowanie: `npm run catalog:build` kopiuje katalog do frontendu, przygotowuje źródła w `/hospitality-credits.html` i aktualizuje seed backendu. Dane mapowe © OpenStreetMap contributors, ODbL 1.0; opisy autorskie.
