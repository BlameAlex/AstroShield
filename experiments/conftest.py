"""Configuración mínima de pytest para los tests de experiments/."""


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: prueba lenta (escala completa)")
