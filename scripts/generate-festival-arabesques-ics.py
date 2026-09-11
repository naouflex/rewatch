#!/usr/bin/env python3
"""Generate Festival Arabesques 2026 ICS with per-event Google Calendar colors."""

from __future__ import annotations

import hashlib
import random
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "festival-arabesques-2026.ics"

# Google Calendar event colorId -> (name, RFC 7986 CSS3 color, hex)
GOOGLE_COLORS = {
    "1": ("Lavender", "mediumpurple", "#7986CB"),
    "2": ("Sage", "mediumseagreen", "#33B679"),
    "3": ("Grape", "purple", "#8E24AA"),
    "4": ("Flamingo", "salmon", "#E67C73"),
    "5": ("Banana", "gold", "#F6BF26"),
    "6": ("Tangerine", "darkorange", "#F4511E"),
    "7": ("Peacock", "deepskyblue", "#039BE5"),
    "8": ("Graphite", "gray", "#616161"),
    "9": ("Blueberry", "mediumslateblue", "#3F51B5"),
    "10": ("Basil", "seagreen", "#0B8043"),
    "11": ("Tomato", "tomato", "#D50000"),
}

EVENTS = [
    {
        "uid": "arabesques-2026-festival@festivalarabesques.fr",
        "start": ("DATE", "20260908"),
        "end": ("DATE", "20260921"),
        "summary": "Festival Arabesques 2026",
        "location": "Montpellier, France",
        "description": (
            "21e édition du Festival Arabesques — le plus grand rendez-vous des arts "
            "du monde arabe en Europe. Du 8 au 20 septembre 2026 à Montpellier.\n\n"
            "Lieux : Opéra Comédie, Domaine d'O, Halle Tropisme\n\n"
            "Site : https://www.festivalarabesques.fr/"
        ),
    },
    {
        "uid": "arabesques-2026-oum@festivalarabesques.fr",
        "start": ("TZ", "20260908T200000"),
        "end": ("TZ", "20260908T213000"),
        "summary": "Oum — Concert d'ouverture",
        "location": "Opéra Comédie / Salle Molière, 14 Rue de la République, 34000 Montpellier",
        "description": "Concert d'ouverture du Festival Arabesques 2026. La vocaliste marocaine Oum ouvre la 21e édition.",
    },
    {
        "uid": "arabesques-2026-bachar@festivalarabesques.fr",
        "start": ("TZ", "20260909T200000"),
        "end": ("TZ", "20260909T213000"),
        "summary": "Bachar Mar-Khalifé joue Christophe",
        "location": "Opéra Comédie / Salle Molière, 14 Rue de la République, 34000 Montpellier",
        "description": "Hommage émouvant à l'artiste Christophe par le musicien franco-libanais Bachar Mar-Khalifé.",
    },
    {
        "uid": "arabesques-2026-imarhan@festivalarabesques.fr",
        "start": ("TZ", "20260911T193000"),
        "end": ("TZ", "20260911T210000"),
        "summary": "Imarhan",
        "location": "Théâtre Jean-Claude Carrière, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Rock touareg — emblème de la nouvelle génération du blues tamasheq.",
    },
    {
        "uid": "arabesques-2026-anouar@festivalarabesques.fr",
        "start": ("TZ", "20260911T213000"),
        "end": ("TZ", "20260911T230000"),
        "summary": "Anouar Brahem Quartet",
        "location": "Amphi d'O, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Le maître oudiste tunisien Anouar Brahem et son quartet de jazz.",
    },
    {
        "uid": "arabesques-2026-jihad-sat@festivalarabesques.fr",
        "start": ("TZ", "20260912T143000"),
        "end": ("TZ", "20260912T154500"),
        "summary": "Jihad Darwiche — Contes",
        "location": "Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Contes et histoires par Jihad Darwiche.",
    },
    {
        "uid": "arabesques-2026-antidote@festivalarabesques.fr",
        "start": ("TZ", "20260912T163000"),
        "end": ("TZ", "20260912T174500"),
        "summary": "L'Antidote — Bijan Chemirani, Redi Hasa & Rami Khalifé",
        "location": "Théâtre Jean-Claude Carrière, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "World jazz — Bijan Chemirani (zarb), Redi Hasa (violoncelle) et Rami Khalifé (piano). Durée : 1h15.",
    },
    {
        "uid": "arabesques-2026-zar@festivalarabesques.fr",
        "start": ("TZ", "20260912T193000"),
        "end": ("TZ", "20260912T210000"),
        "summary": "Zar Electrik + Temenik Electric",
        "location": "Théâtre Jean-Claude Carrière, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Performance hybride entre traditions et modernité.",
    },
    {
        "uid": "arabesques-2026-sahravane@festivalarabesques.fr",
        "start": ("TZ", "20260912T213000"),
        "end": ("TZ", "20260912T230000"),
        "summary": "Sahravane : Souad Asla, Omar Sosa & Lemma",
        "location": "Amphi d'O, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Un pont entre le Sahara et Cuba — chants du sud algérien et traditions afro-caribéennes.",
    },
    {
        "uid": "arabesques-2026-jihad-sun@festivalarabesques.fr",
        "start": ("TZ", "20260913T143000"),
        "end": ("TZ", "20260913T154500"),
        "summary": "Jihad Darwiche — Contes",
        "location": "Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Contes et histoires par Jihad Darwiche. Rencontres littéraires en hommage à Driss Chraïbi.",
    },
    {
        "uid": "arabesques-2026-meryem@festivalarabesques.fr",
        "start": ("TZ", "20260913T163000"),
        "end": ("TZ", "20260913T174500"),
        "summary": "Meryem Aboulouafa",
        "location": "Théâtre Jean-Claude Carrière, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Pop et musiques du monde — auteure-compositrice-interprète de Casablanca.",
    },
    {
        "uid": "arabesques-2026-amine@festivalarabesques.fr",
        "start": ("TZ", "20260913T170000"),
        "end": ("TZ", "20260913T181500"),
        "summary": "Amine Radi — Stand-up",
        "location": "Amphi d'O, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "One-man show — humour franc par l'humoriste Amine Radi.",
    },
    {
        "uid": "arabesques-2026-daoud@festivalarabesques.fr",
        "start": ("TZ", "20260913T193000"),
        "end": ("TZ", "20260913T210000"),
        "summary": "Daoud",
        "location": "Théâtre Jean-Claude Carrière, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Jazz — le trompettiste Daoud.",
    },
    {
        "uid": "arabesques-2026-zina@festivalarabesques.fr",
        "start": ("TZ", "20260913T210000"),
        "end": ("TZ", "20260913T223000"),
        "summary": "Zina Daoudia",
        "location": "Amphi d'O, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Concert de musiques du monde.",
    },
    {
        "uid": "arabesques-2026-soundsystem@festivalarabesques.fr",
        "start": ("TZ", "20260917T193000"),
        "end": ("TZ", "20260918T004500"),
        "summary": "Arabesques Sound System — 100% Féminin : Kbira + Yasmina Karrum + La Louuve",
        "location": "Halle Tropisme, Montpellier",
        "description": "Soirée DJ set 100% féminin — sonorités maghrébines, électroniques et afro. De 19h30 à 00h45.",
    },
    {
        "uid": "arabesques-2026-sofiane@festivalarabesques.fr",
        "start": ("TZ", "20260918T193000"),
        "end": ("TZ", "20260918T210000"),
        "summary": "Sofiane Saidi avec Théo & Valentin Ceccaldi",
        "location": "Théâtre Jean-Claude Carrière, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Musiques du monde et jazz.",
    },
    {
        "uid": "arabesques-2026-ino@festivalarabesques.fr",
        "start": ("TZ", "20260918T213000"),
        "end": ("TZ", "20260918T230000"),
        "summary": "Ino · Casablanca",
        "location": "Amphi d'O, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Rap marocain — phénomène Ino Casablanca.",
    },
    {
        "uid": "arabesques-2026-ali-sat@festivalarabesques.fr",
        "start": ("TZ", "20260919T143000"),
        "end": ("TZ", "20260919T154500"),
        "summary": "Ali Merghache — Contes",
        "location": "Amphi d'O, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Contes et histoires par Ali Merghache.",
    },
    {
        "uid": "arabesques-2026-merwane@festivalarabesques.fr",
        "start": ("TZ", "20260919T163000"),
        "end": ("TZ", "20260919T174500"),
        "summary": "Merwane Benlazar — Stand-up",
        "location": "Théâtre Jean-Claude Carrière, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "One-man show par Merwane Benlazar.",
    },
    {
        "uid": "arabesques-2026-yasmine@festivalarabesques.fr",
        "start": ("TZ", "20260919T193000"),
        "end": ("TZ", "20260919T210000"),
        "summary": "Yasmine Hamdan",
        "location": "Théâtre Jean-Claude Carrière, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Pop électro — pionnière de la scène underground de Beyrouth.",
    },
    {
        "uid": "arabesques-2026-emel@festivalarabesques.fr",
        "start": ("TZ", "20260919T213000"),
        "end": ("TZ", "20260919T230000"),
        "summary": "Emel + Camélia Jordana",
        "location": "Amphi d'O, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Concert folk et musiques du monde.",
    },
    {
        "uid": "arabesques-2026-ali-sun@festivalarabesques.fr",
        "start": ("TZ", "20260920T143000"),
        "end": ("TZ", "20260920T154500"),
        "summary": "Ali Merghache — Contes",
        "location": "Amphi d'O, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Contes et histoires par Ali Merghache.",
    },
    {
        "uid": "arabesques-2026-abdullah@festivalarabesques.fr",
        "start": ("TZ", "20260920T163000"),
        "end": ("TZ", "20260920T174500"),
        "summary": "Abdullah Miniawy",
        "location": "Théâtre Jean-Claude Carrière, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Jazz alternatif — chanteur et poète égyptien.",
    },
    {
        "uid": "arabesques-2026-abdelkader@festivalarabesques.fr",
        "start": ("TZ", "20260920T170000"),
        "end": ("TZ", "20260920T181500"),
        "summary": "Abdelkader Secteur — Stand-up",
        "location": "Amphi d'O, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "One-man show par Abdelkader Secteur.",
    },
    {
        "uid": "arabesques-2026-samifati@festivalarabesques.fr",
        "start": ("TZ", "20260920T193000"),
        "end": ("TZ", "20260920T210000"),
        "summary": "Samifati & Transe Gnawa Express",
        "location": "Théâtre Jean-Claude Carrière, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Électro-gnawa.",
    },
    {
        "uid": "arabesques-2026-souad@festivalarabesques.fr",
        "start": ("TZ", "20260920T210000"),
        "end": ("TZ", "20260920T223000"),
        "summary": "Souad Massi — Concert de clôture",
        "location": "Amphi d'O, Domaine d'O, 178 Rue de la Carriérasse, 34090 Montpellier",
        "description": "Concert de clôture du festival — icône chaâbi-folk algéroise, sous les étoiles.",
    },
]


def ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def color_for_uid(uid: str) -> str:
    digest = hashlib.sha256(uid.encode()).hexdigest()
    rng = random.Random(digest)
    return str(rng.randint(1, 11))


def fold_line(line: str) -> list[str]:
    if len(line) <= 75:
        return [line]
    parts = [line[:75]]
    rest = line[75:]
    while rest:
        parts.append(" " + rest[:74])
        rest = rest[74:]
    return parts


def format_dtstart(kind: str, value: str) -> str:
    if kind == "DATE":
        return f"DTSTART;VALUE=DATE:{value}"
    return f"DTSTART;TZID=Europe/Paris:{value}"


def format_dtend(kind: str, value: str) -> str:
    if kind == "DATE":
        return f"DTEND;VALUE=DATE:{value}"
    return f"DTEND;TZID=Europe/Paris:{value}"


def build_event(event: dict) -> list[str]:
    color_id = color_for_uid(event["uid"])
    _, css_color, hex_color = GOOGLE_COLORS[color_id]
    description = (
        f"{event['description']}\n\n"
        f"Google-Calendar-ColorId: {color_id}"
    )

    lines = [
        "BEGIN:VEVENT",
        f"UID:{event['uid']}",
        "DTSTAMP:20260729T114000Z",
        format_dtstart(*event["start"]),
        format_dtend(*event["end"]),
        f"SUMMARY:{ics_escape(event['summary'])}",
        f"LOCATION:{ics_escape(event['location'])}",
        f"DESCRIPTION:{ics_escape(description)}",
        f"COLOR:{css_color}",
        f"X-GOOGLE-CALENDAR-CONTENT-COLOR:{hex_color}",
        f"X-GOOGLE-CALENDAR-CONTENT-COLOR-ID:{color_id}",
        "URL:https://www.festivalarabesques.fr/",
        "END:VEVENT",
    ]
    return lines


def main() -> None:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Festival Arabesques 2026//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Festival Arabesques 2026",
        "X-WR-TIMEZONE:Europe/Paris",
        "BEGIN:VTIMEZONE",
        "TZID:Europe/Paris",
        "BEGIN:DAYLIGHT",
        "TZOFFSETFROM:+0100",
        "TZOFFSETTO:+0200",
        "TZNAME:CEST",
        "DTSTART:19700329T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
        "END:DAYLIGHT",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0200",
        "TZOFFSETTO:+0100",
        "TZNAME:CET",
        "DTSTART:19701025T030000",
        "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

    for event in EVENTS:
        lines.extend(build_event(event))

    lines.append("END:VCALENDAR")

    folded: list[str] = []
    for line in lines:
        folded.extend(fold_line(line))

    OUTPUT.write_text("\n".join(folded) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(EVENTS)} events)")


if __name__ == "__main__":
    main()
