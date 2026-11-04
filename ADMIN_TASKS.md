# Zadania administratora

## Katalog jezior Lubuskiego

Przy starcie API domyślnie działa addytywny import `backend/lake-catalogs/lubuskie.json`.
Połączono regionalny wyciąg OSM/Geofabrik (pełne geometrie, dokładna granica
województwa i nazwy gmin) z Wikidata. Katalog zawiera 508 pozycji, w tym 115
akwenów bez nazwy w źródle. Zawiera m.in. Liwno/Zabór, Liwno Małe i Jezioro
Droszkowskie. Nazwy jeziorne niekiedy odnoszą się do stawów lub starorzeczy;
oryginalny typ wody jest zachowany w `details.lake_catalog.water_type`.

Import dopasowuje identyfikatory, aliasy i zasięgi akwenów. Nie usuwa istniejących
rekordów ani nie zmienia ich ID, opisów, zdjęć, kontaktów i lake_info. Nie
zatrzymuje innych zadań. Wersja pliku jest zapisywana w `lake_catalog_imports`,
więc restart nie powiela danych. Testy izolują import przez `LAKE_CATALOG_IMPORT=0`;
test dedykowany sprawdza import bezpośrednio. Nie używa OpenAI ani płatnych tokenów.

Źródłowy JSON jest dostępny jako `/lakes-lubuskie.json`, a atrybucja i licencje
jako `/lakes-credits.html` (OSM: ODbL 1.0; Wikidata: CC0 1.0). Odtwarzanie:
`scripts/extract-lubuskie-lakes.py` (wymaga osmium i shapely), następnie
`scripts/build-lubuskie-lakes.py`. Pliki wejściowe są w `.tools/lubuskie-lakes-sources`.
Publiczne źródła nie gwarantują kompletnego urzędowego rejestru wszystkich wód.

## Zadania z promptu

Panel zawiera formularz promptu i listę zadań, bez oddzielnych sekcji dodawania
i zarządzania województwem. Można wpisać np. „Dodaj województwo lubelskie —
atrakcje, opisy i zdjęcia”. Zapis tworzy tylko zadanie. Start dodaje brakujący
region i wyszukuje atrakcje, opisy oraz dostępne zdjęcia w porcjach do 25 obiektów
na uruchomienie. Domyślnie pomija noclegi, restauracje i winiarnie. Istniejący
region jest uzupełniany bez tworzenia duplikatu regionu. Status zadania jest
powiązany z rzeczywistym zadaniem wyszukiwania; model jest przypisany do zadania.
Zatrzymanie odrzuca spóźnione wyniki; ponowny Start czeka na zakończenie zatrzymywania.
Restart zatrzymuje powiązane wyszukiwanie przed uruchomieniem wykonawcy.

Można też zapisać np. „Uzupełnij wszystkie numery telefonów dla zamków”.
Zapis nie wywołuje OpenAI: rozpoznaje zakres i pola, tworzy kolejkę istniejących
obiektów z brakującymi danymi i pokazuje jej liczebność. Obsługiwane pola to
telefon, e-mail, WWW, noclegi i restauracja. Dodawanie województwa ma opisany
powyżej tryb wyszukiwania nowych atrakcji. Nierozpoznane polecenia są odrzucane.
Zakres kategorii, województwa i pól jest widoczny przy zapisanym zadaniu.

Każde zadanie ma własny zapisany model, prompt, postęp i przyciski Start,
Zatrzymaj i Usuń. Jeden Start sprawdza do 10 obiektów w porcjach po 2; pozostałe
wymagają kolejnego Start. Wyszukiwane są oficjalne źródła, a tylko potwierdzone
brakujące pola trafiają od razu do bazy. Istniejące wartości, zdjęcia i pozostałe
pola nie są nadpisywane. Błąd zatrzymuje pracę bez automatycznych płatnych prób.
Wspólna blokada PostgreSQL zapobiega jednoczesnej pracy z dawnym zadaniem kontaktów.

Kolejka i wyniki są w tabelach `admin_prompt_tasks` i `admin_prompt_task_items`.
Usunięcie zatrzymuje zadanie i ukrywa je na liście; przywrócenie nie uruchamia
pracy. Restart serwera także pozostawia zadania zatrzymane. Zmienna
`PROMPT_TASK_WORKER=0` wyłącza wykonywanie i ręczny Start. Testy ustawiają ją na 0
i zastępują dostawcę AI, bez wysyłania płatnych zapytań.

## Zadania wbudowane

Prompt „Dodaj jeziora w województwie lubuskim, opisz czy można tam pływać,
czy mogą pływać motorówki, czy jezioro ma plaże” rozpoznaje jako cel jeziora,
a pytania po „opisz” jako szczegóły. Dodaje do kolejki również istniejące jeziora,
zanim spróbuje pobrać nowe. Wyszukiwanie jezior korzysta najpierw z Wikidata
(typ jezioro, relacja administracyjna do kodu ISO województwa, współrzędne),
następnie z Commons i OSM. Awaria odkrywania nie cofa zapisanych uzupełnień.

Informacje `lake_info` zawierają osobne odpowiedzi swimming/motorboats/beach,
źródło, wyjaśnienie zakresu i datę sprawdzenia. Yes/no wymaga źródła rzeczywiście
zwróconego przez wyszukiwanie; pozostałe odpowiedzi są unknown. Karta jeziora
pokazuje te pola i odnośniki. Uzupełnienie zachowuje opis, zdjęcia i kontakt;
odświeżenie katalogu przy wdrożeniu zachowuje lake_info. Szczegółowe pytania o
jeziora są sprawdzane porcjami po 2, nadal do 25 obiektów na Start.

Panel pokazuje postęp, wykonawcę/model i osobne przyciski Start/Zatrzymaj dla
fotografii, kontaktów oraz opisów wybranego regionu. Otwarcie panelu nie
uruchamia płatnych zadań. Domyślnie kontakty pozostają zatrzymane po restarcie.
Każdy ręczny Start sprawdza najwyżej 10 kontaktów; błędy nie są ponawiane
automatycznie. Region sprawdza domyślnie 25 obiektów, maksymalnie 100 na Start.

Nie ma etapu szkicu ani publikacji województwa. Wszystkie regiony są aktywne,
a zatwierdzone przez zbieranie miejsca trafiają bezpośrednio do publicznego
katalogu. Starsze szkice stają się aktywne przy uruchomieniu nowej wersji.
Zbieranie można uruchamiać ponownie również w istniejących województwach.
Przycisk Usuń zadanie zatrzymuje pracę i usuwa wiersz z listy (trwale zapisane
ukrycie); zachowuje miejsca, zdjęcia, wyniki i historię. Przywrócenie wierszy
nie uruchamia ich pracy. Zadanie regionu jest usuwane tylko dla wybranego regionu.

Modele można wybrać niezależnie w panelu Zadania: Luna, Terra, Sol lub Astra.
Wybór zapisuje się w PostgreSQL, przetrwa restart i ma pierwszeństwo przed
zmiennymi środowiska. Sam zapis nie uruchamia żadnego zadania. Zmiana kontaktów
wymaga zatrzymania tego zadania; zmiana opisów wymaga zatrzymania zbierania we
wszystkich regionach. Planer stosuje nowy model od następnego zapytania.
Zdjęcia nie korzystają z AI i nie mają wyboru modelu. Dostępność wybranego
modelu zależy także od uprawnień konta OpenAI.

Domyślne modele przy braku zapisanego wyboru:

- `OPENAI_CONTACT_MODEL=gpt-6-luna` — kontakty i usługi;
- `OPENAI_RESEARCH_MODEL=gpt-6-luna` — opisy i badanie atrakcji;
- `OPENAI_PLANNER_MODEL=gpt-6.1-terra` — interaktywny planer wycieczek.

Nie ma automatycznego przełączenia na droższy model. Wyszukiwanie WWW jest
rozliczane przez OpenAI niezależnie od tokenów. Aktualne modele i ceny opisuje
[oficjalna dokumentacja OpenAI](https://developers.openai.com/api/docs/models).

`CONTACT_RESEARCH_RUN` identyfikuje kolejkę kontaktów. Nie należy zmieniać jej
przy zwykłym wdrożeniu, ponieważ nowy identyfikator tworzy nową kolejkę.
`CONTACT_RESEARCH_AUTOSTART=0` wyłącza automatyczne uruchamianie; Start w panelu
uruchamia jedną ograniczoną porcję. `CONTACT_RESEARCH_WORKER=0` dodatkowo wyłącza
także ręczny Start na serwerze. Zatrzymanie zachowuje gotowe wyniki i odrzuca
odpowiedź zapytania, które było już w toku; nie uruchamia kolejnych zapytań.

Zdjęcia korzystają tylko z Wikimedia Commons/Wikidata/OpenStreetMap, bez
OpenAI. `PHOTO_RESEARCH_RUN` tworzy jednorazowe zadanie dla
`PHOTO_RESEARCH_REGION` (domyślnie lubuskie). Ten sam identyfikator zachowuje
postęp i stan zatrzymania po wdrożeniu. Domyślnie zmienna jest pusta, a zadanie
uruchamia administrator przyciskiem Start. `PHOTO_RESEARCH_WORKER=0` wyłącza
wykonywanie kolejki. Wyniki i kolejka są zapisywane w PostgreSQL, pobrane zdjęcia
w `catalog_media`. Zatrzymanie zachowuje gotowe wyniki. Brak jednoznacznej
fotografii na obsługiwanej licencji jest wykazywany w raporcie.

Jeziora w Lubuskiem bez fotografii mają zapisane podglądy map: 430 plików
WebP 1200 × 800 w `public/images/lake-maps/`. Są renderowane lokalnie z danych
OSM/Geofabrik, bez pobierania kafelków publicznego serwera i bez AI. Dwa obiekty
bez obrysu mają oznaczenie przybliżonej lokalizacji. Mapa zawiera atrybucję OSM,
a szczegóły miejsca udostępniają źródło i licencję ODbL.

`scripts/extract-lake-map-context.py` przygotowuje kontekst z regionalnego PBF;
`scripts/render-lake-map-previews.py` generuje obrazy i manifest
`backend/lake-map-previews.json`. Narzędzia lokalne wymagają Pillow, Shapely i
pyosmium. Import manifestu przy starcie API uzupełnia tylko brakujące obrazy
lub poprzednie podglądy, zachowując prawdziwe fotografie i pozostałe dane.
`LAKE_MAP_PREVIEWS_IMPORT=0` wyłącza import. Ręczny Start zadania zdjęć może
zastąpić mapę fotografią z potwierdzonym źródłem; dla jezior bez nazwy wymagane
jest bezpośrednie powiązanie zdjęcia z rekordem OSM/Wikidata.

Kolejne wdrożenia zachowują kontakty i fotografie pobrane na produkcji. Rejestr
Wikimedia przy każdym zdjęciu zawiera autora, źródło i licencję. Zadania nie
zastępują ręcznie dodanych fotografii ani społecznościowych danych miejsca.

## Zdjęcia dodawane przez użytkowników

Zalogowana osoba może dodać do 5 własnych zdjęć przy tworzeniu miejsca oraz
uzupełnić je później w szczegółach swojego miejsca. Wymagane jest potwierdzenie
prawa do publikacji. Inne konta nie mogą dodawać zdjęć do tego miejsca.
Obsługiwane pliki: JPG, PNG, WebP, do 10 MB i 20 megapikseli. API sprawdza
rzeczywisty format, obraca obraz według EXIF, zmniejsza do 1600 px i zapisuje
WebP bez metadanych. Pierwsze zdjęcie jest główne, pozostałe tworzą galerię.

Pliki i powiązanie z autorem są przechowywane w tabeli `place_photos` PostgreSQL;
kopie zapasowe bazy obejmują również te obrazy. Przesyłanie używa autoryzowanego
`POST /api/place-photos`, a zapis miejsca atomowo przypina wybrane identyfikatory.
Nieprzypięte pliki nie są publiczne. Porzucone pliki starsze niż 24 h są usuwane
przy kolejnym przesłaniu; limit wynosi 20 oczekujących plików i 30 na godzinę
na konto. Dodawanie do istniejącego miejsca sprawdza `details.submitted_by`.
