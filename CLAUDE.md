\# HURBA Pricing Simulator — istruzioni per Claude Code



\## Scopo

Tool web di simulazione pricing e marginalità per HURBA S.r.l. (scooter elettrici).

Utenti: 3 persone (GI, CP, AT). Self-hosted su VPS Hetzner in Docker.

Il proprietario NON è un programmatore: ogni step deve produrre file completi

e comandi copia-incollabili, mai patch parziali.



\## Stack (non cambiare senza chiedere)

\- Backend: Python 3.12, FastAPI, uvicorn. Nessun database: scenari = file JSON in data/scenarios/.

\- Frontend: HTML + JS vanilla + Chart.js da CDN. Nessun build step, nessun framework.

\- Test: pytest. Il motore va validato PRIMA di costruire l'interfaccia.

\- Deploy: un solo container Docker, dietro il reverse proxy già presente sul VPS, con basic auth.



\## Principio cardine: tutto parametrizzabile

\- app/engine/defaults.yaml è l'UNICA fonte di verità per parametri e formule.

\- Ogni parametro ha: key, value, label (in italiano, parlante), help (spiegazione chiara),

&#x20; example (quando utile), unit, min/max, group. Il pannello Parametri si genera da questo schema:

&#x20; ogni campo mostra un (?) con help ed esempio.

\- Le formule del motore sono stringhe in defaults.yaml valutate con `simpleeval`

&#x20; (mai eval/exec). Se una formula è invalida: fallback al default + messaggio di errore visibile.

\- Nessun numero hard-coded nel codice Python o JS. Se serve una costante, va in defaults.yaml.



\## Formule di default

\- netto = listino / (1 + iva)                              # iva = 0.22

\- landed = (fob\_usd / fx + freight\_eur) \* (1 + dazio)      # fx = 1.15, dazio = 0.06

\- margine\_diretto = netto - landed

\- prezzo\_dealer = netto \* (1 - sconto\_tier)

\- margine\_dealer = prezzo\_dealer - landed

\- costo\_agente = base\_agente \* pct\_agente                   # base scelta per categoria (vedi sotto)

\- ecobonus = aliquota\_eb\_anno \* netto                       # IVA calcolata sull'imponibile pieno

\- street\_price = listino - ecobonus - promo

\- costo\_cessione = ecobonus \* quota\_ceduta \* (1 - pct\_incasso\_cessione)

\- costo\_factoring = pct\_factoring \* prezzo\_dealer \* (1 + iva)   # solo canale dealer

\- margine\_fully\_loaded = margine\_lordo - costo\_cessione - costo\_factoring - costo\_agente



\## Parametri e default (dettaglio in defaults.yaml)

\- Modelli: Brezza 50, Brezza 125, 150S, 150S LR, 200S, 300S. FOB/freight/landed da defaults.yaml.

\- Listini IVA incl.: Brezza 50 2.999 · Brezza 125 3.899 · 200S 7.990 · 300S 8.990.

&#x20; 150S: preset selezionabili — Base 3.949/4.849 · Combo 3 4.190/5.190 · Combo 4 3.949/5.390 · Custom.

\- Split 150S vs 150S LR: parametro come % (default 45/55) OPPURE quantità assolute.

\- Canali: Diretta / Dealer / Distributore. Mix per anno configurabile.

&#x20; Default 2026: 50/50/0 · 2027: 40/60/0. Distributore (sconto 25%) presente ma 0% su Italia.

\- Tier dealer (sconto su netto IVA): 17% / 18% / 20%. Mix per anno configurabile, default 75/10/15.

&#x20; Demo (22%): parametro presente, default 0 (non considerato per ora).

\- Agenti: lista di categorie, ognuna con nome, pct (default 3%), base applicabile

&#x20; (listino | netto | prezzo\_dealer | margine; default listino), quota vendite dealer con agente

&#x20; (default 100%). Un dealer può avere o no un agente: il calcolo espone entrambe le viste.

\- Ecobonus, parametri separati per anno:

&#x20; EB 2026: senza rottamazione 30%, con 40%, aliquota flat usata 35%.

&#x20; EB 2027: senza rottamazione 20%, con 30%, aliquota flat usata 25%.

&#x20; Opzionale: % mix rottamazione → aliquota effettiva calcolata (override del flat).

\- Cessione credito: quota\_ceduta default 0%, pct\_incasso\_cessione default 100%.

&#x20; Rimborso ecobonus al dealer a T+30 (solo informativo, niente cash flow).

\- Factoring: 1,5% su fattura dealer IVA inclusa, default attivo su 100% vendite dealer.

\- Promo: lista configurabile. Ogni promo ha nome (libero), modelli a cui si applica,

&#x20; tipo sconto (€ fisso | %), valore, tetto unità, anno. Default: "Promo EICMA", 150S e 150S LR,

&#x20; -300 € sul listino, 150 unità, 2027. Lo sconto promo NON riduce la base ecobonus.

\- Volumi Italia — 2026: B50 25, B125 40, 200S 190, 300S 200. 2027: B125 50, 150S tot 500,

&#x20; 200S 200, 300S 250.

\- Benchmark concorrenza (listini editabili): Silence S02 3.790 · NIU NQiX 300 3.599 ·

&#x20; Silence S01 4.590 · NIU NQiX 500 4.599 · Silence S01+ 5.590 · NIU NQiX 1000 6.499 ·

&#x20; Seat MÓ 6.750 · Nerva Exe II 7.760 · BMW CE 02 7.750–8.750.

&#x20; Doppia vista: confronto a listino pieno E confronto con ecobonus applicato a tutti.

\- Covenant (alert): tier 20% <= 15% del fatturato dealer; contribuzione >= 25% su OGNI

&#x20; combinazione modello x canale x tier (al netto di cessione, factoring, agenti);

&#x20; costi finanziari totali <= 17% del margine lordo. Soglie parametrizzabili.



\## Fuori perimetro (non implementare)

Cash flow mensile, stagionalità, ordini Cina, batteria extra 150S come ricavo, unità demo.



\## Validazione del motore

Preset "Validazione (analisi set-2026)": EB 25% entrambi gli anni, 150S 3.949/4.849,

cessione 100% incassata all'80%, nessun agente, nessuna promo.

Con questo preset i test devono replicare entro ±1%:

\- 2026: ricavi \~2,66 M€, margine fully loaded \~1,28 M€ (48,6%), ecobonus \~727 k€

\- 2027: ricavi \~4,6 M€, margine fully loaded \~2,02 M€ (44,0%), ecobonus \~1.283 k€

Landed attesi: B50/B125 1.440 · 200S 2.371 · 300S 3.246 · 150S 1.531 · 150S LR 2.038.



\## Regole di lavoro

\- Lingua di interfaccia e commenti: italiano. Etichette parlanti, mai sigle senza help.

\- Ogni modifica al motore deve mantenere verdi i test di validazione.

\- Prima di ogni step: dire cosa si sta per creare e perché; dopo: comando esatto per verificare.

