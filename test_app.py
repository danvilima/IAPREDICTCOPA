from streamlit.testing.v1 import AppTest

def test_app():
    print("Testando inicializacao...")
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception, f"Erro inicial: {at.exception}"
    
    print("Testando Simulacao ao vivo...")
    at.sidebar.radio[0].set_value("Simulação ao vivo").run()
    assert not at.exception, f"Erro simulacao: {at.exception}"
    
    print("Testando Explorador...")
    at.sidebar.radio[0].set_value("Explorador de partidas").run()
    at.button[0].click().run()
    assert not at.exception, f"Erro explorador: {at.exception}"
    
    print("Todos os testes passaram!")

if __name__ == "__main__":
    test_app()
