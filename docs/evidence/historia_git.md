# Historia repozytorium przepisana 2026-11-02 (D-094)

**D-094 (2026-11-02, decyzja autora):** z całej historii git usunięto materiały, które nie powinny być publiczne:

- surowe dane ISMN (`data/7_isismn_data/`, 144 pliki) i dzienny szereg z czujnika ISMN w Condom
  (`docs/evidence/F4_eksperymenty/A_roslinnosc_weryfikacja/ismn_rz.csv`) — licencja ISMN pozwala tylko na użycie
  naukowe i zabrania przekazywania danych dalej;
- prywatne materiały autora: dwie notatki planistyczne w całości, prywatne fragmenty kilku archiwalnych planów,
  lokalne ścieżki do plików w starszych wersjach dokumentów i adres e-mail w danych autora 31 commitów (zamieniony
  na adres GitHub autora).

Przepisanie zrobiono w dwóch przejściach tego samego dnia, więc tabela podaje trzy identyfikatory: oryginalny,
pośredni (istniał kilka godzin) i obecny.

**Co się nie zmieniło:** każdy z 140 oryginalnych commitów ma swojego następcę; kolejność, daty, opisy i autorzy
(poza adresem e-mail w 31 commitach) są te same, podobnie kod, wyniki i protokoły. Pliki protokołów są identyczne,
więc sumy SHA-256 z rejestracji przed liczeniem dalej się zgadzają: W3b `f01b74a804b2`, W3c `45708189b130`,
W3d `599a381bb6d1`, W3e `ff20babadf13`, W7 `a6689c13870c`.

**Co się zmieniło:** identyfikatory commitów i tagu `v1.2`; podpisy cyfrowe 73 commitów zniknęły (przepisanie ich
nie zachowuje). Tabela: [`historia_git_mapa.csv`](historia_git_mapa.csv). Odwołania w dokumentach i w opisach
commitów zamieniono na nowe. Stare identyfikatory zostają w zapisanych wynikach notatników i w dawnych przebiegach
GitHub Actions — tłumaczy je tabela.

Oryginalna historia jest zachowana w prywatnej kopii autora (do wglądu na prośbę, np. przy ocenie wniosku).
