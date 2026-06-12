import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from previsao import prever_jogo, carregar_modelos

def testar_previsoes():
    carregar_modelos()
    confrontos = [
        ("France", "Scotland"),
        ("Scotland", "France"),
        ("Brazil", "Scotland"),
        ("Argentina", "Scotland"),
        ("Spain", "Scotland"),
    ]
    
    print("--- Testes Manuais em Campo Neutro ---")
    for t1, t2 in confrontos:
        try:
            res = prever_jogo(t1, t2, neutro=True)
            print(f"{t1} x {t2}: xG {t1} = {res['gols_esperados_casa']:.2f}, xG {t2} = {res['gols_esperados_visitante']:.2f}")
            print(f"Probabilidades: V={res['prob_vitoria']:.3f}, E={res['prob_empate']:.3f}, D={res['prob_derrota']:.3f}")
        except Exception as e:
            print(f"Erro em {t1} x {t2}: {e}")

if __name__ == "__main__":
    testar_previsoes()
