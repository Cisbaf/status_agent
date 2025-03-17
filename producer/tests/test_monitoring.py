import pytest

@pytest.fixture
def setup():
    print("\nConfiguração antes do teste")
    valor = 99
    yield valor  # Retorna o valor para o teste
    print("\nFinalizando após o teste")

def test_quadrado(setup):
    assert setup ** 2 == 9801

def test_raiz(setup):
    assert setup ** 0.5 == pytest.approx(9.94987, 0.0001)
