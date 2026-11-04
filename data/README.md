# Runtime data

The application writes its SQLite state database and any cached feed data here during local development. Runtime data may contain public headline text and decision metadata but must not contain API keys, passwords, broker login details, or raw account credentials.

The directory is intentionally not initialized with a sample database. Keep live runtime data out of source control. Decision audit retention remains indefinite until a retention/export policy is explicitly configured; do not silently delete audit rows.
