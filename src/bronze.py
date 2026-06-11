import os
import sys
import io
import pandas as pd
from db import get_raw_connection


def main():
    # 1. Ler o caminho do CSV
    caminho_csv = os.environ.get("CAMINHO_CSV", "data/results.csv")
    if len(sys.argv) > 1:
        caminho_csv = sys.argv[1]

    print(f"Lendo dados de: {caminho_csv}")

    # 2. Ler o CSV com pandas
    df = pd.read_csv(caminho_csv, parse_dates=["date"])

    # 3. Transformações mínimas (tipos e renomear)
    # Converter gols para Int64 (inteiro com suporte a nulos)
    df["home_score"] = df["home_score"].astype("Int64")
    df["away_score"] = df["away_score"].astype("Int64")

    # Converter neutral para bool
    df["neutral"] = df["neutral"].astype(bool)

    # Renomear colunas
    mapa_colunas = {
        "date": "data",
        "home_team": "time_casa",
        "away_team": "time_visitante",
        "home_score": "gols_casa",
        "away_score": "gols_visitante",
        "tournament": "torneio",
        "city": "cidade",
        "country": "pais",
        "neutral": "neutro",
    }
    df = df.rename(columns=mapa_colunas)

    # 4. Imprimir inventário
    print("\n--- Inventário ---")
    print(f"Total de linhas: {len(df)}")
    print("\nTipos e nulos:")
    inventario = pd.DataFrame(
        {"Tipo": df.dtypes, "% Nulos": (df.isnull().sum() / len(df) * 100).round(2)}
    )
    print(inventario)
    print("------------------\n")

    # 5. Gravar bronze_jogos
    print("Conectando ao banco de dados...")
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            # Idempotência: DROP + CREATE
            print("Criando tabela bronze_jogos...")
            cur.execute("DROP TABLE IF EXISTS bronze_jogos;")
            cur.execute(
                """
                CREATE TABLE bronze_jogos (
                    id bigint generated always as identity primary key,
                    data date,
                    time_casa text,
                    time_visitante text,
                    gols_casa integer,
                    gols_visitante integer,
                    torneio text,
                    cidade text,
                    pais text,
                    neutro boolean
                );
            """
            )

            # Carregar via COPY
            print("Carregando dados via COPY...")

            # Precisamos salvar o dataframe em um buffer CSV na memória
            buffer = io.StringIO()
            # Na=NULL: o psycopg2 lerá strings vazias como null se passarmos null='' no COPY
            # Mas o df.to_csv com index=False vai imprimir campos vazios para nulos.
            # O PostgreSQL (COPY) vai interpretar campos vazios (,,) como NULL.
            df.to_csv(buffer, index=False, header=False, na_rep="")
            buffer.seek(0)

            cur.copy_expert(
                sql="COPY bronze_jogos (data, time_casa, time_visitante, gols_casa, gols_visitante, torneio, cidade, pais, neutro) FROM STDIN WITH (FORMAT csv, NULL '')",
                file=buffer,
            )

        conn.commit()
        print("Carga concluída com sucesso!")
    except Exception as e:
        conn.rollback()
        print(f"Erro ao carregar dados: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
