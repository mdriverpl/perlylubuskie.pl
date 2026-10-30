# Perły Ziemi Lubuskiej

Projekt aplikacji turystycznej na podstawie dwóch dostarczonych wizualizacji. Vue 3 + Vite, Python / FastAPI, PostgreSQL 17, SQLAlchemy 2, Leaflet / OpenStreetMap. Interfejs po polsku, układ dostosowany do komputera i telefonu.

**Gotowe obrazy Docker i wdrożenie:** [DEPLOYMENT.md](DEPLOYMENT.md). Domyślny `compose.yaml` oraz `compose.deploy.yaml` pobierają frontend i API z GitHub Container Registry i uruchamiają PostgreSQL z trwałym wolumenem. Hostava używa `compose.hostava.yaml` i portu hosta dla proxy: **8080**, mapowanego na port 80 Nginxa w kontenerze. Lokalny build ze źródeł jest w `compose.build.yaml`.

## Funkcje

- Górne menu: „Start”, „Miejsca”, „Planer”, „Wycieczki piesze” i „Wycieczki rowerowe”, z jednokolorowymi ikonami. „Planer” otwiera mapę i planowaną listę; dwie ostatnie pozycje pokazują osobne listy zapisanych tras danego typu. Widać trasy użytkownika z konta oraz zapisane lokalnie na urządzeniu. Wybranie pozycji otwiera planer; pusty widok zawiera przycisk powrotu do miejsc.
- Katalog 175 zamków i pałaców województwa lubuskiego (24 zamki, 151 pałaców), z opisami, współrzędnymi, źródłami i licencjami fotografii; osobne checkboxy „Zamki” i „Pałace”. Zakres i braki: [dokumentacja katalogu](data/heritage/README.md). Nie jest to potwierdzony kompletny rejestr zabytków.
- Filtr „Winnice”: 30 punktów winiarskich w Łazie, Zaborze i okolicy do około 25 km, z opisami, adresami i źródłami. Rozróżniono uprawy, winiarnie, centra i obiekty historyczne; orientacyjne punkty Słonego i parceli Equus są oznaczone wprost. [Zakres i źródła winnic](data/wineries/README.md). Cały katalog aplikacji: 210 miejsc.
- W listach pieszych i rowerowych filtr „Moje wycieczki” ogranicza wyniki do własnych planów i pokazuje „Edytuj”. Planer pozwala zmienić punkty, kolejność i rodzaj, a okno zapisu nazwę i opis. Zapis aktualizuje istniejący rekord, również lokalny, bez tworzenia kopii. Serwer sprawdza właściciela przy każdej aktualizacji. Na listach są też publiczne trasy innych autorów; filtr „Moje wycieczki” ukrywa je.
- Otwarcie własnej zapisanej trasy pozwala przeciągać jej znaczniki na mapie. Pozycje są zapisywane w wycieczce, bez zmieniania katalogu miejsc; trasowanie i GPX uwzględniają przesunięcia. Przycisk „Zapisz trasę” aktualizuje otwarty plan, również bez wejścia przez „Edytuj”. Kolejność punktów można zmieniać strzałkami przy liście.
- Przy zapisie trasy tworzona jest okładka WebP (960 × 600) z mapą całego przebiegu, numerami punktów i oznaczeniem dostawców mapy. Okładka jest pierwszym zdjęciem na listach i stronie Start. Zapis zmian odświeża obraz; stare trasy otrzymają go po ponownym zapisie. Dla kont obraz zapisuje się w bazie, dla planów lokalnych w przeglądarce. Błąd pobierania mapy przerywa zapis z komunikatem, bez utraty szkicu.
- Strona odkrywania regionu: wyszukiwanie, kategorie, katalog miejsc, szczegóły, inspiracje wycieczek.
- „Start” zawiera „Miejsca TOP 20” według sumy polubień i komentarzy (bez własnych prywatnych punktów), podglądy do trzech zapisanych tras pieszych i rowerowych z linkami do pełnych list oraz sekcję „Wycieczki” z dotychczasowymi inspiracjami. Trasy są pokazywane dla bieżącego konta i urządzenia; puste sekcje zachęcają do utworzenia planu.
- Widok główny „Szukaj miejsc” otwiera mapę terenową HERE. Nad mapą nagłówek „Czego szukam?”, sortowanie i ikony widoku: lista, kafelki, mapa; poniżej poziomy wiersz checkboxów kategorii. Wybór kilku kategorii łączy wyniki, a filtry działają we wszystkich widokach. Dotychczasowa strona pozostaje pod „Start”.
- Sortowanie „Odległość — najbliższe” i promień 5–100 km działają wyłącznie od miejscowości wskazanej przez „Znajdź na mapie”. GPS nie służy do filtrowania ani sortowania katalogu. Odległości są liczone w linii prostej. Wpisanie nazwy miejscowości z katalogu automatycznie ustawia mapę na tę miejscowość (zoom 13); wyszukiwanie jest zapamiętywane w przeglądarce osobno dla Miejsc i Planera.
- Sortowanie „Blisko siebie” grupuje sąsiednie miejsca według współrzędnych, z początkiem przy wyszukanej miejscowości albo stałym początkiem geograficznym. GPS nie wpływa na kolejność. Dostępne są również popularność, polubienia, komentarze i nazwa.
- Pole wyboru regionu jest ukryte; katalog i wyszukiwanie lokalizacji obejmują obecnie Lubuskie. Wyszukiwarka i filtry mają stały układ poziomy nad mapą; przełącznik układu menu został usunięty. Kliknięcie znacznika atrakcji otwiera pełny podgląd miejsca.
- „Pokaż, gdzie jestem” korzysta z geolokalizacji przeglądarki dopiero po kliknięciu i zgodzie użytkownika. Pozycja jest pokazywana na mapie z przybliżoną dokładnością i pozostaje tylko w pamięci bieżącego widoku; aplikacja nie zapisuje jej w bazie. Odmowa lub brak obsługi lokalizacji nie blokuje mapy i filtrów.
- Planer: interaktywna mapa, wybór punktów, zmiana kolejności oraz rzeczywiste trasy piesze i rowerowe po danych OpenStreetMap, wyznaczane przez własny BRouter.
- W „Miejscach” przycisk „Dodaj do listy” zbiera punkty bez automatycznego przejścia do tras. Prawy panel „Zaplanowane miejsca” pokazuje kolejność, podgląd, usuwanie i czyszczenie; na telefonie znajduje się pod wynikami. Lista jest wspólna z planerem i zapisywana lokalnie. Przycisk „Dodaj trasę” otwiera formularz nazwy, opisu i rodzaju (piesza/rowerowa). Po zapisaniu otwiera się odpowiednia lista zapisanych tras pieszych albo rowerowych z opisem i typem; wybranie trasy uruchamia planer z jej punktami. Opisy są zapisywane także w PostgreSQL, a istniejące trasy otrzymują pusty opis podczas bezpiecznej migracji dodającej kolumnę.
- W „Miejscach” dwukrotne kliknięcie pustego obszaru mapy otwiera dialog punktu pomocniczego trasy. Punkt należy wyłącznie do bieżącego planu i jest zapisywany jako część konkretnej wycieczki (`custom_points`); nie trafia do katalogu miejsc, wyszukiwarki, rankingu ani ulubionych. Ma podgląd punktu trasy, bez karty miejsca i funkcji społecznościowych. Usunięcie z bieżącego planu nie zmienia innych zapisanych tras. Wcześniejsze lokalne punkty są zachowane przy odczycie starych wycieczek. Działają w trasowaniu i GPX, a prywatne plany zawierające takie punkty są zapisywane lokalnie także po zalogowaniu; publiczne są przechowywane na koncie razem z punktami. Dodawanie miejsc do katalogu jest oddzielną czynnością.
- Mapy HERE Raster Tile API v3: widoki „Mapa”, „Satelita” i „Teren” w wyszukiwarce i planerze. Backend pobiera kafelki oraz oznaczenia dostawców danych; klucz nie trafia do frontendu. Brak klucza lub błąd HERE pozostawia mapę OpenStreetMap. Wyznaczanie tras nadal obsługuje BRouter.
- Wyszukiwanie w katalogu filtruje atrakcje po nazwie i miejscowości. Przycisk „Znajdź na mapie” lub Enter dodatkowo wyszukuje lokalizację przez HERE Geocoding & Search, także poza katalogiem (np. Łaz w gminie Zabór). Wyniki są ograniczone do województwa lubuskiego; lokalizacja ma osobny znacznik i nie staje się automatycznie atrakcją. Zapytanie do HERE jest wysyłane dopiero po zatwierdzeniu. Klucz musi mieć dostęp również do Geocoding & Search API v7.
- Dystans po trasie, orientacyjny czas bez postojów i GPX ze śladem oraz punktami. Tryb samochodowy pozostaje planem punktów.
- Lokalne ulubione i plany bez zakładania konta.
- Rejestracja i logowanie: Argon2, JWT z terminem ważności; ulubione oraz zapisane plany przypisane do użytkownika w PostgreSQL.
- Podgląd miejsca: link do Google Maps według współrzędnych, publiczne komentarze z autorem i datą oraz licznik kont, które oznaczyły „Byłem tu”.
- Publiczne polubienia (kciuk w górę) są osobne od prywatnych ulubionych (serce). Jedno zalogowane konto ma jeden głos na miejsce; ponowne kliknięcie cofa głos. Liczniki polubień i komentarzy są widoczne na kartach oraz w podglądzie. Sortowanie „Popularność” to suma polubień i komentarzy; dostępne są także sortowania według samych polubień, komentarzy i nazwy. Liczniki oraz kolejność aktualizują się po zmianach w bieżącej sesji. Głosy są zapisywane w PostgreSQL, a start API dodaje tabelę `place_likes` bez zmieniania istniejących ulubionych i komentarzy.
- Po zalogowaniu: dodawanie i usuwanie własnych komentarzy, oznaczanie i cofanie wizyty. Jedno konto jest liczone przy miejscu tylko raz, także przy równoczesnych żądaniach. Komentarze mają do 2000 znaków i są stronicowane; limit dodawania to 5 na minutę na konto.
- Backend niedostępny: jawnie oznaczony tryb demonstracyjny z katalogiem i zapisem w przeglądarce. Logowanie pozostaje wyłączone.

## Uruchomienie całego projektu

Opcjonalnie ustaw `HERE_API_KEY` w lokalnym `.env`. Wszystkie pliki Compose przekazują go do API w czasie uruchomienia, więc nie trzeba wbudowywać klucza w obraz. Bez Dockera ustaw tę zmienną w środowisku procesu Python przed uruchomieniem Uvicorna. Po zmianie klucza uruchom ponownie API. `.env` pozostaje poza repozytorium; `.env.example` zawiera wyłącznie pusty wzór. Dokumentacja integracji: [HERE Raster Tile API v3 / Leaflet](https://docs.here.com/map-rendering/docs/example-leaflet).

Wymagany Docker z Docker Compose. W katalogu projektu:

```powershell
Copy-Item .env.example .env
```

Ustaw własne `POSTGRES_PASSWORD` i `SECRET_KEY` w `.env`. Hasło bazy powinno składać się z liter i cyfr, ponieważ trafia do adresu połączenia. Sekret JWT powinien być losowy i mieć przynajmniej 32 znaki; można go wygenerować poleceniem:

```powershell
node -e "console.log(require('crypto').randomBytes(48).toString('hex'))"
docker compose pull
docker compose up -d --wait
```

- Aplikacja: **http://localhost:8080**
- Dokumentacja API: **http://localhost:8000/docs** w trybie developerskim opisanym poniżej. Compose nie wystawia dokumentacji przez Nginx.
- Stan backendu przez frontend: **http://localhost:8080/api/health**

PostgreSQL przechowuje dane w wolumenie `postgres_data`. API tworzy tabele i dodaje sześć przykładowych miejsc przy pierwszym starcie. Baza i API nie mają portów wystawionych poza sieć Compose. Frontend jest dostępny wyłącznie lokalnie. Zatrzymanie bez usuwania danych:

```powershell
docker compose down
```

Domyślne wdrożenie wystawia frontend na porcie 8080. Ustaw `APP_BIND=127.0.0.1` w `.env`, aby ograniczyć dostęp do komputera lokalnego. Budowanie ze źródeł wymaga całego repozytorium, w tym katalogu `backend`:

```powershell
docker compose -f compose.build.yaml up --build -d
```

## Praca nad frontendem

Wymagany Node.js 22.12+ lub 24.

```powershell
npm.cmd ci --cache .npm-cache
npm.cmd run dev
```

Otwórz adres wypisany przez Vite, zwykle **http://127.0.0.1:5173**. Bez backendu działa tryb demonstracyjny. Vite przekazuje `/api` do `127.0.0.1:8000`.

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run preview
```

`npm test` sprawdza komponent aplikacji w jsdom: katalog, ulubione, wyszukiwanie i pusty wynik, kolejność punktów, zapis i odtworzenie planu, niedostępność eksportu pustego planu i zamykanie okna klawiszem Escape. Nie zastępuje weryfikacji wyglądu i mapy w przeglądarce.

## Backend developerski

Wymagany Python 3.12+ oraz działający PostgreSQL z oddzielną bazą aplikacji.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
$env:DATABASE_URL='postgresql+psycopg://perly:HASLO@localhost:5432/perly'
$env:SECRET_KEY='TUTAJ_WSTAW_LOSOWY_SEKRET_MINIMUM_32_ZNAKI'
.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload
```

API: **http://127.0.0.1:8000**, Swagger: **http://127.0.0.1:8000/docs**. Przykład adresu bazy wymaga wcześniejszego utworzenia roli `perly` i bazy `perly`.

### Testy backendu na PostgreSQL

Utwórz **osobną bazę testową**. Testy dodają do niej przykładowe konta i rekordy. Nie wskazuj bazy produkcyjnej.

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://perly:HASLO@localhost:5432/perly_test'
.venv/Scripts/python.exe -m pytest backend/tests -q
```

Testy sprawdzają katalog, filtrowanie, Argon2 i logowanie, odrzucanie tokenów, prywatność i idempotentność ulubionych, izolację planów między kontami, kolejność GPX, znaki specjalne oraz niepoprawne dane. W tej sesji wykonano je na PostgreSQL 17: **9 testów zaliczonych**.

## Struktura

```text
src/App.vue                   interfejs, konto i interakcje
src/components/TravelMap.vue   mapa Leaflet
src/data.js                   katalog demonstracyjny i inspiracje
src/style.css                 responsywna szata graficzna
public/images/                lokalne fotografie z referencji
backend/app/main.py           API, modele, uwierzytelnianie, eksport
backend/seed.json             początkowy katalog PostgreSQL
backend/tests/test_api.py      testy integracyjne
scripts/test-ui.mjs            testy komponentu Vue
compose.yaml                  PostgreSQL + FastAPI + Nginx/Vue
```

## API

| Metoda | Endpoint | Funkcja |
| --- | --- | --- |
| GET | `/api/health` | połączenie z bazą |
| GET | `/api/places?q=&category=` | publiczny katalog |
| GET | `/api/places/{id}/community?offset=0&limit=20` | publiczne komentarze i licznik; po zalogowaniu również własne oznaczenie i uprawnienie usunięcia komentarza |
| PUT / DELETE | `/api/places/{id}/visit` | oznaczenie / cofnięcie „Byłem tu”, wymagane konto |
| POST | `/api/places/{id}/comments` | dodanie komentarza `{ "body": "treść" }`, wymagane konto |
| DELETE | `/api/places/{id}/comments/{comment_id}` | usunięcie wyłącznie własnego komentarza |
| POST | `/api/auth/register` | konto i token |
| POST | `/api/auth/login` | logowanie |
| GET | `/api/favorites` | własne ulubione |
| PUT / DELETE | `/api/favorites/{place_id}` | dodanie / usunięcie |
| GET / POST | `/api/routes` | własne plany / zapis |
| DELETE | `/api/routes/{trip_id}` | usunięcie własnego planu |
| GET | `/api/routes/{trip_id}/gpx` | GPX własnego planu |

Prywatne endpointy wymagają `Authorization: Bearer TOKEN`. Token jest ważny 12 godzin. W tej wersji przeglądarka zapisuje go w localStorage; wylogowanie usuwa go z urządzenia.

## Zakres i materiały

Fotografie zostały wyodrębnione z dostarczonej wizualizacji strony głównej. Nie są kompletnym bankiem autentycznych zdjęć atrakcji. Przed publiczną premierą zastąp je zdjęciami w odpowiedniej rozdzielczości i z potwierdzonymi prawami. Logo jest wektorową interpretacją wzoru. Fonty są ładowane z Google Fonts, a mapa korzysta z publicznych kafelków OpenStreetMap — wymagają internetu.

Opisy i parametry popularnych tras to dane demonstracyjne. „Smaki nad jeziorem” jest inspiracją kulinarną, nie prawdziwą ofertą restauracji. Noclegi mają uczciwy pusty stan — projekt nie zawiera fikcyjnych rezerwacji.

Planer pieszy i rowerowy korzysta z własnego kontenera BRouter (`trekking` dla roweru, `hiking-mountain` dla pieszych), bez płatnych kluczy i publicznego serwera demonstracyjnego. Wybierz co najmniej dwa miejsca. Zmiana kolejności lub profilu przelicza trasę; mapa pokazuje przebieg, a eksport GPX zawiera `trk` / `trkpt`. Bez połączenia z silnikiem aplikacja pokazuje błąd i umożliwia wyraźnie oznaczony eksport samych punktów. Tryb samochodowy nie wyznacza przebiegu.

Obraz `perlylubuskie-router` zawiera segmenty BRouter `E10_N50` i `E15_N50` z danymi zachodniej Polski. API ogranicza punkty do obszaru 14–17°E, 50,5–53,5°N, do 20 punktów i dwóch równoczesnych obliczeń. Trasy są buforowane w pamięci przez godzinę. Dane są snapshotem z budowania obrazu, a nie mapą aktualizowaną w czasie rzeczywistym. BRouter używa do 512 MB sterty JVM; kontener ma limit 768 MB. Sam backend developerski wymaga dodatkowo silnika pod adresem `ROUTER_URL` (domyślnie `http://router:17777/brouter` w Compose).

Przed produkcją należy dodać migracje Alembic zamiast samego `create_all`, limity prób logowania, odzyskiwanie hasła, weryfikację e-maili, HTTPS, kopie zapasowe i docelową politykę sesji. Docker Compose przygotowano do uruchomienia, ale nie został wykonany w tej sesji z powodu braku Dockera. Zweryfikowano kompilację Vue oraz testy komponentu i API; automatyczna kontrola wizualna przeglądarki była niedostępna.

Hosting Sites nie uruchamia zestawu Python + PostgreSQL; pełny projekt przeznaczony jest na serwer z Dockerem. Sam frontend może zostać opublikowany jako demonstracja statyczna.

Osobna zakładka „Miejsca” udostępnia katalog bez panelu trasy i własnych punktów. Ma wspólny z planerem zestaw filtrów, sortowanie, widoki lista/kafelki/mapa oraz istniejące polubienia i komentarze w szczegółach. „Dodaj miejsce” wymaga konta i zapisuje nowy rekord w PostgreSQL przez `POST /api/places`: nazwa, opis, rodzaj, miejscowość, współrzędne i opcjonalne zdjęcie HTTPS. Nowe miejsca są dostępne w katalogu i planerze. Dodanie miejsca nie dodaje punktu do bieżącej trasy.

Przy dodawaniu trasy domyślną nazwą jest nazwa pierwszego miejsca na liście (do 120 znaków), a opis jest opcjonalny. Nazwę można zmienić. Wybór widoczności domyślnie wskazuje „Prywatna”. „Publiczna” wymaga zalogowania i udostępnia trasę przez `GET /api/routes/public`; domyślnie prywatne są również istniejące trasy po migracji. Zmiana widoczności na prywatną usuwa trasę z publicznej listy. Tylko właściciel może edytować i usuwać zapis.

PWA: manifest, ikony 192/512 i maskable, ikona instalacji w nagłówku, obsługa instalacji przez menu udostępniania na iOS oraz aktualizacji aplikacji. Service worker powstaje tylko podczas `npm run build`; lokalny podgląd produkcyjny uruchamia `npm run preview -- --port 4173`. PWA i GPS na domenie wymagają HTTPS (localhost działa lokalnie). Po pierwszym otwarciu online aplikacja uruchamia się offline z wbudowanym katalogiem i lokalnymi planami. Zdjęcia oglądanych miejsc są ograniczone do 80 pozycji; prywatne API, tokeny, trasy serwera i kafelki map nie są buforowane przez service worker. Mapy, trasowanie i zapis okładki wymagają internetu.

Katalog nie pobiera GPS automatycznie. Przycisk „Pokaż, gdzie jestem” na mapie pobiera pozycję wyłącznie na żądanie i rysuje znacznik. Nie zmienia wyników, sortowania, promienia ani zbliżenia na wyszukaną miejscowość. Błąd i odmowa GPS nie blokują katalogu. Pozycja nie jest zapisywana w bazie ani wysyłana do API.

AI na stronie Start: przycisk „Zaplanuj z AI”, polecenie i przykłady, podgląd propozycji oraz „Otwórz w planerze”. Klucz `OPENAI_API_KEY` i model `OPENAI_MODEL` (domyślnie `gpt-6-astra`) są wyłącznie zmiennymi backendu; Compose przekazuje je do API. `/api/ai/config` ujawnia tylko gotowość konfiguracji. `POST /api/ai/plan` interpretuje polecenie przez OpenAI Responses API i Structured Outputs (`store: false`), następnie sprawdza identyfikatory miejsc i wyznacza geometrię/czas/dystans przez BRouter. Do OpenAI trafiają tekst polecenia i dane publicznego katalogu; pozycja GPS, token użytkownika oraz jego prywatne plany nie są dołączane. Limit: 6 prób na godzinę na adres klienta, 60 na dobę na proces API i 2 równoległe zapytania.

Przykład „Spacer dookoła Jeziora Łagowskiego” korzysta z zestawu punktów ścieżek z OpenStreetMap (`backend/app/data/lagowskie-circuit.json`, ODbL 1.0), sprawdzonego przez BRouter. Punkty są pomocniczymi punktami konkretnej trasy, nie nowymi miejscami. Dane pobrano z OSM API 2026-10-30 (obiekt jeziora: https://www.openstreetmap.org/way/240361582). Przebieg zależy od bieżących danych silnika i wybranego profilu. Pozostałe polecenia wybierają istniejące miejsca; przy braku danych AI prosi o doprecyzowanie. Propozycja nie jest zapisywana ani upubliczniana automatycznie.

Dokumentacja integracji: https://developers.openai.com/api/docs/guides/structured-outputs oraz https://developers.openai.com/api/docs/models/gpt-6-astra .

Pętle jezior: Ciecz i Trześniowskie są aliasami tego samego akwenu. Żądanie obejścia jeziora jest rozpoznawane przed wyborem atrakcji i nie może zostać zastąpione odległymi miejscami z katalogu. Obsługiwane obwody: Łagowskie i Ciecz/Trześniowskie (`backend/app/data/*-circuit.json`). Wynik BRouter jest sprawdzany pod kątem zamknięcia, obszaru, maksymalnego dystansu i otoczenia trzech punktów wewnątrz jeziora. Nieznane/niejednoznaczne jezioro oraz nieprawidłowy przebieg kończą się komunikatem bez zastępczej trasy.

Dane Ciecza: OSM relation 12256921, pobranie 2026-10-30, ODbL 1.0. Podgląd pokazuje ograniczenia północnego brzegu przy poligonie w Wędrzynie i link do informacji Gminy Sulęcin; informacja przechodzi także do opisu zapisywanej trasy. Utrwalone ślady w `backend/tests/fixtures/*-route.json` służą testom walidacji geograficznej.
