# Live-Getränkebörse mit dem Fliegenmodell

Stand: 9. November 2026. **Konzeptentwurf zur Diskussion, noch kein freigegebener
Umsetzungsplan.** Die bisherige Beobachtungsdemo ist abgeschlossen. Dieser Entwurf
startet weder einen Simulationslauf noch API-Nutzung, Training oder Kassenzugriff.

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
- Zuerst das Konzept klären; danach den Umsetzungsplan erstellen.

Annahme für diesen Entwurf: Gemeint sind echte Verkaufspreise. Die erste
Erprobung würde trotzdem mit ausdrücklich unverbindlichen Testpreisen erfolgen.
Wie die Bar verbindliche Änderungen übernimmt und wer das betroffene Getränk
auswählt, ist noch offen; siehe die Produktentscheidungen unten.

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
6. Preiswechsel und Sperrende werden dauerhaft gespeichert und mit einer Version
   an Bar und Tafel verteilt. Die genaue Aktivierung hängt von der gewählten
   Übernahme an der Bar ab; ein fehlgeschlagener Übergang zählt nicht als Änderung.

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
Preisentscheid der Fliege. Ob die Bar Preise nur abliest oder ein Kassensystem
automatisch aktualisiert wird, ist noch nicht entschieden.

## Wie aus Aktivität eine Preisentscheidung wird

Die technische Zuordnung muss vor dem Event feststehen und nachvollziehbar sein.
Kein LLM, Zufallswert oder unterhaltungsabhängiger Ersatz entscheidet, falls die
neuronale Aktivität keine klare Entscheidung liefert.

Vorschlag für die Auslese:

- **Getränk:** Falls das Modell auch das Getränk wählen soll, konkurrieren feste
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

Ein Pilot muss Durchsatz, Verzögerung und Ressourcenverbrauch über die geplante
Eventdauer messen. Die Preis-Sperre verwendet reale Zeit, das neuronale Modell
seine tatsächlich berechnete Zeit. Langsame Verarbeitung darf weder als aktuelle
Reaktion ausgegeben werden noch unbegrenzt Uploads aufstauen. Gäste sehen
Warteschlangenstatus und Ablehnung bei voller Kapazität. Die endgültige maximale
Verzögerung und Kapazität werden vor der Eventfreigabe festgelegt.

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

## Noch offene Produktentscheidungen

Bereits zur Klärung gestellt:

1. Übernimmt das Personal Preise von der Tafel, oder sollen sie automatisch ins
   Kassensystem gehen? Davon hängt der verbindliche Aktivierungsablauf ab.
2. Wählt das Modell auch das Getränk, oder wählen Gäste es beim Upload?

Vor einer konkreten Eventkonfiguration ausserdem erforderlich: Getränkeliste,
Start-/Mindest-/Höchstpreise, Preiseinheit, Eventdauer und erwartete Uploadlast.
Diese Werte müssen nicht erfunden werden, um zuerst die technische Machbarkeit
zu planen. Eine zusätzliche globale Begrenzung zwischen Änderungen verschiedener
Getränke ist nur bei Bedarf eine weitere Produktentscheidung.

## Weg zum Umsetzungsplan

Nach Klärung des Konzepts wird ein sequenzieller Plan erstellt: zuerst Auslese und
Dauerbetrieb als begrenzte Machbarkeitsfragen, dann Preisverwaltung und Testtafel,
anschliessend Uploads/Live-Darstellung und Generalprobe. Lernen bleibt ein eigener,
später ausdrücklich gewählter Forschungsstrang. Neue aufwendige Messläufe werden
mit konkreten Grenzen geplant; dieser Entwurf autorisiert sie nicht.
