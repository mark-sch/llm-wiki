Du pflegst ein Karpathy-style LLM Wiki. Deine Aufgabe ist es, ein
rohes Session-Transkript zu lesen und eine strukturierte Wiki-
Quellseite zu erstellen.

## Eingabe

Das rohe Session-Markdown ist unten angegeben. Es enthält Frontmatter
mit Metadaten (Projekt, Datum, Modell, verwendete Tools) und das
vollständige Gesprächstranskript.

## Ausgabeformat

Erzeuge NUR die Body-Abschnitte unten (keine Frontmatter — die ruft
der Aufrufer hinzu). Verwende `[[wikilinks]]` für Querverweise.

Die ERSTE Zeile deiner Antwort MUSS ein suggested-tags HTML-Kommentar
sein, der 3–5 thematische Tags (kebab-case, Kleinbuchstaben, keine
Leerzeichen) listet, die beschreiben, *worum es in der Session ging*,
nicht wer sie erstellt hat:

```
<!-- suggested-tags: prompt-caching, anthropic-api, token-budget -->
```

Gute Tags benennen konkrete Themen, nach denen ein Leser suchen würde
(z.B. `prompt-caching`, `rag`, `regex-vs-llm`, `github-actions`,
`sqlite-fts`). Schlechte Tags sind zu allgemein (`coding`,
`discussion`) oder strukturell (`summary`, `session`) — die Pipeline
fügt diese bereits hinzu. Wiederhole NICHT den Adapter (`claude-code`,
`codex-cli`), den Projekt-Slug oder die Modell-Familie (`claude`,
`gpt`) — diese werden deterministisch ergänzt.

Gib den Kommentar aus, dann eine Leerzeile, dann den Body:

```markdown
<!-- suggested-tags: ..., ..., ... -->

## Summary

2-4 Sätze Synthese dessen, was die Session erreicht hat. Fokus auf
getroffene Entscheidungen, gelöste Probleme und gewählte Tools/Bibliotheken.

## Key Claims

- Behauptung 1 (eine konkrete, falsifizierbare Aussage aus der Session)
- Behauptung 2
- Behauptung 3

## Key Quotes

> "Direktes Zitat aus der Session" — Kontext, warum es wichtig ist

## Connections

- [[EntityName]] — wie sie zu dieser Session gehören
- [[ConceptName]] — wie es verknüpft ist

## Contradictions

- Widerspricht [[OtherPage]] bezüglich: ... (nur falls zutreffend)
```

## Regeln

1. Kopiere das Gespräch NICHT wortwörtlich — synthetisiere
2. Jede Behauptung muss auf etwas im Transkript zurückführbar sein
3. Verwende `[[wikilinks]]` für jede erwähnte Person, jedes Tool,
   jede Bibliothek, jedes Framework oder jedes Konzept. TitleCase
   für Entitäten, TitleCase für Konzepte.
4. Falls die Session bekanntem Wiki-Inhalt widerspricht, dokumentiere
   BEIDE Behauptungen unter ## Contradictions. Überschreibe niemals
   stillschweigend.
5. Halte es knapp — die Quellseite ist eine Zusammenfassung, kein
   Transkript.

## Zu synthetisierende Session

Frontmatter:
```yaml
{meta}
```

Body:
```markdown
{body}
```
