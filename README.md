# Perły Ziemi Lubuskiej

Projekt aplikacji turystycznej na podstawie dwóch dostarczonych wizualizacji. Vue 3 + Vite, Python / FastAPI, PostgreSQL 17, SQLAlchemy 2, Leaflet / OpenStreetMap. Interfejs po polsku, układ dostosowany do komputera i telefonu.

**Gotowe obrazy Docker i wdrożenie:** [DEPLOYMENT.md](DEPLOYMENT.md). Domyślny `compose.yaml` oraz `compose.deploy.yaml` pobierają frontend i API z GitHub Container Registry i uruchamiają PostgreSQL z trwałym wolumenem. Hostava używa `compose.hostava.yaml` i portu hosta dla proxy: **8080**, mapowanego na port 80 Nginxa w kontenerze. Lokalny build ze źródeł jest w `compose.build.yaml`.

## Funkcje

- Strona odkrywania regionu: wyszukiwanie, kategorie, katalog miejsc, szczegóły, inspiracje wycieczek.
- Planer: interaktywna mapa, wybór punktów, zmiana kolejności oraz rzeczywiste trasy piesze i rowerowe po danych OpenStreetMap, wyznaczane przez własny BRouter.
- Dystans po trasie, orientacyjny czas bez postojów i GPX ze śladem oraz punktami. Tryb samochodowy pozostaje planem punktów.
- Lokalne ulubione i plany bez zakładania konta.
- Rejestracja i logowanie: Argon2, JWT z terminem ważności; ulubione oraz zapisane plany przypisane do użytkownika w PostgreSQL.
- Backend niedostępny: jawnie oznaczony tryb demonstracyjny z katalogiem i zapisem w przeglądarce. Logowanie pozostaje wyłączone.

## Uruchomienie całego projektu

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
