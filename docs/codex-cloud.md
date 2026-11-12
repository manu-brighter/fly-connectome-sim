# Codex Cloud — getestetes Linux-Setup, 12. November 2026

Maßgeblich für die Remote-Arbeit **12.–26. November** ist dieses ausführbare
Setup. Der frühere ChatGPT-Projektquellen-Upload ist für diesen Auftrag ersetzt.
Schwerpunkt bleibt **Fly Exchange**; die Lernassay bleibt geparkt.

## Geprüfte Ergebnisse und Plattformstatus

| Bereich | Tatsächlicher Stand |
| --- | --- |
| Entwicklung und Tests | **Alle vier Kompatibilitätsgruppen bestanden** (3100 Passes, 134 begründete Skips); TypeScript/Build erfolgreich. Synthetische Tafel im echten Chromium geprüft. |
| Daten | Offizielle MaleCNS-Quellen heruntergeladen, verifiziert, hart verlinkt, normalisiert und aufbereitet; `verify-prepared` erfolgreich. |
| Nativer Live-Pilot | **Unter Linux nicht verfügbar.** Bilddecoder und nativer Worker benötigen Windows-Prozessbesitz, Pfade und Tool-Bindungen. Keine Fullgraph-Simulation ausgeführt. |
| Wiederverwendbare Plattform-Umgebung | Installations-/Startkonfiguration im Repository gespeichert und ausgeführt. **Noch nicht als Codex-Umgebung veröffentlicht:** dieser normale Default-Task hat keine zugeordnete Konfigurationsversion und bietet keine Save-draft-/Publish-Werkzeuge. |

## Unterwegs fortsetzen und einmalig veröffentlichen

**Diesen Task** auf Browser oder Handy wieder öffnen; Windows kann ausgeschaltet
bleiben. Arbeitsverzeichnis hier: `/workspace/fly-connectome-sim`. Neue Tasks haben
eigene Arbeitsverzeichnisse. Der lokale Checkout allein registriert kein Repository
in einer wiederverwendbaren Umgebung.

Die [aktuelle offizielle Codex-Anleitung](https://developers.openai.com/codex/environments/cloud-environments)
nennt **Settings → Codex Cloud → Environments → Create environment** (alternativ
**Work in → Cloud → Select environment → Create environment**). Dort:

1. Name etwa `Fly Exchange — Linux development`; Repository
   `manu-brighter/fly-connectome-sim` auswählen, GitHub verbinden, falls verlangt.
   **Get started** wählen. Den Branch `feat/connectome-experiment-core` ausdrücklich
   im Setup und vor jeder Fortsetzung prüfen; nicht auf main zurücksetzen.
2. Als **Install script**, aus dem Repository-Verzeichnis:

   ```sh
   bash scripts/cloud/setup.sh
   bash scripts/cloud/data.sh --download-and-prepare
   ```

   Das erste Skript installiert Werkzeuge/Abhängigkeiten und baut den Viewer;
   das zweite bereitet ausschließlich Daten vor. Compiler `c++`, `curl`, `tar`,
   `xz`, `sha256sum`, Git und GNU `timeout` müssen im Linux-Image vorhanden sein.
   Auf dieser Debian-13-Instanz waren sie vorhanden, kein Systempaket war nötig.
3. Als **Start skill** die Anweisungen aus
   [`scripts/cloud/START.md`](../scripts/cloud/START.md) übernehmen. Die Skripte
   werden nicht durch ein bloßes `export` in einer früheren Shell aktiviert.
4. Netzwerk: hier ist öffentlicher ausgehender HTTPS-Zugriff durch den Cloud-Proxy
   tatsächlich geprüft. Bei eingeschränkter Konfiguration Package managers erlauben,
   dazu `nodejs.org` und `storage.googleapis.com`; erforderlich sind außerdem
   `github.com`, `release-assets.githubusercontent.com`, `pypi.org`,
   `files.pythonhosted.org` und `registry.npmjs.org`. Proxy- und CA-Einstellungen
   beibehalten; `env.sh` setzt für Node-Fetch `NODE_USE_ENV_PROXY=1`.
   Für diese Arbeit sind **keine API-Schlüssel** erforderlich.
5. **Who can use: Only me**; Konfiguration/Setup-Bericht prüfen,
   **Save draft**, danach bei fertigem/ruhendem Setup **Publish** wählen.
   Erst die Meldung **Environment published** bestätigt die Veröffentlichung.
   Danach **Start a new task**, diese Umgebung wählen und Branch, Versionen,
   `verify-prepared` und einen Start/Stop erneut prüfen. Neue Plattforminstanzen
   und ein veröffentlichter Snapshot wurden hier nicht getestet.

**Aufbewahrung:** Laut obiger aktueller Anleitung ist der Zustand eines einzelnen
Tasks standardmäßig bis zu **sieben Tage nach dem letzten Turn/Resume**
wiederherstellbar. Zwei Wochen Untätigkeit sind damit nicht zugesichert.
Während der Reise regelmäßig fortsetzen und wichtige Änderungen auf dem
Feature-Branch sichern. Ein veröffentlichter vorbereiteter Snapshot plus diese
Skripte ermöglicht neue Tasks; er ersetzt keine Git-Sicherung. Rohdaten bleiben
ignoriert und können bei Verlust neu aus offiziellen Quellen vorbereitet werden.
Dies ist kein zwei Wochen durchgehend laufender Server.

## Exakte Start- und Wiederherstellungsbefehle

```sh
cd /workspace/fly-connectome-sim
git status --short --branch
git remote -v
git log -1 --format='%H %s'
source scripts/cloud/env.sh
uv --version                 # 0.12.15
.venv/bin/python --version    # 3.12.14
node --version               # v24.21.0
npm --version                # 11.19.0

# Synthetische Tafel, Vordergrund, nur Loopback; Stop mit Ctrl+C:
bash scripts/cloud/start.sh market
# Gleichwertig mit eigener Datenbank/Port:
bash scripts/cloud/start.sh market 8765 .tools/cloud/market/state.sqlite3

# Separat: Viewer für Entwicklung, Vordergrund, Stop mit Ctrl+C:
bash scripts/cloud/start.sh viewer 5173
```

Die Tafel verwendet bewusst **synthetische Testvorschläge**, keine Neuronendaten
und keine Verkaufspreise. Ihre beim Start ausgegebenen operator/view-Links sind
private Fähigkeiten: nicht in Chat, Git, Screenshots oder Logs kopieren.
Primäre Tafel übernehmen, ACK/anwesend abwarten, ausdrücklich **Fortsetzen**.
Jeder Neustart beginnt pausiert und erzeugt neue Rollenlinks. Dieselbe Datenbank
behält Preise; geänderte Getränke erhalten die volle 30-Minuten-Neustartsperre.
Lockdateien niemals zum Umgehen von Besitzprüfungen löschen.

Eine private Cloud-Portvorschau war in diesem Task nicht verfügbar. `localhost`
bezeichnet hier die Cloud-VM, nicht den Browser auf dem Handy. Die tatsächliche
UI-Prüfung erfolgte mit dem vorhandenen Chromium **innerhalb** der VM. Zum
interaktiven Anschauen unterwegs eine von Codex angebotene authentifizierte
Vorschau/Cloud-Desktop verwenden, falls verfügbar; keine öffentliche Weiterleitung
anlegen und nicht auf `0.0.0.0` umstellen. Die synthetische API prüft Loopback und
Origin/Host; ein externer Preview-Hostname ist damit nicht automatisch kompatibel.
Codebearbeitung und Tests benötigen keine solche Vorschau.

Frischer Checkout, falls ein Task verloren geht:

```sh
git clone --single-branch --branch feat/connectome-experiment-core \
  https://github.com/manu-brighter/fly-connectome-sim.git
cd fly-connectome-sim
bash scripts/cloud/setup.sh
bash scripts/cloud/data.sh --download-and-prepare
```

## Gemessene Umgebung und Installation

- Checkout anfangs sauber, origin korrekt, HEAD und Remote beide
  `123ea373463a254a89ce4ef1c02c52898ad0d57c`. Der ältere ausführbare Übergabestand
  `65601b5…` wurde nicht erzwungen; aktueller Feature-HEAD wurde bewahrt.
- Debian GNU/Linux **13.6**, x86_64, Kernel **6.18.57**.
  `nproc` meldet 5; das tatsächliche Cgroup-CPU-Budget ist **4 Kerne**
  (`cpu.max: 400000 100000`). RAM-Limit **17.179.869.184 Bytes = 16 GiB**,
  kein Swap. Vor Installation etwa 30 GiB frei auf 32-GB-Dateisystem.
- **Python 3.12.14**, uv **0.12.15**, Node **24.21.0**, npm **11.19.0**.
  Node bringt genau diese npm-Version mit. Vorinstallierte abweichende Versionen
  (uv 0.13.6, Node 24.22.1, npm 11.9.0) werden nicht für das Projekt verwendet.
- **GNU C++ 14.2.0**, Debian-Paketkennung `14.2.0-19`, `/usr/bin/c++`.
  C++17-Probe kompiliert/ausgeführt; echte kleine native Kompatibilität separat.
  Der Compiler war bereits installiert, seine Version wird nicht universell gepinnt.
- `uv sync --locked --extra test --extra media --python 3.12.14`;
  NumPy 2.4.6, pandas 3.0.5, Pillow 12.3.0, PyArrow 25.0.1,
  PyAV 19.0.2, pytest 9.1.1. Viewer mit `npm --prefix viewer ci`.
  Kein Lockfile-/Dependency-Upgrade. Preisservice: SQLite **3.53.1**,
  `clock_gettime(CLOCK_MONOTONIC)`, gemeldete Auflösung **1 ns**; das ist keine
  garantierte Scheduling- oder Netzwerk-Latenz.
- Offizielle Toolarchive SHA-256:
  uv Linux x86_64 `f97935763c04be3e692460a7aaeaaab8fc3b78fcf8b389da820b38ae7423a638`;
  Node Linux x64 `fd8e59d5a511510f6a298afb548f18c7d2b1be404d8b4a27d94fbe49f56cb2d6`.
  Setup prüft jeweils veröffentlichte Checksummen und tatsächliche Versionen.
- `bash scripts/cloud/setup.sh` nach der Erstinstallation erneut erfolgreich
  ausgeführt, einschließlich C++17-Probe, locked sync, npm ci, TypeScript und Build.
  Ein zweiter komplett leerer VM-Start ist damit nicht nachgewiesen. Nach
  Test-Cleanup sind rund **28 GiB frei**; kein Tafel-/Viewer-Dienst bleibt an.
- Cloud-Status: `observations_current=true`, Netzwerk `enforced`, Revision 1,
  keine konfigurierten Secrets/Identitäten, `source_config_id=null`,
  `source_config_version_id=null`. Desktop-Fähigkeit als enabled/unknown gemeldet;
  keine Desktop-Steuerwerkzeuge (`cua_repl.js`/`open_in_codex`) angeboten.
  Executor-ID dieser Prüfung:
  `ccarenv_b64_Y2NhcmVudl85MDc1OTUyYzMwN2M4MTkxYmI3ZjdkM2FlOWUzZDFjMw`.
  Kein veröffentlichter Snapshot behauptet.
- Native/Buffer melden denselben tatsächlich berechneten Linux/LF-Quellfingerprint
  (`model-source/v1`):
  `21198646722c414553f935885ea5ae303b3eb76eeca86eca2c73aa08c106626c`.
  Das ist eine Quellbyte-Identität, keine wissenschaftliche Qualifikation.

## Tests und tatsächliche Ergebnisse

```sh
bash scripts/cloud/check.sh all
# Oder einzeln: native | market_buffers | market_price | viewer
```

`check.sh` bildet die vier Gruppen aus `.github/workflows/compatibility.yml`
mit deren vollständiger Testauswahl ab (zusätzlich `-ra` für Skip-Gründe).
Jede Gruppe erhält einen frischen Quell-Export und eine eigene Installation.
Native und Buffer verwenden jeweils `.tools/ci/runtime`; Market Price verwendet
`.tools/ci/market-price/runtime`, jeweils vor Import vorhanden und **leer**.
`FLY_CONNECTOME_SIM_FULL_TEST`, `FLY_CONNECTOME_SIM_CXX`, `PYTHONPATH` und
`PYTHONHOME` sind leer; `UV_NO_CACHE=true`. Native/Buffer installieren test+media,
Price nur test, Viewer `npm ci`, `npm test`, `npm run build` (enthält
`tsc --noEmit`). Je Gruppe gelten dieselben 15 Minuten wie im Workflow.
Die vorbereiteten MaleCNS-Daten gelangen nicht in die Test-Exporte.

In dieser Sitzung verweigert die zusätzliche Agent-Kommando-Sandbox sowohl
den Proxyzugriff als auch lokale Sockets (`Operation not permitted`). Installation,
der abschließende Vier-Gruppen-Lauf sowie Browser-/Serverchecks wurden deshalb
mit der regulären freigegebenen Tool-Ausführung außerhalb dieser Sandbox
durchgeführt (`sandbox_permissions=require_escalated`); die Cloud-Netzwerkpolicy
und TLS-Prüfung bleiben aktiv. Bei späteren gleichartigen Fehlern denselben
Befehl über diesen vorgesehenen Freigabeweg ausführen, keine Schutzprüfung ändern.

| Gruppe | Ergebnis | Testlaufzeit | Begründete Skips |
| --- | --- | ---: | --- |
| Native/Session | **1469 bestanden**, 47 Skips | 720,50 s | 44 Windows-Lifecycle-/Job-/Zig-/Pfadfälle; drei fehlende historische Sessions |
| Market buffers | **253 bestanden**, sechs Skips | 346,74 s | sechs echte Windows-Prozess-/Frontend-Lifecycle-Fälle |
| Market price (`tests/market`) | **1042 bestanden**, 77 Skips | 187,67 s | Windows-Prozessbesitz/Handles, D2, isolierter Lib-Bootstrap und Windows-Pfadsemantik |
| Viewer | **336 bestanden**, vier Skips; TypeScript/Build Exit 0 | 87,83 s (Tests) | vier importierte Fälle ohne historische lokale Markdown-/Session-Artefakte |

Der gespeicherte Aufruf `bash scripts/cloud/check.sh all` endete mit **Exit 0**;
alle vier Gruppen sind PASS, insgesamt **3100 Passes / 134 Skips / null Fehler**.
Die 77 Market-Skips teilen sich in
14 Job-Ownership-, zwei isolierte Lib-Bootstrap-, sechs D2-Job-, drei optionale
D2-CLI-, einen Windows-Pfad-, 50 Job-/Handle- und einen nativen Bootstrap-Fall.
Sie belegen gerade keine Linux-Unterstützung für Decoder oder Live-Worker.
Lokale Rohlogs: `.tools/cloud/logs/check-20261112T221821Z.GyaTxB/`; sie sind ignoriert.
Der versionierte Bericht enthält die Ergebnisse.

Ein erster `npm --prefix viewer test` innerhalb des Agent-Sandboxprozesses
endete mit 28 erfolgreichen Dateigruppen und einer fehlgeschlagenen Dateigruppe
`prepare-demo.test.mjs` (100,20 s, keine konkrete Einzeltestdiagnose ausgegeben).
Dieser Lauf bleibt fehlgeschlagen; das Ergebnis des separaten frischen Exports
ersetzt ihn nicht rückwirkend. Ein gezielter anschließender Diagnoselauf außerhalb
der Sandbox besteht: 43 Passes, ein Skip wegen fehlender historischer lokaler
Dateien, 59,21 s:

```sh
source scripts/cloud/env.sh
node --test --test-reporter=tap viewer/tests/prepare-demo.test.mjs
```

Die Ursache des ersten Fehlers ist damit nicht nachgewiesen. Der vollständige
Viewer-Lauf im frischen Export besteht anschließend ebenfalls (siehe Tabelle).
TypeScript/Build separat erfolgreich,
bestehende Warnung: Three.js-Chunk größer als 500 kB.

Zusätzlicher tatsächlicher UI-/Lebenszykluscheck mit vorhandenem, getrenntem
Playwright **1.62.0** / Chromium **156.0.8078.79** der Cloud (keine neue
Projektabhängigkeit; diese beiden Werkzeuge sind Voraussetzung nur für den
optionalen Smokecheck und werden von `setup.sh` nicht installiert):

```sh
# Hier: das vorinstallierte python3 enthält Playwright, Chromium: /usr/bin/chromium
python3 scripts/cloud/smoke-market.py
```

Ergebnis **PASS**: gespeichertes `start.sh`, temporäre SQLite-Datenbank,
20 Getränke, Start pausiert, Claim/ACK/Resume, CHF4→7, `no_change`, `cooldown`,
Pause, read-only auf 390px ohne Horizontalüberlauf, Disconnection → unbekannt,
persistenter Preis nach Neustart, neue Rollenlinks und Neustartsperre,
SIGINT mit Exit 0 und geschlossenem Listener. Auch `start.sh viewer 5173` wurde
separat tatsächlich gestartet (HTTP 200) und per SIGINT-Prozessgruppe beendet;
der npm-Wrapper endete dabei mit -2, der Listener war geschlossen. Kein Dienst
bleibt absichtlich an.

## Verfügbare Daten und Provenienz

```sh
bash scripts/cloud/data.sh --download-and-prepare
source scripts/cloud/env.sh
.venv/bin/python -m fly_connectome_sim.data verify-prepared
```

Das gespeicherte Skript führt exakt Downloader, `verify-sources`, `stage`,
`neural.connectome malecns_v1`, `neural.prepare` und `verify-prepared` aus.
**Keine nachfolgende allgemeine pytest-/Fullgraph-Ausführung** aus dem längeren
Getting-started-Beispiel wurde automatisch gestartet.

Vor Aufbereitung: 27,77 GiB frei, 13,71 GiB verfügbarer RAM. Skript fordert
vorsichtig mindestens je 8 GiB; das ist eine Vorprüfung, keine Fullgraph-Kapazitäts-
oder Laufzeitqualifikation. Quelldownload exakt **1.109.008.094 Bytes**. Der
Importer verarbeitet 151.856.684 Quellenkanten zeilen-/batchweise; Vorbereitung
sortiert die 25.582.938 erhaltenen Kanten im RAM. Ressourcen dieser VM reichten.
Quellen plus generierte Daten belegen nach Abschluss rund **1,6 GiB** dank
Hardlinks (Quellen/Staging liegen auf demselben Dateisystem).

| Offizielle Datei | Bytes | SHA-256, erfolgreich geprüft |
| --- | ---: | --- |
| body-annotations-male-cns-v1.0-minconf-0.5.feather | 14483314 | `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2` |
| body-neurotransmitters-male-cns-v1.0.feather | 43282834 | `95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621` |
| connectome-weights-male-cns-v1.0-minconf-0.5.feather | 1051241946 | `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1` |

Downloader bestätigt außerdem Objektgeneration, Größe und MD5 aus dem Manifest.
Runtime: `data/malecns-v1.0/runtime/`, einschließlich `source.lock.json`,
`normalized/neurons.feather`, `normalized/edges.arrow`, `graph.npz`, Manifesten.
`verify-prepared`: **166.700 Neuronen / 25.582.938 gerichtete Kanten /
arrays_verified=true**, 124.177.617 erhaltene synaptische Kontakte.
Quellen-/Neuron-/Array-Locks und Lizenzhinweise bleiben unverändert. Daten,
Werkzeuge, Caches und venv sind nicht Bestandteil des Git-Commits.

## Konkreter Linux-Blocker für Bilder und nativen Live-Pilot

Tatsächliche Vorprüfung mit Python 3.12.14: Decoder-`_command` und
Native-CLI-`_check_platform` ergeben beide **`unsupported_platform`**.
Der öffentliche Native-Prepare-Aufruf endet **Exit 1 / prerequisite_failed**,
ohne Worker-/Engine-Start. Vorhandene Skip-Tests sind kein Linux-Nachweis.

- `market/image_decode_windows.py`: `ctypes.WinDLL(kernel32)`, Windows Jobs,
  Prozess-/Threadhandles, angehaltene Prozesserzeugung mit Job-Zuordnung,
  Handle-Vererbung, Pipe-Drain/EOF, Eigentümer- und Cleanup-Bestätigung.
- `scripts/market-image-decode-worker.py`: isolierter Bootstrap mit festem
  `.venv/Lib/site-packages` statt Linux-Pfad. Pillow-Verfügbarkeit allein löst
  weder Prozessbesitz noch Bootstrap-Prüfung.
- `market/native_windows.py`, `scripts/market_supervision.py`: Job-Commit-Quota,
  Prozessidentität, Compiler-Probe, IPC, Stop-/Owner-Death-/Cleanup-Receipts
  sind an Windows gebunden.
- `market/native_protocol.py`: Windows-Laufwerks-/ntpath-Validierung,
  `.venv/Scripts/python.exe`, `memory.dll`, Site-Packages, Windows-Environment
  und Zig-0.16.0-`version`-Probe sind feste Bindungen. Der allgemeine Linux-C++17-
  Kernel-Build ist dafür kein austauschbarer Worker-Transport.

Erforderlicher Umfang einer späteren Portierung: eigener geprüfter POSIX-
Prozessbesitz/Prozessbaum-Cleanup auch bei Owner-Death, begrenzte Pipe-/Probe-
Transporte und Ressourcenüberwachung/Quoten, sichere Pfad-/Interpreter-/Bibliotheks-
und Compiler-Bindungen, isolierter Linux-Decoder-Bootstrap sowie echte Linux-
Prozess-/Fehler-/Cancellation-Tests. Vor Nutzung danach ein separat beauftragter
endlicher integrierter Pilot. Schutzprüfungen erhalten; kein Entfernen von
Plattform-Gates, kein Ersatzsimulator. Diese Portierung ist hier nicht ausgeführt.

## Verbleibend

- Plattform-Umgebung wie oben speichern/veröffentlichen und in **neuem Task**
  Snapshot/Netzwerk/Start prüfen. Zwei Wochen Aufbewahrung nicht aus Default ableiten.
- Private interaktive Vorschau auf dem Handy ist noch nicht nachgewiesen.
- Linux-Portierung des Bild-/Live-Workers; danach separat begrenzte Abnahme.
  Mehrstunden-Generalprobe, Eventlast und öffentlicher Betrieb bleiben offen.
- Historische Windows-Aufzeichnungen, Filme, private Bilder und Checkpoints
  sind in diesem Cloud-Checkout **nicht vorhanden** und wurden nicht reproduziert.
  Keine neuen Fullgraph-Experimente, Trainingsläufe, bezahlten API-Aufrufe oder
  wissenschaftlichen Qualifikationsläufe wurden ausgeführt.
