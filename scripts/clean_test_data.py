"""Delete the rows that demo and test runs leave behind. Keeps the knowledge base, portfolio and
seed documents.

  python scripts/clean_test_data.py          show what would be deleted
  python scripts/clean_test_data.py --yes    really delete it
"""

import sys

from sqlalchemy import create_engine, text

from app.db import get_db_url

# (what, SQL that counts the rows, SQL that deletes them)
CLEANUPS = [
    ("sessions from demo runs", "SELECT COUNT(*) FROM ai.agno_sessions", "DELETE FROM ai.agno_sessions"),
    ("runs from demo runs", "SELECT COUNT(*) FROM ai.agno_runs", "DELETE FROM ai.agno_runs"),
    ("approvals", "SELECT COUNT(*) FROM ai.agno_approvals", "DELETE FROM ai.agno_approvals"),
    ("pretend trades", "SELECT COUNT(*) FROM ai.trades", "DELETE FROM ai.trades"),
    ("audit_log rows", "SELECT COUNT(*) FROM ai.audit_log", "DELETE FROM ai.audit_log"),
    ("insights saved by the agent",
     "SELECT COUNT(*) FROM ai.valura_knowledge WHERE meta_data->>'doc_type' = 'insight'",
     "DELETE FROM ai.valura_knowledge WHERE meta_data->>'doc_type' = 'insight'"),
    ("agent-ingested filing / media rows",
     "SELECT COUNT(*) FROM ai.valura_knowledge WHERE meta_data->>'source' IN "
     "('ingest_filing_pdf', 'transcribe_earnings_audio', 'describe_dashboard_screenshot')",
     "DELETE FROM ai.valura_knowledge WHERE meta_data->>'source' IN "
     "('ingest_filing_pdf', 'transcribe_earnings_audio', 'describe_dashboard_screenshot')"),
]

really_delete = "--yes" in sys.argv
with create_engine(get_db_url()).begin() as conn:
    for label, count_sql, delete_sql in CLEANUPS:
        found = conn.execute(text(count_sql)).scalar()
        print(f"{label:<38} {found:>6} rows")
        if really_delete:
            conn.execute(text(delete_sql))

print("\nDeleted." if really_delete else "\nNothing deleted. Add --yes to delete.")
