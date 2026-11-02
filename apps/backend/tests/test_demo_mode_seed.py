"""Regressions for preventing demonstration data in non-demo environments."""
from unittest.mock import Mock

from app import main


def test_does_not_open_database_or_seed_when_demo_mode_disabled(monkeypatch):
    db_factory = Mock(side_effect=AssertionError("demo seeding accessed DB"))
    seeder = Mock(side_effect=AssertionError("demo data seeded"))
    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main, "SessionLocal", db_factory)
    monkeypatch.setattr(main, "seed_data", seeder)

    main.startup_seed()

    db_factory.assert_not_called()
    seeder.assert_not_called()


def test_seeds_and_closes_database_in_explicit_demo_mode(monkeypatch):
    db = Mock()
    seeder = Mock()
    monkeypatch.setattr(main.settings, "demo_mode", True)
    monkeypatch.setattr(main, "SessionLocal", Mock(return_value=db))
    monkeypatch.setattr(main, "seed_data", seeder)

    main.startup_seed()

    seeder.assert_called_once_with(db)
    db.close.assert_called_once()
