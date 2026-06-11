from src.db import get_engine


def main():
    try:
        engine = get_engine()

        with engine.connect() as conn:
            print("Conexão OK com o banco!")

    except Exception as e:
        print("Erro ao conectar no banco:")
        print(e)


if __name__ == "__main__":
    main()
