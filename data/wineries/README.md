# Winnice Łazu, Zaboru i okolic

Stan sprawdzenia źródeł: 30.10.2026. Katalog zawiera 30 punktów winiarskich: winnice i winiarnie, kompleks Winnicy Samorządowej, Lubuskie Centrum Winiarstwa oraz dwie lokalizacje prezentujące historyczne uprawy (Park Winny i skansen w Ochli).

„Okolice” oznaczają promień około 25 km w linii prostej od Łazu (51.94944, 15.68673). Obejmuje to gminę Zabór, wschodnią i centralną Zieloną Górę, Górzykowo, Cigacice, Mozów, Trzebiechów, Niedoradz, Starą Wieś, Świdnicę, Słone i Buchałów. Odległość nie jest długością trasy drogowej.

## Zakres i kompletność

- Ujęto wszystkie 26 punktów z publicznego katalogu Lubuskiego Centrum Winiarstwa mających opublikowane GPS w przyjętym promieniu.
- Katalog gminy Zabór posłużył do kontroli nazw i adresów lokalnych winnic; wszystkie wymienione tam winnice są reprezentowane.
- Dodano Jany, Słone, osobny punkt kompleksu Winnicy Samorządowej oraz parcelę Equus w Zaborze. Equus ma siedzibę poza tym obszarem, ale uprawę w Zaborze potwierdzają sam producent i LCW.
- To opracowanie turystyczne na podstawie publicznych źródeł. Nie jest urzędową ewidencją wszystkich plantatorów ani gwarancją kompletności prywatnych, niepublikowanych upraw. Nie każda uprawa jest stale dostępna do zwiedzania.

Nie utożsamiamy budynku LCW z całym kompleksem nasadzeń ani siedziby producenta z każdą jego parcelą. Przy Jany oznaczono winiarnię pod oficjalnym adresem Jany 14; opis informuje o uprawie w Łazie. Przy Trojan, Kruczej i Senatorze wyjaśniono rozdzielenie punktu od drugiej lokalizacji.

## Dokładność punktów

GPS 26 wpisów pochodzi z katalogu LCW, a punkt kompleksu z przewodnika LCW. Mogą to być lokalizacje obiektu, siedziby lub opublikowanego punktu uprawy, niekoniecznie brama wejściowa.

Jany: centroid budynku adresowego w OpenStreetMap, zestawiony z adresem na oficjalnym portalu turystycznym Zielonej Góry.

Słone: nie znaleziono potwierdzonego punktu wejścia przy ul. Słonecznej 69. Znacznik wskazuje orientacyjnie ulicę z OSM, co jest jawnie opisane w aplikacji. Link Google Maps wyszukuje pełny adres zamiast prowadzić do centroidu ulicy.

Equus w Zaborze: nie potwierdzono dokładnej pozycji parceli. Użyto opublikowanego punktu orientacyjnego przy LCW, gdzie według LCW można organizować spotkania grup. Punkt nie wskazuje granic uprawy ani odległej winiarni w Mierzęcinie. Oba ograniczenia są widoczne w podglądzie.

Dwa rekordy OSM: © OpenStreetMap contributors, [ODbL 1.0](https://www.openstreetmap.org/copyright). Linki do konkretnych obiektów i dokładność są zapisane przy punktach.

## Opisy, fotografie i aktualizacja

Opisy napisano samodzielnie na podstawie informacji źródłowych. Każdy wpis ma indywidualne linki. Nie publikujemy niepotwierdzonych godzin otwarcia, cen ani zapewnień o dostępności.

Zdjęcie LCW pochodzi z Wikimedia Commons; autor i licencja CC BY-SA 4.0 są zachowane w metadanych i podglądzie. Pozostałe wpisy mają wyraźnie podpisaną ilustrację zastępczą. Fotografii ze stron producentów nie skopiowano bez potwierdzonej licencji do ponownego użycia.

Opracowanym zbiorem jest `source-records.json`. Identyfikatory 900001–900030 są stałe i nie zależą od sortowania. Nie zmieniaj ich przy aktualizacji — wiążą komentarze, głosy i plany użytkowników.

```powershell
npm.cmd run catalog:build
npm.cmd test
```

Generator buduje katalog dla Vue, wspólny seed PostgreSQL oraz `/wineries-credits.html`. Synchronizacja przy starcie API dodaje nowe punkty bez usuwania zapisanych wcześniej aktywności użytkowników.

Główne źródła: [katalog LCW](https://centrumwiniarstwa.pl/winnice), [gmina Zabór](https://turystyka.gminazabor.pl/winnice/), [Visit Zielona Góra — Jany](https://visitzielonagora.pl/sekcja/winnica-jany/), [Słone — kontakt](https://winnicaslone.pl/kontakt/), [Equus — parcele](https://www.winnicaequus.pl/filozofia).
