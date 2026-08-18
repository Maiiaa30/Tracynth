# Collector boundary

Collectors implement a typed contract with metadata/version, supported target
types, configuration validation, `can_run`, bounded `collect`, normalization, and
production of entities, relationships, evidence, and findings.

Application services own persistence. Collector failures become module errors
and do not abort unrelated scan modules.
