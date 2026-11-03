# Zadania administratora

Panel pokazuje postęp, wykonawcę/model i osobne przyciski Start/Zatrzymaj dla
fotografii, kontaktów oraz opisów wybranego regionu. Otwarcie panelu nie
uruchamia płatnych zadań. Domyślnie kontakty pozostają zatrzymane po restarcie.
Każdy ręczny Start sprawdza najwyżej 10 kontaktów; błędy nie są ponawiane
automatycznie. Region sprawdza domyślnie 25 obiektów, maksymalnie 100 na Start.

Modele można ustawić niezależnie:

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

Kolejne wdrożenia zachowują kontakty i fotografie pobrane na produkcji. Rejestr
Wikimedia przy każdym zdjęciu zawiera autora, źródło i licencję. Zadania nie
zastępują ręcznie dodanych fotografii ani społecznościowych danych miejsca.
