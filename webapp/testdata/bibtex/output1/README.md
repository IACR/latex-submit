This has a bug in it where it doesn't generate labelalpha for two of
the 32 references. This is because there are two @misc entries with
only a title (no author). This comes from Eurocrypt 2024 paper #253.