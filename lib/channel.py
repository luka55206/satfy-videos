"""ONE place for channel identity. Fill in once the channel exists.

Every tool that names the channel reads from here, so a rebrand is one edit.
The channel name must NOT contain a trademark (see lib/compliance.py).
"""
CHANNEL = "SatFy"           # YouTube channel display name
CHANNEL_ID = "UCqp3ol1tiQRHMATXmFeSKqg"   # @TheSatFy, read from Studio 2026-10-22
WATERMARK = CHANNEL         # faint on-screen watermark ("" = none)
TIMEZONE = "Asia/Tbilisi"   # local clock used for schedule slots
NICHE = "peg-board ball-drop simulations (code-generated)"
