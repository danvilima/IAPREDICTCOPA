import sys
import os
import pandas as pd
import pickle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from db import get_raw_connection

def run_diagnostics():
    conn = get_raw_connection()
    try:
        print("--- 1. Ranking de ELO Atual ---")
        df_elo = pd.read_sql("""
            SELECT selecao, ROUND(elo::numeric, 0) AS elo
            FROM silver_elo_atual
            ORDER BY elo DESC
            LIMIT 30;
        """, conn)
        print(df_elo.to_string())
        
        print("\n--- 2. Colunas do Modelo (pickle) ---")
        with open("models/colunas_atributos.pkl", "rb") as f:
            print(pickle.load(f))
            
        print("\n--- 4. Lambdas e Probabilidades (Primeiros 20 Jogos) ---")
        df_lambdas = pd.read_sql("""
            SELECT
                time_casa,
                time_visitante,
                ROUND(gols_esperados_casa::numeric, 2) AS xg_casa,
                ROUND(gols_esperados_visitante::numeric, 2) AS xg_visitante,
                ROUND(prob_vitoria::numeric, 3) AS p_vitoria,
                ROUND(prob_empate::numeric, 3) AS p_empate,
                ROUND(prob_derrota::numeric, 3) AS p_derrota
            FROM previsoes
            ORDER BY data, id
            LIMIT 20;
        """, conn)
        print(df_lambdas.to_string())
        
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    import warnings
    warnings.filterwarnings('ignore')
    run_diagnostics()
