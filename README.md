# Kachelmannwetter für Home Assistant

Inoffizielle Custom Integration für die [Kachelmannwetter-API (v02)](https://api.kachelmannwetter.com/v02/_doc.html) von Meteologix AG / Kachelmann Gruppe. Nicht mit dem Anbieter verbunden.

## Voraussetzungen

1. Ein **Plus-Abo** bei kachelmannwetter.com (oder ein anderes API-fähiges Abo von Meteologix).
2. Ein **API-Key** unter *accounts.meteologix.com → Abos → „API-Keys verwalten“*.
3. Mindestens ein **API-Standort** unter *„API-Standorte verwalten“*. Im Hobby-Tarif sind zwei Standorte möglich. Die Koordinaten, die du in Home Assistant einträgst, müssen zu diesem Standort passen, sonst antwortet die API mit 403.

## Installation über HACS

1. HACS öffnen → Menü (drei Punkte) → **Benutzerdefinierte Repositories**.
2. Repository-URL eintragen, Kategorie **Integration**.
3. „Kachelmannwetter“ installieren und Home Assistant neu starten.
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Kachelmannwetter**.
5. API-Key, Name und Koordinaten eintragen. Der Key wird nur in Home Assistant gespeichert.

Manuell: Ordner `custom_components/kachelmannwetter` nach `config/custom_components/` kopieren.

## Was die Integration liefert

**Wetter-Entität** (`weather.<name>`)
- Aktuelle Werte: Temperatur, Taupunkt, Luftdruck, Luftfeuchte, Wind, Böen, Windrichtung, Bewölkung, Zustand
- Stündliche Vorhersage (24 h)
- Tägliche Vorhersage (14-Tage-Trend)

**Sensoren**
- Taupunkt, Windböen, Bewölkung, Niederschlag 1 h, Schneehöhe
- Regenvorhersage: Niederschlag nächste 3 h, Niederschlag nächste 24 h, Zeitpunkt des nächsten Regens, Regenwahrscheinlichkeit heute

Es gibt bewusst keine Warnungen und kein Minuten-Regenradar: Die öffentliche API bietet dafür keinen Endpunkt. Die Regenvorhersage basiert auf der stündlichen Modellvorhersage.

## Update-Intervall und Request-Budget

Standard sind 15 Minuten. Pro Update werden 2 Requests gesendet (aktuell + stündlich), der 14-Tage-Trend nur alle 3 Stunden. Das sind ca. **200 Requests pro Tag und Standort** bei einem Limit von 700 im Hobby-Tarif. Das Intervall lässt sich unter *Konfigurieren* ändern (5 bis 120 Minuten).

## Fehlersuche

| Meldung | Ursache |
|---|---|
| Ungültiger API-Key (401) | Key falsch oder abgelaufen. Home Assistant startet automatisch die Neuanmeldung. |
| Standort nicht hinterlegt (403) | Koordinaten stimmen nicht mit einem API-Standort im Konto überein. |
| Tageslimit erreicht (429) | Update-Intervall erhöhen. |
