"""SOYUZ — engine/signal_format_upgrade_note.py

Nota di miglioramento presentazione segnali.
Non è una regola. Non promuove.
Non legge e non scrive final_decision. Non invia ordini.
promoted = None.

2026-10-29 ~05:10 CET.

Studiato formati tipici di canali segnalatori Telegram (entry/SL/TP multipli, rischio %, motivo chiaro, timestamp, disclaimer).

Migliorato solo il layer di presentazione:
- telegram/signals.py: formato più strutturato stile canale professionale.
- telegram/commodity_direction_alert.py: _ALLOWED allineato all'universo trimmed a 10 core.

Il motore di decisione, la regola ENERGY_SHOCK_AND_WEEKLY_SAME_SIDE,
final_decision e qualsiasi invio ordine restano invariati.
PAPER ONLY.

File toccati: solo i due sopra + questa nota.
"""
