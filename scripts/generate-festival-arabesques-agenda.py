#!/usr/bin/env python3
"""Generate a standalone Festival Arabesques 2026 HTML agenda."""

from __future__ import annotations

import json
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "festival-arabesques-2026-agenda.html"
IMG = "https://www.festivalarabesques.fr/images/arabesques2026"


def img(*names: str) -> list[str]:
    return [f"{IMG}/{name}" for name in names]


EVENTS = [
    {"id": "oum", "day": "2026-09-08", "start": "20:00", "end": "21:30", "title": "Oum", "subtitle": "Concert d'ouverture", "venue": "Opéra Comédie", "venueShort": "Opéra", "type": "concert", "desc": "La vocaliste marocaine ouvre la 21e édition avec un répertoire poétique et épuré.", "images": img("Oum_1__Lamia_Lahbabi.jpg", "Oum_1.jpg", "Oum.jpg")},
    {"id": "bachar", "day": "2026-09-09", "start": "20:00", "end": "21:30", "title": "Bachar Mar-Khalifé", "subtitle": "Joue Christophe", "venue": "Opéra Comédie", "venueShort": "Opéra", "type": "concert", "desc": "Hommage émouvant à Christophe par le musicien franco-libanais.", "images": img("Bachar%20Mar-Khalife%20C%20Cedric%20Aoudia%203.jpg", "Bachar_Mar-Khalife_1.jpg")},
    {"id": "imarhan", "day": "2026-09-11", "start": "19:30", "end": "21:00", "title": "Imarhan", "subtitle": "Blues touareg", "venue": "Théâtre Jean-Claude Carrière", "venueShort": "T. Carrière", "type": "concert", "desc": "Emblème de la nouvelle génération du blues tamasheq.", "images": img("Imarhan_1.jpg", "Imarhan.jpg")},
    {"id": "anouar", "day": "2026-09-11", "start": "21:30", "end": "23:00", "title": "Anouar Brahem Quartet", "subtitle": "Jazz & oud", "venue": "Amphi d'O", "venueShort": "Amphi d'O", "type": "concert", "desc": "Le maître oudiste tunisien et son quartet.", "images": img("Anouar_Brahem_1__Marco_Borggreve.jpg", "Anouar_Brahem_1.jpg")},
    {"id": "jihad-sat", "day": "2026-09-12", "start": "14:30", "end": "15:45", "title": "Jihad Darwiche", "subtitle": "Contes", "venue": "Domaine d'O", "venueShort": "Domaine d'O", "type": "conte", "desc": "Contes et histoires pour petits et grands.", "images": img("_DSC2565Arabesques_Jihad_Darwiche_2025Luc_Jennepin_1.jpg")},
    {"id": "antidote", "day": "2026-09-12", "start": "16:30", "end": "17:45", "title": "L'Antidote", "subtitle": "Chemirani · Hasa · Khalifé", "venue": "Théâtre Jean-Claude Carrière", "venueShort": "T. Carrière", "type": "concert", "desc": "World jazz instrumental — zarb, violoncelle et piano.", "images": img("Antidote_1__Gabriele_Surdo.jpg", "L_Antidote_1.jpg")},
    {"id": "zar", "day": "2026-09-12", "start": "19:30", "end": "21:00", "title": "Zar Electrik + Temenik Electric", "subtitle": "Traditions & électro", "venue": "Théâtre Jean-Claude Carrière", "venueShort": "T. Carrière", "type": "concert", "desc": "Rituels zar et sonorités électriques berbères.", "images": img("Zar_Electrik_1.jpg", "Zar_Electrik_Temenik_Electric_1.jpg")},
    {"id": "sahravane", "day": "2026-09-12", "start": "21:30", "end": "23:00", "title": "Sahravane", "subtitle": "Asla · Sosa · Lemma", "venue": "Amphi d'O", "venueShort": "Amphi d'O", "type": "concert", "desc": "Un pont entre le Sahara et Cuba.", "images": img("Omar_Sosa__Lemma_1__Erol_Gum.jpg", "Sahravane_1.jpg")},
    {"id": "jihad-sun", "day": "2026-09-13", "start": "14:30", "end": "15:45", "title": "Jihad Darwiche", "subtitle": "Contes", "venue": "Domaine d'O", "venueShort": "Domaine d'O", "type": "conte", "desc": "Rencontres littéraires en hommage à Driss Chraïbi.", "images": img("_DSC2565Arabesques_Jihad_Darwiche_2025Luc_Jennepin_1.jpg")},
    {"id": "meryem", "day": "2026-09-13", "start": "16:30", "end": "17:45", "title": "Meryem Aboulouafa", "subtitle": "Pop & folk", "venue": "Théâtre Jean-Claude Carrière", "venueShort": "T. Carrière", "type": "concert", "desc": "Auteure-compositrice de Casablanca.", "images": img("Meryem_Aboulouafa_1.jpg")},
    {"id": "amine", "day": "2026-09-13", "start": "17:00", "end": "18:15", "title": "Amine Radi", "subtitle": "Stand-up", "venue": "Amphi d'O", "venueShort": "Amphi d'O", "type": "humour", "desc": "Humour franc et décapant.", "images": img("Amine_Radi_1.jpg")},
    {"id": "daoud", "day": "2026-09-13", "start": "19:30", "end": "21:00", "title": "Daoud", "subtitle": "Jazz", "venue": "Théâtre Jean-Claude Carrière", "venueShort": "T. Carrière", "type": "concert", "desc": "Le trompettiste Daoud en concert.", "images": img("Daoud_1.jpg")},
    {"id": "zina", "day": "2026-09-13", "start": "21:00", "end": "22:30", "title": "Zina Daoudia", "subtitle": "Chaâbi & pop", "venue": "Amphi d'O", "venueShort": "Amphi d'O", "type": "concert", "desc": "Énergie et fête au Domaine d'O.", "images": img("Zina_Daoudia_1.jpg")},
    {"id": "soundsystem", "day": "2026-09-17", "start": "19:30", "end": "00:45", "endDay": "2026-09-18", "title": "Arabesques Sound System", "subtitle": "Kbira · Karrum · La Louuve", "venue": "Halle Tropisme", "venueShort": "Tropisme", "type": "dj", "desc": "Soirée 100% féminine — maghreb, afro & électro.", "images": img("Arabesques_Sound_System_1.jpg", "Kbira_1.jpg")},
    {"id": "sofiane", "day": "2026-09-18", "start": "19:30", "end": "21:00", "title": "Sofiane Saidi", "subtitle": "avec Théo & Valentin Ceccaldi", "venue": "Théâtre Jean-Claude Carrière", "venueShort": "T. Carrière", "type": "concert", "desc": "Raï punk et jazz manouche.", "images": img("Sofiane_Saidi_1.jpg")},
    {"id": "ino", "day": "2026-09-18", "start": "21:30", "end": "23:00", "title": "Ino · Casablanca", "subtitle": "Rap marocain", "venue": "Amphi d'O", "venueShort": "Amphi d'O", "type": "concert", "desc": "Le phénomène du rap alternatif marocain.", "images": img("Ino_Casablanca_1.jpg", "Ino_1.jpg")},
    {"id": "ali-sat", "day": "2026-09-19", "start": "14:30", "end": "15:45", "title": "Ali Merghache", "subtitle": "Contes", "venue": "Amphi d'O", "venueShort": "Amphi d'O", "type": "conte", "desc": "Contes et histoires du Maghreb.", "images": img("Ali_Merghache_1.jpg")},
    {"id": "merwane", "day": "2026-09-19", "start": "16:30", "end": "17:45", "title": "Merwane Benlazar", "subtitle": "Stand-up", "venue": "Théâtre Jean-Claude Carrière", "venueShort": "T. Carrière", "type": "humour", "desc": "One-man show hilarant.", "images": img("Merwane_Benlazar__Exsteb_2_1_1.jpg")},
    {"id": "yasmine", "day": "2026-09-19", "start": "19:30", "end": "21:00", "title": "Yasmine Hamdan", "subtitle": "Pop électro", "venue": "Théâtre Jean-Claude Carrière", "venueShort": "T. Carrière", "type": "concert", "desc": "Pionnière de la scène underground de Beyrouth.", "images": img("Yasmine_Hamdan_1.jpg")},
    {"id": "emel", "day": "2026-09-19", "start": "21:30", "end": "23:00", "title": "Emel + Camélia Jordana", "subtitle": "Duo exceptionnel", "venue": "Amphi d'O", "venueShort": "Amphi d'O", "type": "concert", "desc": "Voix tunisienne et chanson française.", "images": img("Emel_Camelia_Jordana_1.jpg", "Emel_1.jpg")},
    {"id": "ali-sun", "day": "2026-09-20", "start": "14:30", "end": "15:45", "title": "Ali Merghache", "subtitle": "Contes", "venue": "Amphi d'O", "venueShort": "Amphi d'O", "type": "conte", "desc": "Dernière session de contes du week-end.", "images": img("Ali_Merghache_1.jpg")},
    {"id": "abdullah", "day": "2026-09-20", "start": "16:30", "end": "17:45", "title": "Abdullah Miniawy", "subtitle": "Jazz alternatif", "venue": "Théâtre Jean-Claude Carrière", "venueShort": "T. Carrière", "type": "concert", "desc": "Chanteur et poète égyptien.", "images": img("Abdullah_Miniawy_1.jpg")},
    {"id": "abdelkader", "day": "2026-09-20", "start": "17:00", "end": "18:15", "title": "Abdelkader Secteur", "subtitle": "Stand-up", "venue": "Amphi d'O", "venueShort": "Amphi d'O", "type": "humour", "desc": "Humour engagé et décalé.", "images": img("Abdelkader_Secteur_1.jpg")},
    {"id": "samifati", "day": "2026-09-20", "start": "19:30", "end": "21:00", "title": "Samifati & Transe Gnawa Express", "subtitle": "Électro-gnawa", "venue": "Théâtre Jean-Claude Carrière", "venueShort": "T. Carrière", "type": "concert", "desc": "Transe et rythmes gnawa revisités.", "images": img("Samifati__Transe_Gnawa_Express_2_1.jpg")},
    {"id": "souad", "day": "2026-09-20", "start": "21:00", "end": "22:30", "title": "Souad Massi", "subtitle": "Concert de clôture", "venue": "Amphi d'O", "venueShort": "Amphi d'O", "type": "concert", "desc": "Clôture majestueuse sous les étoiles.", "images": img("Souad_Massi_1.jpg")},
]

TYPE_COLORS = {
    "concert": "#e8a838",
    "conte": "#5eb8b0",
    "humour": "#e06b8c",
    "dj": "#9b6dff",
}

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Festival Arabesques 2026 — Agenda</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,700;1,500&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0c1018;
  --bg2: #121a26;
  --card: rgba(255,255,255,.05);
  --card-hover: rgba(255,255,255,.08);
  --border: rgba(255,255,255,.09);
  --text: #f4efe6;
  --muted: #9aa8b8;
  --gold: #e8a838;
  --terracotta: #d4644a;
  --teal: #2f9e95;
  --now: #ff5f6d;
  --shadow: 0 20px 60px rgba(0,0,0,.45);
  --radius: 18px;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: "Outfit", system-ui, sans-serif;
  color: var(--text);
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(232,168,56,.14), transparent 55%),
    radial-gradient(900px 500px at 90% 0%, rgba(47,158,149,.12), transparent 50%),
    linear-gradient(180deg, #0a0e15 0%, var(--bg) 30%, #0d1219 100%);
  min-height: 100vh;
}
body::before {
  content: "";
  position: fixed; inset: 0; pointer-events: none; opacity: .35;
  background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}
.wrap { max-width: 1100px; margin: 0 auto; padding: 0 20px 80px; position: relative; z-index: 1; }

.hero {
  padding: 42px 0 28px;
  text-align: center;
}
.eyebrow {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 6px 14px; border-radius: 999px;
  background: rgba(232,168,56,.12); border: 1px solid rgba(232,168,56,.25);
  color: var(--gold); font-size: .78rem; letter-spacing: .14em; text-transform: uppercase;
}
.hero h1 {
  margin: 18px 0 8px;
  font-family: "Cormorant Garamond", Georgia, serif;
  font-size: clamp(2.4rem, 6vw, 4.2rem);
  font-weight: 700; line-height: 1.02;
  background: linear-gradient(135deg, #fff 0%, #f0d7a2 45%, #e8a838 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero p { margin: 0; color: var(--muted); font-size: 1.05rem; }
.hero .meta { margin-top: 14px; display: flex; justify-content: center; gap: 18px; flex-wrap: wrap; font-size: .92rem; }
.hero .meta span { display: inline-flex; align-items: center; gap: 8px; }

.status {
  margin: 24px auto 0; max-width: 680px;
  padding: 14px 18px; border-radius: 14px;
  background: rgba(255,255,255,.04); border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
}
.status strong { font-size: 1rem; }
.status .clock { font-variant-numeric: tabular-nums; color: var(--gold); font-weight: 600; }
.btn-now {
  margin-left: auto; padding: 8px 14px; border-radius: 999px; border: 1px solid rgba(255,95,109,.35);
  background: rgba(255,95,109,.12); color: #ffb4bc; font-size: .78rem; font-weight: 600;
  cursor: pointer; letter-spacing: .04em; text-transform: uppercase;
}
.btn-now:hover { background: rgba(255,95,109,.2); }

.timeline-shell {
  position: sticky; top: 0; z-index: 20;
  margin: 28px 0 34px;
  padding: 16px 0 18px;
  backdrop-filter: blur(16px);
  background: rgba(12,16,24,.78);
  border-bottom: 1px solid rgba(255,255,255,.06);
}
.timeline-head {
  display: flex; justify-content: space-between; align-items: end;
  margin-bottom: 12px; gap: 12px; flex-wrap: wrap;
}
.timeline-head h2 {
  margin: 0; font-family: "Cormorant Garamond", serif;
  font-size: 1.35rem; font-weight: 600;
}
.timeline-head small { color: var(--muted); }

.timeline-track {
  position: relative; height: 54px;
  border-radius: 14px;
  background: linear-gradient(90deg, rgba(255,255,255,.04), rgba(255,255,255,.07), rgba(255,255,255,.04));
  border: 1px solid var(--border);
  overflow: hidden;
}
.timeline-days {
  position: absolute; inset: 0;
  display: grid;
  grid-template-columns: repeat(13, 1fr);
}
.day-cell {
  position: relative; border-right: 1px solid rgba(255,255,255,.05);
  display: flex; align-items: end; justify-content: center;
  padding-bottom: 6px; font-size: .68rem; color: var(--muted);
}
.day-cell:last-child { border-right: none; }
.day-cell.active { background: rgba(232,168,56,.08); color: var(--gold); font-weight: 600; }
.day-cell.has-events::before {
  content: ""; position: absolute; top: 10px; left: 50%; transform: translateX(-50%);
  width: 5px; height: 5px; border-radius: 50%; background: var(--teal);
}
.timeline-progress {
  position: absolute; top: 0; left: 0; bottom: 0;
  background: linear-gradient(90deg, rgba(232,168,56,.18), rgba(47,158,149,.12));
  width: 0; pointer-events: none;
}
.timeline-cursor {
  position: absolute; top: -4px; bottom: -4px; width: 3px;
  background: linear-gradient(180deg, #fff, var(--now), #fff);
  box-shadow: 0 0 18px rgba(255,95,109,.8), 0 0 4px rgba(255,255,255,.8);
  transform: translateX(-50%);
  transition: left .8s cubic-bezier(.22,1,.36,1);
  z-index: 3;
}
.timeline-cursor::before {
  content: ""; position: absolute; top: -7px; left: 50%; transform: translateX(-50%);
  width: 14px; height: 14px; border-radius: 50%;
  background: var(--now); border: 2px solid #fff;
  box-shadow: 0 0 16px rgba(255,95,109,.9);
}
.timeline-cursor::after {
  content: "MAINTENANT"; position: absolute; bottom: -22px; left: 50%; transform: translateX(-50%);
  font-size: .58rem; letter-spacing: .12em; color: var(--now); font-weight: 700; white-space: nowrap;
}
.timeline-cursor.hidden { opacity: 0; }

.legend { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 14px; }
.legend span { font-size: .75rem; color: var(--muted); display: inline-flex; align-items: center; gap: 6px; }
.legend i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }

.day-section { margin-bottom: 42px; position: relative; }
.day-header {
  display: flex; align-items: baseline; gap: 14px;
  margin: 0 0 18px; padding-bottom: 10px;
  border-bottom: 1px solid rgba(255,255,255,.08);
}
.day-header h3 {
  margin: 0; font-family: "Cormorant Garamond", serif;
  font-size: 1.8rem; font-weight: 700;
}
.day-header .weekday { color: var(--gold); text-transform: uppercase; letter-spacing: .08em; font-size: .78rem; font-weight: 600; }
.day-header .count { margin-left: auto; color: var(--muted); font-size: .85rem; }

.events-rail { position: relative; padding-left: 88px; }
.events-rail::before {
  content: ""; position: absolute; left: 34px; top: 0; bottom: 0; width: 2px;
  background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.18), rgba(255,255,255,.08));
}
.now-line {
  position: absolute; left: 0; right: 0; height: 2px; z-index: 5; pointer-events: none;
  background: linear-gradient(90deg, transparent, var(--now), transparent);
  box-shadow: 0 0 20px rgba(255,95,109,.5);
  opacity: 0; transition: opacity .4s;
}
.now-line.visible { opacity: 1; }
.now-line::before {
  content: ""; position: absolute; left: 22px; top: 50%; transform: translate(-50%,-50%);
  width: 12px; height: 12px; border-radius: 50%; background: var(--now); border: 2px solid #fff;
}

.event-card {
  position: relative;
  display: grid; grid-template-columns: 96px 1fr; gap: 18px;
  margin-bottom: 16px; padding: 16px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  transition: transform .25s ease, background .25s ease, border-color .25s ease;
}
.event-card:hover { transform: translateY(-2px); background: var(--card-hover); border-color: rgba(255,255,255,.14); }
.event-card.live {
  border-color: rgba(255,95,109,.45);
  background: linear-gradient(135deg, rgba(255,95,109,.08), rgba(255,255,255,.04));
}
.event-card.past { opacity: .62; }
.event-card.upcoming { border-color: rgba(232,168,56,.25); }

.time-col {
  position: absolute; left: -88px; width: 68px; text-align: right;
  top: 22px; font-variant-numeric: tabular-nums;
}
.time-col .start { display: block; font-weight: 600; font-size: .95rem; }
.time-col .end { display: block; color: var(--muted); font-size: .75rem; margin-top: 2px; }
.time-dot {
  position: absolute; left: 26px; top: 28px; width: 16px; height: 16px;
  border-radius: 50%; background: var(--bg2); border: 3px solid var(--gold);
  z-index: 2;
}
.event-card.live .time-dot { border-color: var(--now); box-shadow: 0 0 12px rgba(255,95,109,.7); animation: pulse 1.6s infinite; }
@keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.12); } }

.thumb {
  width: 96px; height: 96px; border-radius: 14px; overflow: hidden;
  background: linear-gradient(135deg, rgba(255,255,255,.08), rgba(255,255,255,.02));
  border: 1px solid rgba(255,255,255,.08);
  position: relative; flex-shrink: 0;
}
.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumb .fallback {
  position: absolute; inset: 0; display: grid; place-items: center;
  font-family: "Cormorant Garamond", serif; font-size: 1.6rem; font-weight: 700;
  color: rgba(255,255,255,.85);
}

.body h4 { margin: 0 0 4px; font-size: 1.15rem; font-weight: 600; }
.body .subtitle { margin: 0 0 8px; color: var(--gold); font-size: .88rem; font-weight: 500; }
.body .desc { margin: 0 0 10px; color: var(--muted); font-size: .88rem; line-height: 1.45; }
.meta-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 999px; font-size: .72rem; font-weight: 600;
  letter-spacing: .04em; text-transform: uppercase;
  background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.08);
}
.badge.type-concert { color: var(--gold); border-color: rgba(232,168,56,.25); background: rgba(232,168,56,.08); }
.badge.type-conte { color: #7fd8cf; border-color: rgba(94,184,176,.25); background: rgba(94,184,176,.08); }
.badge.type-humour { color: #f08ba8; border-color: rgba(224,107,140,.25); background: rgba(224,107,140,.08); }
.badge.type-dj { color: #c4a0ff; border-color: rgba(155,109,255,.25); background: rgba(155,109,255,.08); }
.venue { color: var(--muted); font-size: .8rem; }

.footer {
  margin-top: 48px; text-align: center; color: var(--muted); font-size: .82rem;
  padding-top: 24px; border-top: 1px solid var(--border);
}
.footer a { color: var(--gold); text-decoration: none; }

@media (max-width: 720px) {
  .events-rail { padding-left: 0; }
  .events-rail::before, .time-col, .time-dot { display: none; }
  .event-card { grid-template-columns: 72px 1fr; gap: 12px; padding: 12px; }
  .thumb { width: 72px; height: 72px; }
  .timeline-cursor::after { display: none; }
}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div class="eyebrow">21e édition · Montpellier</div>
    <h1>Festival Arabesques</h1>
    <p>Le plus grand rendez-vous des arts du monde arabe en Europe</p>
    <div class="meta">
      <span>📅 8 – 20 septembre 2026</span>
      <span>📍 Opéra Comédie · Domaine d'O · Halle Tropisme</span>
    </div>
    <div class="status">
      <strong id="statusText">Chargement…</strong>
      <span class="clock" id="clock"></span>
      <button class="btn-now" id="jumpNow" type="button">Aller à maintenant</button>
    </div>
  </header>

  <section class="timeline-shell" aria-label="Timeline du festival">
    <div class="timeline-head">
      <h2>Progression du festival</h2>
      <small id="timelineLabel">—</small>
    </div>
    <div class="timeline-track" id="timelineTrack">
      <div class="timeline-progress" id="timelineProgress"></div>
      <div class="timeline-days" id="timelineDays"></div>
      <div class="timeline-cursor hidden" id="timelineCursor"></div>
    </div>
    <div class="legend">
      <span><i style="background:var(--gold)"></i> Concert</span>
      <span><i style="background:#5eb8b0"></i> Conte</span>
      <span><i style="background:#e06b8c"></i> Humour</span>
      <span><i style="background:#9b6dff"></i> DJ set</span>
      <span><i style="background:var(--now)"></i> Maintenant</span>
    </div>
  </section>

  <main id="agenda"></main>

  <footer class="footer">
  Programme & images © <a href="https://www.festivalarabesques.fr/" target="_blank" rel="noopener">Festival Arabesques</a> ·
  Agenda généré le 29 juillet 2026
  </footer>
</div>

<script>
const EVENTS = __EVENTS_JSON__;
const FESTIVAL_START = new Date('2026-09-08T00:00:00+02:00');
const FESTIVAL_END = new Date('2026-09-20T23:59:59+02:00');
const TYPE_LABELS = { concert: 'Concert', conte: 'Conte', humour: 'Humour', dj: 'DJ set' };
const TYPE_COLORS = __TYPE_COLORS_JSON__;
const WEEKDAYS = ['Dimanche','Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'];
const MONTHS = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];

function parseEventDate(event) {
  const endDay = event.endDay || event.day;
  return {
    start: new Date(`${event.day}T${event.start}:00+02:00`),
    end: new Date(`${endDay}T${event.end}:00+02:00`),
  };
}

function formatTime(d) {
  return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Paris' });
}

function formatDayHeader(dayStr) {
  const d = new Date(`${dayStr}T12:00:00+02:00`);
  return {
    weekday: WEEKDAYS[d.getDay()],
    label: `${d.getDate()} ${MONTHS[d.getMonth()]} 2026`,
  };
}

function makeFallbackThumb(event) {
  const hue = [...event.id].reduce((a,c)=>a+c.charCodeAt(0),0) % 360;
  const initials = event.title.split(/[\s·&+]+/).filter(Boolean).slice(0,2).map(w=>w[0]).join('').toUpperCase();
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0%' stop-color='hsl(${hue},55%,42%)'/><stop offset='100%' stop-color='hsl(${(hue+40)%360},60%,28%)'/></linearGradient></defs><rect width='200' height='200' fill='url(#g)'/><text x='50%' y='54%' text-anchor='middle' dominant-baseline='middle' fill='rgba(255,255,255,.9)' font-family='Georgia,serif' font-size='56' font-weight='700'>${initials}</text></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function groupByDay(events) {
  const days = {};
  for (const e of events) {
    (days[e.day] ||= []).push(e);
  }
  for (const k of Object.keys(days)) {
    days[k].sort((a,b) => a.start.localeCompare(b.start));
  }
  return Object.keys(days).sort().map(day => ({ day, events: days[day] }));
}

function loadThumb(img, fallback, event) {
  const sources = event.images || [];
  let index = 0;
  const tryNext = () => {
    if (index >= sources.length) {
      img.remove();
      fallback.hidden = false;
      fallback.style.background = `linear-gradient(135deg, ${TYPE_COLORS[event.type] || '#888'}66, rgba(255,255,255,.04))`;
      fallback.textContent = event.title.split(/[\s·&+]+/).filter(Boolean).slice(0,2).map(w=>w[0]).join('');
      return;
    }
    img.src = sources[index++];
  };
  img.addEventListener('error', tryNext);
  tryNext();
}

function renderAgenda() {
  const root = document.getElementById('agenda');
  root.innerHTML = '';
  const groups = groupByDay(EVENTS);
  for (const group of groups) {
    const { weekday, label } = formatDayHeader(group.day);
    const section = document.createElement('section');
    section.className = 'day-section';
    section.id = `day-${group.day}`;
    section.innerHTML = `
      <div class="day-header">
        <div>
          <div class="weekday">${weekday}</div>
          <h3>${label}</h3>
        </div>
        <div class="count">${group.events.length} événement${group.events.length > 1 ? 's' : ''}</div>
      </div>
      <div class="events-rail" data-day="${group.day}"></div>`;
    const rail = section.querySelector('.events-rail');
    for (const event of group.events) {
      const { start, end } = parseEventDate(event);
      const card = document.createElement('article');
      card.className = 'event-card';
      card.dataset.eventId = event.id;
      card.dataset.start = start.toISOString();
      card.dataset.end = end.toISOString();
      card.innerHTML = `
        <div class="time-col"><span class="start">${event.start.replace(':', 'h')}</span><span class="end">${event.end.replace(':', 'h')}</span></div>
        <div class="time-dot"></div>
        <div class="thumb">
          <img alt="${event.title}" loading="lazy" decoding="async">
          <div class="fallback" hidden></div>
        </div>
        <div class="body">
          <h4>${event.title}</h4>
          <p class="subtitle">${event.subtitle}</p>
          <p class="desc">${event.desc}</p>
          <div class="meta-row">
            <span class="badge type-${event.type}">${TYPE_LABELS[event.type] || event.type}</span>
            <span class="venue">📍 ${event.venue}</span>
          </div>
        </div>`;
      const img = card.querySelector('img');
      const fallback = card.querySelector('.fallback');
      loadThumb(img, fallback, event);
      rail.appendChild(card);
    }
    root.appendChild(section);
  }
}

function renderTimelineDays() {
  const container = document.getElementById('timelineDays');
  container.innerHTML = '';
  const eventDays = new Set(EVENTS.map(e => e.day));
  for (let i = 8; i <= 20; i++) {
    const dayStr = `2026-09-${String(i).padStart(2,'0')}`;
    const cell = document.createElement('div');
    cell.className = 'day-cell' + (eventDays.has(dayStr) ? ' has-events' : '');
    cell.textContent = i;
    cell.title = dayStr;
    container.appendChild(cell);
  }
}

function updateNow() {
  const now = new Date();
  const clock = document.getElementById('clock');
  clock.textContent = now.toLocaleString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Europe/Paris'
  });

  const status = document.getElementById('statusText');
  const cursor = document.getElementById('timelineCursor');
  const progress = document.getElementById('timelineProgress');
  const label = document.getElementById('timelineLabel');

  if (now < FESTIVAL_START) {
    const days = Math.ceil((FESTIVAL_START - now) / 86400000);
    status.textContent = `Le festival commence dans ${days} jour${days > 1 ? 's' : ''}`;
    cursor.classList.add('hidden');
    progress.style.width = '0%';
    label.textContent = 'Avant le festival';
  } else if (now > FESTIVAL_END) {
    status.textContent = 'Le festival est terminé — à l\'année prochaine !';
    cursor.classList.add('hidden');
    progress.style.width = '100%';
    label.textContent = 'Après le festival';
  } else {
    status.textContent = 'Le festival est en cours';
    cursor.classList.remove('hidden');
    const pct = ((now - FESTIVAL_START) / (FESTIVAL_END - FESTIVAL_START)) * 100;
    cursor.style.left = `${pct}%`;
    progress.style.width = `${pct}%`;
    label.textContent = `${Math.round(pct)}% du festival écoulé`;
  }

  document.querySelectorAll('.event-card').forEach(card => {
    const start = new Date(card.dataset.start);
    const end = new Date(card.dataset.end);
    card.classList.remove('live', 'past', 'upcoming');
    if (now >= start && now <= end) card.classList.add('live');
    else if (now > end) card.classList.add('past');
    else if (now < start) card.classList.add('upcoming');
  });

  document.querySelectorAll('.day-cell').forEach((cell, idx) => {
    const day = 8 + idx;
    const dayDate = new Date(`2026-09-${String(day).padStart(2,'0')}T12:00:00+02:00`);
    const active = now.toDateString() === dayDate.toDateString();
    cell.classList.toggle('active', active);
  });

  document.querySelectorAll('.events-rail').forEach(rail => {
    rail.querySelectorAll('.now-line').forEach(n => n.remove());
    const day = rail.dataset.day;
    const dayStart = new Date(`${day}T00:00:00+02:00`);
    const dayEnd = new Date(`${day}T23:59:59+02:00`);
    if (now < dayStart || now > dayEnd) return;
    const cards = [...rail.querySelectorAll('.event-card')];
    let placed = false;
    for (let i = 0; i < cards.length; i++) {
      const card = cards[i];
      const start = new Date(card.dataset.start);
      const end = new Date(card.dataset.end);
      if (now > end && i < cards.length - 1) continue;
      if (now <= end) {
        const line = document.createElement('div');
        line.className = 'now-line visible';
        const top = card.offsetTop + (now >= start && now <= end ? card.offsetHeight * 0.5 : 0);
        line.style.top = `${Math.max(0, top)}px`;
        rail.appendChild(line);
        placed = true;
        break;
      }
    }
    if (!placed && cards.length) {
      const last = cards[cards.length - 1];
      if (now > new Date(last.dataset.end)) {
        const line = document.createElement('div');
        line.className = 'now-line visible';
        line.style.top = `${last.offsetTop + last.offsetHeight}px`;
        rail.appendChild(line);
      }
    }
  });
}

renderTimelineDays();
renderAgenda();
updateNow();
setInterval(updateNow, 1000);

document.getElementById('jumpNow').addEventListener('click', () => {
  const live = document.querySelector('.event-card.live');
  const next = document.querySelector('.event-card.upcoming');
  const target = live || next || document.querySelector('.day-section');
  target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
});
</script>
</body>
</html>
"""

def main() -> None:
    html = (
        HTML_TEMPLATE.replace("__EVENTS_JSON__", json.dumps(EVENTS, ensure_ascii=False))
        .replace("__TYPE_COLORS_JSON__", json.dumps(TYPE_COLORS, ensure_ascii=False))
    )
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(EVENTS)} events, {len(html):,} bytes)")


if __name__ == "__main__":
    main()
