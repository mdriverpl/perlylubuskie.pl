# Wdrożenie obrazów Docker

Gotowy zestaw składa się z trzech kontenerów:

| Usługa | Obraz | Dane |
| --- | --- | --- |
| Vue + Nginx | `ghcr.io/mdriverpl/perlylubuskie-web:latest` | frontend i proxy `/api` |
| FastAPI | `ghcr.io/mdriverpl/perlylubuskie-api:latest` | API, schemat i katalog początkowy |
| PostgreSQL | `postgres:17-alpine` | dane w trwałym wolumenie `postgres_data` |

Obrazy aplikacji są budowane dla **Linux amd64**. Serwer wymaga Dockera z Compose v2. Schemat bazy i sześć miejsc początkowych są tworzone automatycznie przy pierwszym starcie API. Hasła, konta użytkowników i zawartość lokalnej bazy nie są publikowane w obrazach.

## Pierwsze uruchomienie na serwerze

Domyślny `compose.yaml` pobiera gotowe obrazy, więc zwykłe `docker compose up -d --wait` nie wymaga katalogu `backend` ani budowania na serwerze. `compose.build.yaml` służy wyłącznie do budowania lokalnego z pełnego checkoutu. `compose.deploy.yaml` zachowano dla wcześniejszych instrukcji.

```sh
git clone https://github.com/mdriverpl/perlylubuskie.pl.git
cd perlylubuskie.pl
sh scripts/setup-deploy.sh
```

Skrypt generuje `.env` z losowym hasłem bazy i sekretem JWT, bez nadpisywania istniejącego pliku. Można też samodzielnie skopiować `.env.deploy.example` do `.env` i uzupełnić wartości. Ustaw `PUBLIC_URL` na docelowy adres i `APP_PORT` na wybrany port.

Nowe pakiety GHCR mogą wymagać autoryzacji. Jeżeli pobieranie zwróci `denied`, zaloguj się kontem z dostępem do pakietów; jako hasła użyj tokena GitHub z uprawnieniem `read:packages`:

```sh
docker login ghcr.io -u TWOJ_LOGIN_GITHUB
```

Następnie:

```sh
docker compose -f compose.deploy.yaml pull
docker compose -f compose.deploy.yaml up -d --wait --wait-timeout 180
docker compose -f compose.deploy.yaml ps
curl --fail http://localhost:8080/api/health
```

Aplikacja jest dostępna pod `http://ADRES_SERWERA:8080`. Do publicznego ruchu HTTPS skieruj własną domenę przez reverse proxy na port aplikacji; przy proxy na tym samym serwerze ustaw `APP_BIND=127.0.0.1`. Baza i API nie wystawiają osobnych portów na serwerze.

## Hostava

Wklej zawartość **`compose.hostava.yaml`** jako definicję aplikacji. Ten plik używa obrazów GHCR, bez `build`, ścieżek do źródeł i mapowania portu hosta. W panelu ustaw:

- usługa publiczna: `web`;
- port HTTP dla proxy Hostavy: **8080** (port hosta; Nginx w kontenerze s?ucha na 80);
- ścieżka zdrowia: `/api/health`;
- zmienne: własne `POSTGRES_PASSWORD`, `SECRET_KEY` i `PUBLIC_URL=https://TWOJA_DOMENA`.

Zachowaj dotychczasowe hasło i wolumen PostgreSQL przy aktualizacji istniejącej aplikacji. Nie zmieniaj hasła tylko w `.env`, jeżeli baza jest już zainicjalizowana. Nie wklejaj `compose.build.yaml` do panelu — Hostava nie ma lokalnego katalogu źródeł `backend`.

## Automatyczna publikacja i weryfikacja

Workflow [Docker images](https://github.com/mdriverpl/perlylubuskie.pl/actions/workflows/docker-publish.yml) po każdym pushu na `main`:

1. Uruchamia testy Vue i API z rzeczywistym PostgreSQL.
2. Buduje oba obrazy i publikuje je do GHCR z tagami `latest` oraz pełnym SHA commita.
3. Pobiera opublikowane obrazy i uruchamia `compose.deploy.yaml` na pustej bazie.
4. Sprawdza przez Nginx stronę, stan bazy, rejestrację, logowanie, ulubione, zapis planu i pobranie GPX.
5. Usuwa wyłącznie jednorazowy zestaw testowy na runnerze GitHub Actions.

Przed wdrożeniem wybieraj wersję z zielonym wynikiem wszystkich trzech etapów. Do powtarzalnych wdrożeń ustaw w `.env` `IMAGE_TAG=PELNY_SHA_COMMITA`; `latest` jest aktualizowany na `main`.

## Aktualizacja i powrót do poprzedniej wersji

```sh
git pull --ff-only
docker compose -f compose.deploy.yaml pull
docker compose -f compose.deploy.yaml up -d --wait --wait-timeout 180
```

Dane bazy pozostają w wolumenie. Powrót do obrazu: zmień `IMAGE_TAG` na SHA wcześniej działającego commita i ponów `pull` oraz `up`. Zmiany schematu bazy wymagają oddzielnych migracji i planu wycofania — ten starter inicjalizuje aktualny schemat przez SQLAlchemy `create_all`.

## Kopia zapasowa i logi

Na serwerze Linux:

```sh
docker compose -f compose.deploy.yaml exec -T db pg_dump -U perly -d perly -Fc > perly-backup.dump
docker compose -f compose.deploy.yaml logs --tail=100 api web
```

Plik kopii zawiera dane użytkowników: przechowuj go poza repozytorium, w bezpiecznym miejscu. `docker compose -f compose.deploy.yaml down` zatrzymuje aplikację z zachowaniem danych; nie używaj `down -v`, jeśli chcesz zachować bazę.

Obrazy obejmują bieżące funkcje i dane demonstracyjne opisane w README. Eksport GPX nadal zawiera punkty do odwiedzenia, bez routingu po drogach.
