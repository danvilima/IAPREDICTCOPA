import io
import pandas as pd
from db import get_engine, get_raw_connection

DATA_REF = "2026-06-11"
MEIA_VIDA_ANOS = 5

NIVEL_3 = {
    "FIFA World Cup",
    "Confederations Cup",
    "CONMEBOL–UEFA Cup of Champions",
    "CONMEBOL-UEFA Cup of Champions",
}

CONTINENTAIS = {
    "UEFA Euro",
    "Copa América",
    "African Cup of Nations",
    "AFC Asian Cup",
    "Gold Cup",
    "Oceania Nations Cup",
}

def classificar_peso_torneio(torneio: str) -> int:
    torneio = str(torneio).strip()
    torneio_lower = torneio.lower()

    if torneio in NIVEL_3:
        return 3

    if (
        "qualification" in torneio_lower
        or "nations league" in torneio_lower
        or torneio in CONTINENTAIS
    ):
        return 2

    return 1

def main():
    print("Conectando ao banco para ler silver_jogos...")
    engine = get_engine()
    
    query = """
        SELECT id, data, time_casa, time_visitante, gols_casa, gols_visitante, 
               torneio, cidade, pais, neutro, eh_amistoso
        FROM silver_jogos
    """
    df = pd.read_sql(query, engine)
    
    # 2. Rastreabilidade
    df["jogo_id"] = df["id"]
    df = df.drop(columns=["id"])
    
    # Garantir tipagem de data
    df["data"] = pd.to_datetime(df["data"])
    
    # 4. Strip do torneio e Classificação
    print("Calculando peso_torneio...")
    df["torneio"] = df["torneio"].astype(str).str.strip()
    df["peso_torneio"] = df["torneio"].apply(classificar_peso_torneio)
    
    print("Calculando peso_recencia...")
    data_ref = pd.to_datetime(DATA_REF)
    df["idade_anos"] = ((data_ref - df["data"]).dt.days / 365.25).clip(lower=0)
    df["peso_recencia"] = 0.5 ** (df["idade_anos"] / MEIA_VIDA_ANOS)
    
    print("\n--- Relatório Pesos ---")
    print(df["peso_torneio"].value_counts().sort_index())
    print("\nAmostra peso_recencia (5 mais recentes):")
    print(df[["data", "peso_recencia"]].sort_values("data", ascending=False).head(5))
    print("-----------------------\n")
    
    # Garantir nulos não se convertam em string nos gols, mantendo formatação
    df["gols_casa"] = df["gols_casa"].astype("Int64")
    df["gols_visitante"] = df["gols_visitante"].astype("Int64")
    
    print("Gravando tabela silver_ponderado...")
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS silver_ponderado;")
            cur.execute("""
                CREATE TABLE silver_ponderado (
                    id bigint generated always as identity primary key,
                    jogo_id bigint,
                    data date,
                    time_casa text,
                    time_visitante text,
                    gols_casa integer,
                    gols_visitante integer,
                    torneio text,
                    cidade text,
                    pais text,
                    neutro boolean,
                    eh_amistoso boolean,
                    peso_torneio integer,
                    peso_recencia double precision
                );
            """)
            
            # Ordenar colunas para o COPY
            colunas_copy = [
                "jogo_id", "data", "time_casa", "time_visitante", 
                "gols_casa", "gols_visitante", "torneio", "cidade", 
                "pais", "neutro", "eh_amistoso", "peso_torneio", "peso_recencia"
            ]
            df_to_copy = df[colunas_copy]
            
            buffer = io.StringIO()
            df_to_copy.to_csv(buffer, index=False, header=False, na_rep="")
            buffer.seek(0)
            
            cur.copy_expert(
                sql="COPY silver_ponderado (jogo_id, data, time_casa, time_visitante, gols_casa, gols_visitante, torneio, cidade, pais, neutro, eh_amistoso, peso_torneio, peso_recencia) FROM STDIN WITH (FORMAT csv, NULL '')",
                file=buffer,
            )
            
        conn.commit()
        print("Tabela silver_ponderado criada com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar silver_ponderado: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
