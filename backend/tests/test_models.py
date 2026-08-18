from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from entities.models import Entity, Relationship
from targets.models import Target


@pytest.mark.django_db
def test_target_normalizes_and_enforces_uniqueness(user):
    first = Target(target_type=Target.Type.DOMAIN, display_value=" Example.COM ", created_by=user)
    first.full_clean()
    first.save()
    assert first.normalized_value == "example.com"

    duplicate = Target(target_type=Target.Type.DOMAIN, display_value="example.com", created_by=user)
    with pytest.raises(ValidationError):
        duplicate.full_clean()


@pytest.mark.django_db
def test_relationship_cannot_point_to_itself():
    entity = Entity.objects.create(
        entity_type="domain", display_value="example.com", normalized_value="example.com"
    )
    relationship = Relationship(
        source=entity,
        target=entity,
        relationship_type="related_to",
        confidence=Decimal("0.500"),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        relationship.save()
