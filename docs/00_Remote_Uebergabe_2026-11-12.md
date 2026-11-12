# Remote-Übergabe — Fly Connectome Sim / Fly Exchange

Stand: **12. November 2026**. Arbeitszeitraum: **12.–26. November 2026**.
Diese Datei zuerst lesen, danach `cloud-handover.md` und `getting-started.md`.

## Verfügbarkeit und maßgebliche Version

- Der lokale Projektname ist `flay-connectome-sim`; das Repository heißt
  [manu-brighter/fly-connectome-sim](https://github.com/manu-brighter/fly-connectome-sim).
- Verbindlicher ausführbarer Ausgangsstand:
  **`65601b5da697101790f0eac6c877bfbe54a76e3e`**, Branch
  **`feat/connectome-experiment-core`**. Lokaler Stand und Remote-Branch wurden
  am 12. November durch `git ls-remote` abgeglichen und waren identisch.
- [Unveränderlicher Quellstand](https://github.com/manu-brighter/fly-connectome-sim/tree/65601b5da697101790f0eac6c877bfbe54a76e3e)
  und [vollständiger Original-Download](https://github.com/manu-brighter/fly-connectome-sim/archive/65601b5da697101790f0eac6c877bfbe54a76e3e.zip)
  sind unabhängig vom ausgeschalteten PC verfügbar. Das Repository ist öffentlich;
  darin sind keine privaten Laufzeitdaten oder Rollen-Zugänge enthalten.
- [CI dieses ausführbaren Stands](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42899642066)
  wurde am 12. November erneut abgefragt: alle vier Jobs erfolgreich
  (Market, Buffer, Tiny-native/Session, Viewer samt Build). Das ist Software- und
  Plattformkompatibilität, keine wissenschaftliche Qualifikation.
- **Cloud-Projektzuordnung und dauerhafter Quellen-Upload sind noch offen.**
  Die verbundene Liste enthält dieses Projekt nur lokal; der Projektlink wurde
  angefragt. Der automatisierte Browser ist nicht angemeldet. Ein anderer
  angemeldeter Browser war im fremden Projekt „Jobsuche“ geöffnet; dessen
  Inhaltszugriff wurde durch die automatische Freigabeprüfung abgelehnt.
  Kein erfolgreicher Upload und keine abschließende Cloud-Prüfung werden behauptet.
- Die vorbereitete Dateiauswahl enthält einen Index mit Herkunft, SHA-256 und
  Uploadstatus. `auswahl-manifest.json` benennt jede Datei; Originalarchive
  bewahren die bearbeitbaren Quelldateien. Gebündelte Texte sind zusätzliche
  Lesefassungen, kein Ersatz für ihre versionierten Originale.

## Aktueller Produktstand

**Aktiver Schwerpunkt: lokaler experimenteller Getränkepreis-Pilot „Fly Exchange“.**
Python/SQLite verwaltet dauerhafte Preise; eine separate Browseransicht zeigt
die animierte Fliege am Trading-Tisch, bestätigte Preisänderungen, beobachtete
Preisverläufe und sieben gemessene Populationskurven. Freigegebene, tatsächlich
begonnene und noch frische Bilder erscheinen auf ihrem Handy. Bewegung und
Preisgesten sind Illustrationen; statische Verbindungen sind keine gemessene
synaptische Übertragung. Live-Zell-/Anatomieansichten sind separat offen.

Der ursprüngliche Beobachtungsdemo ist abgeschlossen: echte API-Proposal → eine
kontinuierliche native Sitzung → gemessene Auswahl → unveränderter Plan → Film.
Der separate deutsche Planungsbegleiter und kombinierte Demo-Import sind ebenfalls
abgeschlossen. Die Lernassay-Forschung bleibt geparkt und unqualifiziert.

## Verbindliche Entscheidungen

- Das Modell bestimmt Getränk und Zielpreis über das deklarierte technische
  Motor-Readout. Keine behaupteten zwanzig biologischen Getränkekanäle.
- Ganze Sprünge innerhalb der konfigurierten Getränkepreisspanne sind erlaubt.
  **Kein CHF-0.50-Limit pro Änderung.** Preise sind ganzzahlige Rappen;
  das konfigurierte Preisraster bleibt maßgeblich.
- Zwischen tatsächlichen Änderungen desselben Getränks liegen mindestens
  **30 Minuten Realzeit**. `no_change` startet diese Sperre nicht neu.
  Modellzeit und Realzeit bleiben getrennt.
- Personal übernimmt die angezeigten Preise manuell; kein Kassensystem/POS im
  ersten Pilot. Serverseitige Aktivierung ist dauerhaft und braucht keine
  manuelle Bestätigung jeder einzelnen Änderung.
- Keine erzwungene Rotation oder regelmäßige Preisänderung. Lange stille Phasen
  und Favoriten sind akzeptiert; alle konfigurierten Getränke bleiben technisch
  wählbar. Technische Erreichbarkeit und tatsächlich beobachtete Vielfalt getrennt
  ausweisen; historische Beobachtung war oft nur ein Getränk von zwanzig.
- Langsamer als Echtzeit ist im ersten lokalen Pilot akzeptiert. Modelluhr,
  Warteschlange, Messfrische und Verbindungszustand ehrlich anzeigen.
- Endliche Bildwarteschlange und höchstens **fünf reale Minuten** von Annahme bis
  Übergabe. Volle Queue ablehnen, abgelaufene Bilder nicht verspätet übergeben.
  Bilder durchlaufen private Vorschau und menschliche Freigabe.
- Ein verarbeiteter Bildeingang braucht acht zusammenhängende validierte
  Beobachtungen à 500 ms. Auch schwarze Intervalle vorrücken lassen; eine
  kontinuierliche Engine, keine versteckten Resets. Lernen und externe DAN aus.
- Pause, Presence/ACK, Idempotenz, Neustart-/Uhrfehlerbehandlung und konservativer
  Offline-Zustand bleiben Teil der Preisautorität. Synthetische und native
  Preiswege sowie deren Datenbanken strikt getrennt halten.
- Originalkern, Provenienz-Locks und MIT-Hinweis erhalten. Keine Aussagen über
  Bewusstsein, Semantik, biologisches Lernen, Dopaminkonzentration,
  Rezeptoraktivität oder validiertes Motorverhalten.
- Neue Messungen nur mit konkretem geprüftem Protokoll und endlichen Grenzen.
  Kein automatischer bezahlter API-Aufruf, kein Guthabenkauf und kein Retry.
  Kein PR, Merge, Deployment oder öffentliche Freigabe ohne separaten Auftrag.

## Ergebnisse und Grenzen

1. **Akzeptierter nativer Pilot02 vom 10. November:** 80 Beobachtungen / 40
   Modellsekunden, zwei generierte Bilder mit jeweils acht verarbeiteten
   Beobachtungen; 197 Ereignisse und 3462 Monitorrecords. Eine tatsächliche
   Aktivierung `drink-00` von CHF 4 auf CHF 5, später `no_change` bei CHF 5.
   Cleanup bestätigt; Quellbindungen stimmen. Das belegt weder Bildkausalität
   noch Mehrstundenbetrieb. Quelle: `2026-11-10-native-worker-software.md`.
2. **Fly-Exchange-Ansicht:** echtes freigegebenes Bild in Beobachtungen 52–59
   verarbeitet; Handy-Anzeige bei abgeschlossener Beobachtung 53 pixelgenau geprüft
   und später bei Schwarz entfernt. Bewegung bleibt illustrativ.
   Historische lokale Checks: 339 Viewer-Passes / ein Windows-Symlink-Skip,
   198 betroffene Backend-Passes, TypeScript und Build erfolgreich. Diese Zahlen
   sind dokumentierte damalige Prüfungen; am 12. November wurde kein Modelllauf
   und keine vollständige Testsuite erneut gestartet.
3. **Negative Vorstufen bleiben negativ:** kontinuierlicher v1-Motor-Probe ohne
   vollständige Vorschläge; Balanced-Rearm ohne Release/Vorschläge;
   Population-Excursion-Screen ohne unterstützte Blöcke. Die später separat
   definierte ContinuousMotorDrive-Auswertung hebt diese Ergebnisse nicht auf.
4. **Historischer Beobachtungsdemo vom 8. November:** 7 s Feed + 2 s Karten,
   L7/R2 → Sunset Rooftop Social; 256 Zellen, 512 statische Verbindungen,
   90 abgeschlossene 100-ms-Fenster. Film 360 Frames / 12 s einschließlich
   beschriftetem 3-s-Präsentationshalt. Keine stabile semantische Präferenz.

## Offene Aufgaben für die Remote-Fortsetzung

1. Ziel-Cloud-Projekt per eindeutigem Link zuordnen, vorhandene Quellen prüfen,
   fehlende/neuere ausgewählte Dateien hochladen und nach Neuladen einzeln
   nachweisen. Vorhandene Cloud-Quellen erhalten. Aktuellen Uploadstatus im
   separaten Manifest/Prüfprotokoll dokumentieren.
2. Den nächsten Produktschritt anhand des lokalen Pilots festlegen. Als echte
   Restarbeit dokumentiert sind längere Realzeit-Generalprobe und konkrete
   Last-/Kapazitätsprüfung. 10–20 Getränke, 50–300 Gäste und meist 6–8 Stunden
   sind Planungsgrößen, keine nachgewiesene Leistung. Etwa zwölf Stunden sind
   eine spätere Testreferenz, keine automatisch bestätigte Laufzeit.
3. Vor neuer Ausführung die benötigte Cloud-Umgebung separat herstellen:
   Original-Repository, Python 3.12.14, uv 0.12.15, Node 24.21.0/npm 11.19.0,
   gesperrte Abhängigkeiten und C++17-Compiler; genaue Schritte stehen in
   `getting-started.md`. Linux-CI mit kleinen/data-free Fällen ist geprüft;
   Fullgraph-Linux und der Windows-spezifische Bild-/Workerpfad sind nicht als
   austauschbare Produktionsumgebung qualifiziert.
4. Für einen Fullgraph-Lauf die offiziellen checksum-gebundenen MaleCNS-Daten
   separat herunterladen und aufbereiten (etwa 1,1 GB Quelldownload plus
   generierte Daten). Das Quellenpaket enthält weder Laufzeitdaten noch lokale
   Compiler-Caches oder Checkpoints. Keine historischen Zustände nachbauen und
   als Original ausgeben. Vor neuem Messlauf dessen Ressourcen prüfen.
5. Öffentlicher Eventbetrieb, Hosting/Erreichbarkeit, langes Eventprofil,
   reiche Live-Anatomie/Zellen und biologische Forschung sind jeweils separat
   zu entscheiden. Das Quellenhochladen startet keinen Server und erhält
   keinen lokalen Prozess bei ausgeschaltetem PC.

Es sind keine konkreten Eventtermine oder zugesagten Lieferfristen dokumentiert.
Der Zeitraum 12.–26. November ist die gewünschte Remote-Arbeitsphase.

## Überholte Angaben eindeutig einordnen

- `cloud-handover.md` enthält eine fortgeschriebene Chronik. „Next“, „now“,
  „ongoing“, Prozessnummern und lokale Portlinks aus älteren Absätzen gelten
  jeweils zum damaligen Datum, nicht als aktueller Laufstatus.
- Die am 10. November gestartete Trader-Sitzung war damals laufend/unversiegelt.
  Aus dem bisherigen Chat ist ein späteres Prozessende ohne erfolgreich
  bestätigten Abschluss ersichtlich. Am 12. November wurde lokal kein Listener
  auf Port 18767 gefunden. **Nicht als laufend oder erfolgreich abgeschlossen
  behandeln.** Der akzeptierte endliche Pilot02 ist davon getrennt.
- Frühere Vorgaben „Training vor Reels“, verpflichtendes ruhiges Rearm,
  Stage-A ohne HTTP, frühe „keine native Preisaktivierung/kein Frame-Endpunkt“
  und frühere „Implementation is next“-Sätze sind durch die später akzeptierten
  Produkt-/Implementierungsschritte überholt. Negative Messungen bleiben gültig.
- Die alten Freeze-/Fingerprint-Absätze beziehen sich auf ihre jeweils
  bezeichneten Quellenstände. „Kein neuer Fullgraph-Lauf“ im alten
  Follow-up-Kontext ist keine Verneinung des späteren endlichen Pilots.
- Der ursprüngliche Produktplan und die Assay-Unterlagen sind historische bzw.
  geparkte Forschung. Sie steuern keine automatische Rückkehr in die Lernassay.

## Originale, Nachweise und Links

- [Verbindliche Projektregeln](https://github.com/manu-brighter/fly-connectome-sim/blob/65601b5da697101790f0eac6c877bfbe54a76e3e/AGENTS.md)
- [Fortgeschriebene technische Übergabe](https://github.com/manu-brighter/fly-connectome-sim/blob/65601b5da697101790f0eac6c877bfbe54a76e3e/docs/cloud-handover.md)
- [Setup, Daten und Bedienung](https://github.com/manu-brighter/fly-connectome-sim/blob/65601b5da697101790f0eac6c877bfbe54a76e3e/docs/getting-started.md)
- [Marktkonzept](https://github.com/manu-brighter/fly-connectome-sim/blob/65601b5da697101790f0eac6c877bfbe54a76e3e/docs/superpowers/specs/2026-11-09-live-drink-market-design.md)
- [Nativer Pilot und exakte Ergebnisgrenzen](https://github.com/manu-brighter/fly-connectome-sim/blob/65601b5da697101790f0eac6c877bfbe54a76e3e/docs/experiments/2026-11-10-native-worker-software.md)
- [Offizielle MaleCNS-Daten](https://male-cns.janelia.org/download/)
- [Upstream-/Lizenzhinweise](https://github.com/manu-brighter/fly-connectome-sim/blob/65601b5da697101790f0eac6c877bfbe54a76e3e/THIRD_PARTY.md)
- [Unterschied lokale und Cloud-Projektquellen](https://learn.chatgpt.com/docs/projects)

Die Dateiauswahl bewahrt wichtige Konzepte, Implementierungspläne und Ergebnisse
einzeln im Original. Ergänzende Textsammlungen bündeln historische Entscheidungen
und Nachweise mit ihren Repository-Dateinamen. Vollständiger Quellcode, Tests,
Konfiguration, Lockfiles, Dokumentation und Lizenztexte liegen außerdem als
Originalarchiv vor. SHA-256 im Manifest prüft Dateigleichheit, keine wissenschaftliche
Reproduzierbarkeit oder native Replay-Attestation.

Lokale Zugangsdaten, API-Schlüssel, Rollen-URLs, private Bedienlogs, Abhängigkeiten,
Caches, temporäre Testdateien und Referenzbilder sind ausgeschlossen. Ausgewählte
historische Ergebnisoriginale werden getrennt verpackt; vollständige Laufverzeichnisse
und Datenbanken werden nicht pauschal kopiert. Der alte private Ideationschat ist
keine aktuelle Anforderung und wird nicht als Projektregel hochgeladen.

**Spätere lokale Änderungen müssen erneut in die Cloud-Projektquellen hochgeladen
werden.** Ein Git-Push aktualisiert diese Quellen nicht automatisch. Unterwegs
geänderte Dokumente ebenfalls versioniert sichern und bei Rückkehr mit dem
Repository abgleichen; alte Cloud-Quellen nicht stillschweigend überschreiben.
