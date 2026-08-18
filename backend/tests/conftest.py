import pytest

from accounts.models import User


@pytest.fixture(autouse=True)
def isolate_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def password():
    return "Correct-Horse-Battery-Staple-947!"


@pytest.fixture
def user(db, password):
    return User.objects.create_user(username="operator", password=password)
