# Plan v10 — wskazówki AgriScreen potwierdzone pomiarami

Status: zaakceptowany przez autora 2026-11-01 (D-093). Protokół: `docs/evidence/W7_protokol_wskazowki.md`
(szkic do akceptacji, potem rejestracja przed liczeniem).

## Cel

Pokazać na rzeczywistych pomiarach naziemnych, że wskazówki z panelu — „sucho w okolicy”, „roślinność poniżej
swojej normy”, przymrozek, upał — trafiają częściej niż przypadek. Pokazać to klientowi jako historię trafień,
np. „gdy mówimy »sucho«, czujnik w gruncie potwierdził to w N% dni; przypadkiem byłoby M%”, aktualizowaną co
tydzień. Nie chodzi o dokładną wartość wilgotności gleby, tylko o trafność i użyteczność wskazówki.

## Decyzje

- **D-093 (2026-11-01):** prawda w walidacji to wyłącznie pomiary naziemne i oficjalne rejestry. Model (ERA5-Land)
  i satelita to produkt, nigdy dowód. Wartości uzupełnione (ERA, MDS) i dane syntetyczne nie są wynikiem.
  Stacje wybrane regułą przed liczeniem (wszystkie stacje ICOS we Francji z produktem L2 Fluxnet); stacje nie muszą
  leżeć przy Condom. Metoda produktu bez zmian.

## Kroki

1. Protokół W7 z kryteriami → akceptacja autora → rejestracja (SHA-256, commit) przed liczeniem.
2. Pobranie danych na Dysk z rejestrem `MANIFEST_W7.csv` (adres, data, SHA-256, licencja): ICOS L2 Fluxnet
   i L2 Meteo (10 stacji), deklaracje celne Gers (douane), Sentinel-2 i ERA5-Land dla stacji.
3. Produkt bez zmian metody dla kwadratów wokół wież; testy K1 i K2; notatnik `notebooks/experiments/W7_*.ipynb`;
   notatka `docs/evidence/W7_wyniki.md` (także wynik negatywny).
4. Publikacja: wiersze w „How far to trust it” (panel), README, strona; historia trafień co tydzień ze stacji
   z danymi bieżącymi.
5. Końcowe sprawdzenie produktu: działanie, przepływ danych, porządek, prywatność, uczciwość, gotowość pod
   wnioski (lista braków), tylko dane rzeczywiste.

## Stan realizacji (aktualizowany przy każdym kroku; po przerwie zaczynamy od pierwszego niezrobionego)

- [x] Protokół W7 zarejestrowany 2026-11-02 (commit `cf2dfcf`, SHA-256 `a6689c13…`).
- [x] Kod: `agriscreen/experiments/w7_data.py` (pobieranie, rejestr źródeł), `w7.py` (prawda, wskazówki, testy,
      wiersze panelu), generator notatnika `notebooks/experiments/build_w7.py`.
- [x] Deklaracje celne Gers 2016–2025 pobrane (`09_Reference_Stations/douane`).
- [ ] Archiwa ICOS L2 (10 stacji) → `09_Reference_Stations/<stacja>/`, wpisy w `MANIFEST_W7.csv`.
- [ ] ERA5-Land w punktach stacji → `W7_stacje/<stacja>_era5_land_daily.csv`.
- [ ] Sentinel-2 i statystyki kwadratów 7 stacji → `W7_stacje/<stacja>/` (`w7_data.run_s2_station`, przyrostowo).
- [ ] Notatnik `W7_wskazowki.ipynb` wykonany; `docs/evidence/W7_wyniki.md`; wiersz w `karta_wynikow.md`.
- [ ] Publikacja: wiersze K1/K2 w panelu (`w7.trust_rows`, `w7_tests.csv` w `docs/showcase/`), README, strona.
- [ ] Końcowe sprawdzenie produktu (6 obszarów + tylko dane rzeczywiste).

Wznowienie: brakujące dane dociąga ponowne uruchomienie tych samych funkcji (pobierają tylko to, czego brak).

## Granice (mówimy je wprost)

- Żadna wieża ICOS nie stoi w winnicy. Wieże potwierdzają metodę; o samych winnicach mówią czujnik ISMN w Condom,
  deszczomierz Météo-France i (opisowo) plon wina w Gers.
- Test roślinności może wyjść słaby; wtedy piszemy „niepotwierdzone”.
- Biuletyny BSV Vigne Gascogne pomijamy: opisy słowne, zamiana na liczby byłaby subiektywna.
