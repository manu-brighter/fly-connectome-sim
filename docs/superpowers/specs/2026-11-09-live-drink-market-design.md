# Live-Getränkebörse mit dem Fliegenmodell

Stand: 9. November 2026. **Etappenweise Umsetzung freigegeben und begonnen.**
Der Nutzer hat die manuelle Preisübernahme von der Tafel und die Getränkeauswahl
durch das Modell gewählt und anschliessend den Plan zur Umsetzung freigegeben.
Der zugehörige [Umsetzungsplan](../plans/2026-11-09-live-drink-market.md) beginnt
mit einer begrenzten Auswertung vorhandener Daten. Aktuell werden keine neuen
Simulationsläufe, API-Aufrufe oder Trainingsversuche durchgeführt.

## Ziel und bereits festgelegte Regeln

Während eines Events zeigt eine grosse Tafel das laufende Fliegenmodell,
gemessene neuronale Aktivität und verbindliche Getränkepreise. Gäste können Bilder
einsenden, die dem Modell als visuelle Eingaben vorgelegt werden. Eine vorab
festgelegte technische Übersetzung der Aktivität erzeugt Preisvorschläge.

Vom Nutzer festgelegt:

- Für jedes Getränk gibt es einen erlaubten Mindest- und Höchstpreis.
- Ein Sprung über den gesamten Bereich ist erlaubt, beispielsweise CHF 4 direkt
  auf CHF 7. **Keine Begrenzung auf 50 Rappen pro Änderung.**
- Zwischen zwei tatsächlichen Preisänderungen desselben Getränks liegen
  mindestens **30 Minuten realer Zeit**.
- Innerhalb der Regeln soll das Modell Zeitpunkt, Häufigkeit und Ausmass
  bestimmen. Die Regeln schreiben keine regelmässigen Änderungen vor.
- Das Modell bestimmt auch das betroffene Getränk. Gäste laden Bilder für die
  gesamte Getränketafel hoch und wählen beim Upload kein Getränk aus.
- Das Personal übernimmt die gültigen Preise von der Preistafel. Für den ersten
  Pilot gibt es keine automatische Kassenschnittstelle.
- Lange Ruhephasen und klare Getränkefavoriten sind für den experimentellen Pilot
  akzeptiert. Alle konfigurierten Getränke müssen technisch auswählbar bleiben;
  sie müssen nicht alle in einer endlichen Testaufnahme tatsächlich vorkommen.
  Technische Erreichbarkeit und beobachtete Auswahl werden getrennt ausgewiesen.
- Zuerst das Konzept klären; danach den Umsetzungsplan erstellen.

Vom Nutzer ergänzte Betriebsgrösse: gewöhnlich **10–20 Getränke**, **50–300 Gäste**
und **6–8 Stunden**, gelegentlich deutlich kürzer oder ungefähr **12 Stunden**.
Die Eventdauer bleibt konfigurierbar. Zwölf Stunden dienen als erste Referenz
für die spätere Langzeitprüfung, nicht als automatische Abschaltgrenze.
Gästezahl allein legt weder Uploadrate noch akzeptable Wartezeit fest.

Ziel sind echte Verkaufspreise. Vorgeschlagen ist eine erste Erprobung mit
ausdrücklich unverbindlichen Testpreisen vor dem Verkaufseinsatz. Der folgende
Aktivierungsablauf konkretisiert die manuelle Preisübernahme als technische
Planungsentscheidung; er verlangt keine Bestätigung jedes Vorschlags.

## Empfehlung für die erste Version

**Laufende neuronale Reaktionen ohne neues Training.** Bilder und der bisherige
Modellzustand beeinflussen gemessene Aktivität. Eine feste, versionierte
Ausleseregel übersetzt diese in Entscheidungen. Das ist weder ein Zufallsgenerator
noch ein Nachweis von Lernen oder einem Verständnis von Getränken und Preisen.

Das Projekt besitzt bereits einen laufenden Zustand, visuelle Eingaben,
Motor-Auslese, Messdaten und eine Darstellung. Weiterverwendet werden diese
Bestandteile und der bestehende Python/C++-Kern. Ergänzt wird eine getrennte
Event-Anwendung im selben Repository: Uploads, Warteschlange, Live-Daten,
Preisverwaltung und Bar-Bedienung. Ein zweiter Simulator oder ein Projekt-Fork
ist dafür nicht erforderlich. Die bisherige Replay-Demo bleibt separat nutzbar.

Der Preisweg benötigt kein LLM und keine bezahlten LLM-Aufrufe. Ein späterer
optionaler Dienst für beispielsweise Bildmoderation wäre separat zu entscheiden.

## Ablauf für Gäste, Modell und Bar

1. Ein Gast öffnet die Upload-Seite per QR-Code und sendet ein Bild.
2. Nach Dateiprüfung und der festgelegten Freigabe gelangt es in eine begrenzte
   Warteschlange. Abgewiesene oder überzählige Uploads kommen nicht in den Lauf.
3. Genau ein Bild wird nach einem festen Darbietungsprotokoll verarbeitet.
   Der Zustand wird zwischen Bildern nicht zurückgesetzt. Die Tafel zeigt das
   tatsächlich verarbeitete Bild und den zugehörigen Messzeitpunkt.
4. Die Auslese kann ein neues Entscheidungsereignis melden: Getränk und Zielpreis.
   Auch keine Entscheidung ist ein gültiges Ergebnis.
5. Eine unabhängige Preisverwaltung prüft Freigabe, Signalalter, erlaubten Bereich,
   Rundung und die Sperre dieses Getränks. Nur ein zulässiger Vorschlag kann einen
   verbindlichen Preiswechsel auslösen.
6. Die Preisverwaltung aktiviert eine neue Preisversion dauerhaft und
   veröffentlicht sie auf der verbindlichen Tafel. Der serverseitige
   Aktivierungszeitpunkt startet die Sperre. Die Bar übernimmt diesen Preis;
   ein nicht gespeicherter Vorschlag ist noch keine gültige Änderung.

Die Upload-Reihenfolge und Bilddauer sind Betriebsregeln, keine neuronalen
Entscheidungen. Ein Upload garantiert weder eine Preissenkung noch überhaupt eine
Preisänderung. Auch ohne neue Uploads muss ein definierter neutraler visueller
Input verarbeitet werden; Schwarzintervalle überspringen die Modellzeit nicht.

## Verbindlicher Preiszustand

Pro Getränk werden ID, Name, Startpreis, Minimum, Maximum, zulässige Preiseinheit,
aktueller Preis, letzte Aktivierung und frühester nächster Änderungszeitpunkt
gespeichert. Geldbeträge werden intern als ganze Rappen geführt. Die Preiseinheit
ist eine Rundungsvorgabe, keine Begrenzung der Sprunghöhe; ihre konkrete Grösse
wird mit der Getränkeliste festgelegt.

Beispiel: Ein Getränk wechselt um 20:12 von CHF 4 auf CHF 7. Vor 20:42 darf es
nicht erneut wechseln. Um 20:42 wird es nur wieder freigegeben. Ohne neues
Entscheidungsereignis bleibt es bei CHF 7. Andere Getränke haben eigene Sperren.

Vorgeschlagene genaue Regeln:

- Der erste vom Modell ausgelöste Wechsel ist nach dem ausdrücklichen Start des
  Marktbetriebs möglich. Das Einrichten des Startpreises löst keine Sperre aus.
- Die Sperre beginnt mit der verbindlichen Aktivierung des neuen Verkaufspreises,
  nicht mit Upload, Messung oder einem noch unverbindlichen Vorschlag.
- Ein Vorschlag für den bereits geltenden, gerundeten Preis ist keine Änderung
  und verlängert keine Sperre.
- Gesperrte Vorschläge werden verworfen. Keine Warteliste von Preisänderungen,
  kein Nachholen und keine Weiterleitung an ein anderes Getränk.
- Ein anhaltendes Signal wird nicht nach jeder Sperre automatisch erneut benutzt.
  Für einen weiteren Vorschlag muss sich die Auslese nach ihrer festen
  Rücksetzregel erneut aktivieren.
- Ein Entscheidungsereignis betrifft höchstens ein Getränk. Verschiedene Getränke
  könnten dennoch kurz nacheinander wechseln. Die 30-Minuten-Regel pro Getränk
  verhindert das nicht; eine zusätzliche globale Sperre ist bisher nicht vereinbart.
- Neustart, Wiederverbindung und doppelte Zustellung dürfen die Sperre nicht
  zurücksetzen oder dieselbe Änderung zweimal ausführen. Bei unklarer Uhrzeit
  wird kein neuer Wechsel aktiviert.
- Die Preisverwaltung ist die einzige Quelle gültiger Preise. Ein Kandidat aus
  der Simulation, eine Animation oder eine verspätete Tafel darf diese nicht
  eigenständig überschreiben.
- Bei Fehlern, veralteten Messwerten oder manueller Pause bleiben die letzten
  gültigen Preise bestehen. Nach Wiederanlauf braucht es frische Signale.
- Bereichsänderungen während eines laufenden Events werden nicht still angewandt.
  Dafür wird der Markt pausiert und die neue Konfiguration ausdrücklich aktiviert.

Die Bar erhält Pause/Fortsetzen, die gültige Preistafel und den Status ihrer
Verbindung. Ein manueller Notbetrieb wird als solcher ausgewiesen und ist kein
Preisentscheid der Fliege. Für den ersten Pilot wird möglichst dieselbe Tafel
für Bar und Publikum verwendet. Die Preisverwaltung aktiviert zulässige
Modellentscheidungen automatisch; das Personal bestätigt nicht jeden Wechsel.
Das tatsächliche Abrechnen zum angezeigten Preis bleibt Aufgabe der Bar.

Aktivierungen benötigen eine frische Verbindung zur primären Tafel. Die spätere
Service-Spezifikation legt Heartbeat und Erkennungsschwelle fest. Verbindungsausfall
sperrt weitere Aktivierungen nach seiner Erkennung; eine Netztrennung lässt sich
nicht augenblicklich oder durch blosses Absenden einer Nachricht ausschliessen.
Ein abgetrennter Bildschirm zeigt seine letzte Version mit Zeitstempel und einer
deutlichen Warnung, dass der aktuelle Stand unbekannt ist. Er kann eine bereits
verbindlich gespeicherte Änderung verpasst haben. Diese wird nicht zurückgerollt.
Nach Wiederverbindung wird der vollständige aktuelle Preisstand geladen; es gibt
keine Behauptung, dass mehrere Displays oder eine manuelle Kasse atomar wechseln.

## Wie aus Aktivität eine Preisentscheidung wird

Die technische Zuordnung muss vor dem Event feststehen und nachvollziehbar sein.
Kein LLM, Zufallswert oder unterhaltungsabhängiger Ersatz entscheidet, falls die
neuronale Aktivität keine klare Entscheidung liefert.

Vorschlag für die Auslese:

- **Getränk:** Für die gewählte Getränkeauswahl durch das Modell konkurrieren feste
  Auslesekanäle. Nur ein hinreichend starker und eindeutiger Gewinner liefert eine
  Auswahl. Die Zuordnung von Kanal zu Getränk ist technisch festgelegt; sie
  bedeutet nicht, dass diese Zellen ein Getränk erkennen.
- **Zielpreis:** Ein signiertes, normalisiertes Aktivitätssignal wird mit einer
  festen Kennlinie auf den ganzen Preisbereich des ausgewählten Getränks
  abgebildet. Die Endpunkte müssen erreichbar sein. Kleine oder unklare Signale
  dürfen ausdrücklich zu keiner Änderung führen.
- **Zeitpunkt:** Ein neues Schwellenereignis mit fester Rücksetzregel erzeugt den
  Vorschlag. Regelmässige Messfenster dienen der Auswertung, nicht einem festen
  Preisfahrplan. Zwischen tatsächlichen Änderungen darf beliebig lange Ruhe sein.

**Noch nicht nachgewiesen:** Die heutige Links-/Rechts-Motorauslese liefert nicht
automatisch mehrere brauchbare Getränkekanäle und eine unabhängige Preisstärke.
Konkrete Zellgruppen, Fenster, Normalisierung, Schwellen und Kennlinie sind daher
eine offene technische Machbarkeitsprüfung. Vor einem Verkaufseinsatz müssen
Bildempfindlichkeit, Kanalvielfalt, Neutralrate und Extrempreise gemessen werden.
Eine dauerhafte Seiten- oder Kanalvorliebe darf nicht als Getränkegeschmack
vermarktet oder durch verdeckte Zufallswahl kaschiert werden.

Kalibrierung und Überprüfung werden getrennt: Parameter zunächst anhand
deklarierter Kalibrierungsdaten bestimmen, dann einfrieren und an anderen Bildern
prüfen. Wenn die Auslese ungeeignet ist, wird das als offenes Ergebnis berichtet;
das Konzept verspricht noch keine funktionierende Mehrgetränkesteuerung.

## Lernvarianten und Empfehlung

| Variante | Konkrete Idee | Empfehlung |
| --- | --- | --- |
| Reaktionen ohne Training | Bilder beeinflussen den fortlaufenden Zustand; feste Auslese erzeugt Preisvorschläge. | Erste Eventversion. Weniger unbekannte Faktoren, Wirkung direkt untersuchbar. |
| Kontrolliertes Training vor dem Event | Zwei klar definierte visuelle Muster werden in einem separaten Versuch unterschiedlich mit einem festgelegten Verstärkungssignal gekoppelt. Danach ohne dieses Signal testen. | Sinnvoller nächster Forschungsschritt, wenn der Lerneffekt selbst Teil des Projekts werden soll. |
| Lernen während des Events | Ein explizites Rückmeldesignal verändert die Modellparameter während des Betriebs. | Zunächst nur getrennt und ohne Autorität über Verkaufspreise untersuchen. |

**Mein bevorzugtes Lernexperiment:** Zuerst einfache Muster A und B statt
beliebiger Fotos oder Getränkebegriffe verwenden. Prüfen, ob die erklärte
Plastizitätsregel nach unterschiedlicher Kopplung eine anhaltende, musterspezifische
Änderung des vorab festgelegten neuronalen Messwerts erzeugt. Untrainierte,
ungepaarte und gefrorene Kontrollen sowie vertauschte Zuordnungen helfen,
Bildunterschiede und blosse Zustandsnachwirkungen vom Kandidaten-Lerneffekt zu
trennen. Erst danach wäre zu prüfen, ob diese Änderung auch die Preis-Auslese
zuverlässig beeinflusst.

Eine mögliche spätere Publikumsvariante wäre eine getrennte visuelle Aufgabe mit
vorher festgelegter richtiger Antwort. Feedback wird an die Antwort in dieser
Aufgabe gebunden, nicht an die Höhe eines Getränkepreises. Das vermeidet, dass
Gäste einfach jede Preissenkung belohnen und dadurch einen Rabattknopf bedienen.
Ob der aktuelle Kern dieses Ziel überhaupt lernen kann, ist offen.

Für eine erste Lernversion ungeeignet sind Likes für günstige Preise, Uploadzahl,
Umsatz oder konsumierte Getränkemengen als unbesehenes Belohnungssignal: Das Ziel
wäre unklar oder leicht manipulierbar, und der beobachtete Effekt schwer zuzuordnen.
Beliebige hochgeladene Bilder sind allein noch keine Lerndaten; es fehlen ein
definiertes Lernziel, das Verstärkungssignal und ein belastbarer Nachweis.

Der vorhandene Forschungsansatz prüft eine erklärte PPL101-modulierte
KC→MBON11-Plastizität. Er ist noch unqualifiziert und wird durch dieses Konzept
nicht wieder gestartet. Sein primärer Endpunkt belegt weder Getränkeerkennung
noch gelernte Preis- oder Motorsteuerung. `learning=False` unterbindet den neuen
plastischen Lernantrieb, setzt aber den laufenden Zustand nicht zurück und
schaltet normalen passiven Zerfall vorhandener Gedächtnisvariablen nicht ab.

Die zugrunde liegende [Arbeit von Huang, Luo et al. (2024)](https://www.nature.com/articles/s41586-024-07819-w)
untersucht Geruchskonditionierung und Gedächtnisdynamik. Sie ist keine Validierung
unserer visuellen Eingaben, Übertragung auf MaleCNS oder Preiszuordnung.

## Darstellung und ehrliches Live-Verhalten

Die Haupttafel zeigt gültige Preise, letzte Änderungen und den Zeitpunkt, ab dem
ein Getränk frühestens wieder geändert werden darf. Eine separate Aktivitätsansicht
zeigt das aktuell verarbeitete Bild, gemessene Zell-/Populationsaktivität sowie
das Ergebnis: keine Entscheidung, durch Sperre verworfen oder Preis aktiviert.
Es gibt keinen Countdown, der einen zwingenden nächsten Preiswechsel verspricht.

Neuronale Aktivität kann auch zwischen Preisänderungen sichtbar bleiben. Die
Darstellung behauptet aber keine Reaktion auf jedes Bild und keine gemessene
Signalübertragung entlang jeder gezeichneten Verbindung. Animierte Fliege,
statische Anatomie und tatsächlich gemessene Aktivität bleiben unterscheidbar.

**Laufende Berechnung ist nicht automatisch Berechnung in Echtzeit.** Der
[bisherige 9-Sekunden-Lauf](../../experiments/2026-11-08-cell-capture-api.md)
brauchte rund 109 Sekunden insgesamt. Die gespeicherten Ereignisse dieses Laufs
summieren rund 70 Sekunden Kernberechnung. Das Problem besteht also nicht nur
aus Startzeit; ein dauerhaft laufender Prozess allein garantiert keine Echtzeit.
Diese Werte betreffen den damaligen Aufbau und sind kein neuer Benchmark.

Der Nutzer hat nach der begrenzten Messung vom 9. November ausdrücklich akzeptiert,
dass der erste lokale Pilot langsamer als Echtzeit rechnet. Die Anzeige kennzeichnet
Modellzeit und aktuelle beziehungsweise wartende Eingaben. Die Preissperre bleibt
bei 30 echten Minuten. Diese Entscheidung ersetzt keine Messung von Durchsatz,
Warteschlangenkapazität oder tatsächlicher Verzögerung. Der Nutzer hat anschließend
höchstens **fünf reale Minuten Wartezeit** vom angenommenen Bild bis zur Übergabe
an die Simulation festgelegt. Bei voller begrenzter Warteschlange werden weitere
Uploads abgewiesen. Abgelaufene Einträge werden ausdrücklich verworfen und nicht
verspätet gezeigt; ein ausgefallener Worker kann keine erfolgreiche Übergabe garantieren.

Ein Pilot muss Durchsatz, Verzögerung und Ressourcenverbrauch über die geplante
Eventdauer messen. Die Preis-Sperre verwendet reale Zeit, das neuronale Modell
seine tatsächlich berechnete Zeit. Langsame Verarbeitung darf weder als aktuelle
Reaktion ausgegeben werden noch unbegrenzt Uploads aufstauen. Gäste sehen
Warteschlangenstatus, Ablauf und Ablehnung bei voller Kapazität. Die feste Kapazität
und die Einhaltung der Fünf-Minuten-Grenze werden vor der Eventfreigabe überprüft.

## Grenzen vor einem öffentlichen Einsatz

- Uploads: erlaubte Bildformate, Byte-/Pixelgrenzen, sichere Dekodierung,
  Mengenbegrenzung, befristete Speicherung und festgelegte Freigabe vor Anzeige.
- Betrieb: dauerhaft begrenzte Warteschlangen, Beobachtungsdaten und Logs;
  Ausfälle halten gültige Preise, ohne Ereignisse später nachzuholen.
- Nachvollziehbarkeit: Konfiguration und Ausleseversion, Bildbezug,
  Modell-/Messzeiten, Vorschlag, Ablehnungsgrund und aktivierte Preisversion.
- Funktion: voller erlaubter Sprung, unabhängige 30-Minuten-Sperren, keine
  Doppeländerung bei Wiederholung/Neustart, verständliche Pausenanzeige.
- Wirkung: gleiche Ausgangszustände mit Bild versus Schwarz, kontrollierte
  Layout-/Helligkeitsänderungen, Wiederholungen und andere Bildreihenfolgen.
  Bildempfindlichkeit allein belegt keine semantische Auswahl und kein Lernen.
- Belastbarkeit: Generalprobe ohne Verkauf über die vorgesehene Dauer und Last;
  danach erst ein begrenzter Bar-Pilot. Eine Kassenschnittstelle ist eine
  zusätzliche Integration und braucht eigene Fehler-/Abgleichstests.

## Eventkonfiguration vor einem Verkaufspilot

Vor einer konkreten Eventkonfiguration erforderlich: Getränkeliste,
Start-/Mindest-/Höchstpreise, Preiseinheit, Eventdauer und erwartete Uploadlast.
Diese Werte müssen nicht erfunden werden, um zuerst die technische Machbarkeit
zu planen. Eine zusätzliche globale Begrenzung zwischen Änderungen verschiedener
Getränke ist nur bei Bedarf eine weitere Produktentscheidung.

## Weg zum Umsetzungsplan

Der [sequenzielle Plan](../plans/2026-11-09-live-drink-market.md) konkretisiert
zuerst eine reine Bestandsauswertung und beschreibt die weiteren Etappen samt
Übergangskriterien. Die vorhandene Sekundenaufnahme kann einen mehrstündigen
Eventbetrieb nicht qualifizieren. Lernen bleibt ein eigener, später ausdrücklich
gewählter Forschungsstrang. Neue aufwendige Messläufe benötigen ein geprüftes
Protokoll mit konkreten Grenzen; dieser Entwurf autorisiert sie nicht.
