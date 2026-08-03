"""Entry point for the MailPilot SaaS web app.

    python run_saas.py

Environment variables:
  SAAS_SECRET_KEY  Flask session secret (set this in production).
  SAAS_DATABASE    Path to the sqlite database (default: data/saas.db).
  PORT             Port to bind (default: 5001).
"""

import os

from saas.app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="127.0.0.1", port=port, debug=bool(os.environ.get("SAAS_DEBUG")))
