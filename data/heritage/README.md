# Katalog zamków i pałaców województwa lubuskiego

Stan źródeł: 30 października 2026. 175 odrębnych obiektów: 24 zamki i 151 pałaców, w tym ruiny, wieże mieszkalne oraz udokumentowane pozostałości. Po połączeniu z dotychczasowymi miejscami aplikacja zawiera 180 punktów.

To katalog rozpoznanych obiektów, **nie potwierdzony kompletny rejestr wszystkich zabytków**. Nie obejmuje automatycznie wszystkich dworów. Regionalna liczba około 250 rezydencji dotyczy szerszego zakresu: zamków, pałaców i dworów. Nie należy utożsamiać jej z liczbą zamków i pałaców.

## Źródła i opracowanie

- Wikidata (CC0): obiekty typu zamek / pałac i podtypy, w województwie lubuskim według hierarchii administracyjnej, także rekordy bez współrzędnych.
- Kategorie Wikimedia Commons „Castles in Lubusz Voivodeship” i „Palaces in Lubusz Voivodeship”: uzupełnienie nazw, identyfikatorów i fotografii.
- Polskojęzyczna Wikipedia: krótkie fragmenty wstępów z podaniem artykułu źródłowego oraz licencji CC BY-SA 4.0; historia artykułu wskazuje autorów.
- [Regionalny portal turystyczny](https://lubuskie.pl/cms/57/zamki_palace_i_dwory) oraz [wykaz NID z 9 lipca 2025](https://nid.pl/wp-content/uploads/2025/07/LBS-rej_9.07.2025.pdf): kontrola zakresu i wybranych wpisów. Nie wykonano pełnej ręcznej inwentaryzacji każdej pozycji wykazu NID.

Scalono duplikaty budynku i zespołu oraz alternatywne wpisy dotyczące tego samego obiektu. Osobne budowle pozostają osobnymi punktami, także gdy stoją obok siebie. Usunięto parki, bramy i zabudowania pomocnicze błędnie klasyfikowane jako pałace. Szczegółowy zakres, wyłączenia i nierozstrzygnięte rekordy zawiera `coverage.json`.

Nie dodano zgadywanych współrzędnych zamku w Buchałowie ani niezlokalizowanych pozostałości zespołu w Mycielinie. Współrzędne pochodzą z przypisanych rekordów źródłowych; ich dokładność jest różna. Punkt nie gwarantuje wejścia do obiektu ani dostępności dla zwiedzających.

## Zdjęcia i licencje

123 obiekty mają przypisaną fotografię z potwierdzoną licencją Commons, zapisaną lokalnie w projekcie; dla pozostałych 52 aplikacja pokazuje podpisaną ilustrację zastępczą. Fotografie archiwalne mają osobne oznaczenie. Nie zastępujemy brakującej fotografii zdjęciem innego zabytku.

Autor, licencja, strona pliku i informacja o przekształceniu są w `source-records.json`, podglądzie miejsca i na `/heritage-credits.html`. Kopie WebP mają maksymalnie 1200 px szerokości, zachowane proporcje i nie są kadrowane w pliku. Interfejs wyświetla miniatury. Jeśli pobranie nie powiedzie się, używany jest oryginalny adres Commons z lokalnym obrazem zastępczym na wypadek błędu ładowania.

## Aktualizacja lokalna

`source-records.json` jest opracowanym zbiorem źródłowym. Nie nadpisuj go automatycznym wyszukiwaniem bez kontroli duplikatów, współrzędnych i przypisania fotografii.

```powershell
node scripts/download-heritage-photos.mjs
npm.cmd run catalog:build
npm.cmd test
```

Pobieranie jest sekwencyjne; odpowiedź HTTP 429 kończy pobieranie. Ponowienie wykorzystuje już zapisane pliki. Generator tworzy `src/catalog/heritage.json`, `backend/seed.json` i stronę atrybucji. Identyfikatory nowych miejsc wynikają z identyfikatorów Wikidata; Łagów zachowuje dotychczasowe ID 1. Zmiana głównego identyfikatora źródłowego wymaga jawnej migracji, aby zachować relacje użytkowników.

API przy starcie dodaje kolumnę metadanych i rozszerza pole adresu zdjęcia. Następnie aktualizuje katalog po ID, bez usuwania kont, komentarzy, wizyt ani planów. Dane spoza importowanych ID pozostają w bazie. Źródłowe pola importowanych miejsc są aktualizowane przy starcie — własne zmiany należy wprowadzać do zbioru źródłowego. Migracja oraz synchronizacja działają na PostgreSQL.

Zmiany przygotowano lokalnie; publikacja i wdrożenie wymagają osobnego polecenia użytkownika.
