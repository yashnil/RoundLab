"""Academic and institutional search provider adapters for Pass 9.

Each adapter normalizes raw provider responses into ProviderResult.
Provider-specific payload shapes never escape adapter boundaries.
All adapters are independently testable with mocked HTTP.
"""
