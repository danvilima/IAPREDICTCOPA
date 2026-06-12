import io
import pandas as pd
from db import get_engine, get_raw_connection

# Constantes da feature
DATA_CORTE_HISTORICO = "2006-01-01"
DATA_INICIO_COPA_2026 = "2026-06-11"
TORNEIO_COPA = "FIFA World Cup"
TORNEIO_AMISTOSO = "Friendly"

MAPA_SELECOES = {
    # "USA": "United States",
}

COLUNAS_NEGOCIO = [
    "data",
    "time_casa",
    "time_visitante",
    "gols_casa",
    "gols_visitante",
    "torneio",
    "cidade",
    "pais",
    "neutro",
]

def main():
    print("Conectando ao banco de dados para ler bronze_jogos...")
    engine = get_engine()
    
    # 1. Ler todos os dados da Bronze
    query = "SELECT * FROM bronze_jogos"
    df = pd.read_sql(query, engine)
    
    # Remover ID vindo do banco pois geraremos os novos
    if "id" in df.columns:
        df = df.drop(columns=["id"])
    
    # 2. Corrigir e garantir tipos
    df["data"] = pd.to_datetime(df["data"]).dt.date
    df["gols_casa"] = df["gols_casa"].astype("Int64")
    df["gols_visitante"] = df["gols_visitante"].astype("Int64")
    df["neutro"] = df["neutro"].astype(bool)
    
    # Garantir que textos básicos sejam strings
    for col in ["time_casa", "time_visitante", "torneio", "cidade", "pais"]:
        df[col] = df[col].astype(str)
    
    # 3. Padronizar nomes de seleções
    df["time_casa"] = df["time_casa"].str.strip().replace(MAPA_SELECOES)
    df["time_visitante"] = df["time_visitante"].str.strip().replace(MAPA_SELECOES)
    
    # 4. Padronizar textos básicos
    df["torneio"] = df["torneio"].str.strip()
    df["cidade"] = df["cidade"].str.strip()
    df["pais"] = df["pais"].str.strip()
    
    # 5. Remover duplicatas exatas
    df = df.drop_duplicates(subset=COLUNAS_NEGOCIO).copy()
    
    # 6. Criar coluna eh_amistoso
    df["eh_amistoso"] = df["torneio"].eq(TORNEIO_AMISTOSO)
    
    # 7. Separação anti-leakage
    mask_copa2026 = (
        (df["torneio"] == TORNEIO_COPA)
        & (pd.to_datetime(df["data"]) >= pd.to_datetime(DATA_INICIO_COPA_2026))
    )
    
    mask_historico = (
        (pd.to_datetime(df["data"]) >= pd.to_datetime(DATA_CORTE_HISTORICO))
        & df["gols_casa"].notna()
        & df["gols_visitante"].notna()
        & (~mask_copa2026)
    )
    
    df_copa2026 = df[mask_copa2026].copy()
    df_jogos = df[mask_historico].copy()
    
    print("\n--- Relatório Silver ---")
    print(f"Total de linhas lidas da Bronze: {len(df)}")
    print(f"Linhas em silver_jogos (histórico >2006, sem Copa 2026): {len(df_jogos)}")
    print(f"Linhas em silver_copa2026 (Copa 2026 apenas): {len(df_copa2026)}")
    print("------------------------\n")
    
    # 10. Gravação idempotente
    print("Conectando ao banco para gravar tabelas Silver...")
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            tabelas = ["silver_jogos", "silver_copa2026"]
            for tb in tabelas:
                print(f"Recriando tabela {tb}...")
                cur.execute(f"DROP TABLE IF EXISTS {tb};")
                cur.execute(f"""
                    CREATE TABLE {tb} (
                        id bigint generated always as identity primary key,
                        data date,
                        time_casa text,
                        time_visitante text,
                        gols_casa integer,
                        gols_visitante integer,
                        torneio text,
                        cidade text,
                        pais text,
                        neutro boolean,
                        eh_amistoso boolean
                    );
                """)
            
            def load_df_via_copy(df_to_load, table_name):
                print(f"Carregando {table_name} via COPY...")
                buffer = io.StringIO()
                df_to_load.to_csv(buffer, index=False, header=False, na_rep="")
                buffer.seek(0)
                cur.copy_expert(
                    sql=f"COPY {table_name} (data, time_casa, time_visitante, gols_casa, gols_visitante, torneio, cidade, pais, neutro, eh_amistoso) FROM STDIN WITH (FORMAT csv, NULL '')",
                    file=buffer,
                )
            
            load_df_via_copy(df_jogos, "silver_jogos")
            load_df_via_copy(df_copa2026, "silver_copa2026")
            
        conn.commit()
        print("Carga Silver concluída com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao carregar dados Silver: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
