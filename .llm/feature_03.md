# Feature 03 — Pesos: torneio + recência

## Contexto

Nem todo jogo deve ter o mesmo impacto no modelo.

Um jogo de Copa do Mundo recente deve influenciar mais o aprendizado do que um amistoso antigo. Por isso, esta feature cria duas colunas de ponderação:

```text
peso_torneio
peso_recencia
```

Essas colunas serão usadas nas próximas etapas para ponderar o treinamento do modelo.

Importante: esses pesos medem a importância da amostra no treino. Eles não devem ser tratados como características reais de uma partida futura.

## Objetivo

Ler `silver_jogos` e gerar a tabela:

```text
silver_ponderado
```

A nova tabela deve conter todas as colunas de `silver_jogos` mais:

```text
peso_torneio
peso_recencia
```

## Entrada

Tabela:

```text
silver_jogos
```

Colunas esperadas:

```text
id
data
time_casa
time_visitante
gols_casa
gols_visitante
torneio
cidade
pais
neutro
eh_amistoso
```

## Saída

Tabela:

```text
silver_ponderado
```

Colunas:

```text
id
jogo_id
data
time_casa
time_visitante
gols_casa
gols_visitante
torneio
cidade
pais
neutro
eh_amistoso
peso_torneio
peso_recencia
```

Observação:

```text
jogo_id = id original de silver_jogos
id = chave primária própria de silver_ponderado
```

Isso ajuda a manter rastreabilidade entre as camadas.

## Constantes da feature

```python
DATA_REF = "2026-06-11"
MEIA_VIDA_ANOS = 5
```

A data de referência é o início da Copa 2026. Ela serve como âncora para o cálculo da recência.

## Requisitos

### 1. Ler dados da Silver

Ler todos os dados de:

```sql
SELECT *
FROM silver_jogos;
```

A Feature 03 deve usar somente `silver_jogos`.

Não usar:

```text
bronze_jogos
silver_copa2026
```

### 2. Criar `jogo_id`

Antes de gravar a nova tabela, preservar o ID original de `silver_jogos` em uma nova coluna:

```python
df["jogo_id"] = df["id"]
```

A tabela `silver_ponderado` terá um novo `id` próprio, mas `jogo_id` permitirá fazer rastreio até `silver_jogos`.

### 3. Classificar `peso_torneio`

Criar a coluna:

```text
peso_torneio
```

Ela deve assumir apenas os valores:

```text
1, 2 ou 3
```

A classificação deve ser feita pelo nome do torneio.

### 4. Regra de classificação dos torneios

A classificação deve respeitar esta ordem:

### Nível 3 — peso máximo

Usar igualdade exata para:

```text
FIFA World Cup
Confederations Cup
CONMEBOL–UEFA Cup of Champions
CONMEBOL-UEFA Cup of Champions
```

Peso:

```text
3
```

Observação: considerar tanto o traço `–` quanto o hífen `-`, porque o dataset pode variar.

### Nível 2 — peso intermediário

Peso 2 quando o nome do torneio:

1. contém `qualification`, ignorando maiúsculas/minúsculas;
2. contém `nations league`, ignorando maiúsculas/minúsculas;
3. ou está exatamente em um destes torneios continentais:

```text
UEFA Euro
Copa América
African Cup of Nations
AFC Asian Cup
Gold Cup
Oceania Nations Cup
```

Peso:

```text
2
```

### Nível 1 — peso baixo

Todos os demais torneios recebem peso 1.

Isso inclui:

```text
Friendly
torneios menores
torneios regionais
competições de cauda longa
```

Peso:

```text
1
```

### 5. Função sugerida para classificação

A classificação deve limpar espaços extras antes da comparação.

Exemplo:

```python
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
```

### 6. Calcular `peso_recencia`

Criar a coluna:

```text
peso_recencia
```

Usar decaimento exponencial com meia-vida de 5 anos:

```python
peso_recencia = 0.5 ** (idade_anos / 5)
```

Onde:

```python
idade_anos = (DATA_REF - data).days / 365.25
```

### 7. Proteger contra datas futuras

Como a referência é `2026-06-11`, qualquer jogo com data posterior poderia gerar idade negativa e `peso_recencia > 1`.

Para evitar isso, aplicar limite inferior em `idade_anos`:

```python
idade_anos = max(0, idade_anos)
```

Em pandas:

```python
df["idade_anos"] = (
    (DATA_REF - df["data"]).dt.days / 365.25
).clip(lower=0)

df["peso_recencia"] = 0.5 ** (df["idade_anos"] / MEIA_VIDA_ANOS)
```

Assim, o peso de recência sempre ficará no intervalo:

```text
0 < peso_recencia <= 1
```

### 8. Não normalizar os pesos

Não normalizar `peso_torneio`.

Não normalizar `peso_recencia`.

Eles devem permanecer como pesos relativos.

Errado:

```python
df["peso_recencia"] = df["peso_recencia"] / df["peso_recencia"].max()
```

Certo:

```python
df["peso_recencia"] = 0.5 ** (df["idade_anos"] / 5)
```

### 9. Não calcular força de seleção nesta feature

A Feature 03 não deve calcular:

```text
ELO
ranking
média de gols
aproveitamento
força ofensiva
força defensiva
probabilidade de vitória
```

Ela apenas adiciona pesos aos jogos.

### 10. Uso correto nas próximas features

As colunas criadas aqui devem ser usadas com cuidado.

Uso correto:

```text
peso_torneio
peso_recencia
```

como peso de amostra no treino.

Exemplo:

```python
peso_amostra = peso_torneio * peso_recencia
```

Uso incorreto:

```text
usar peso_torneio e peso_recencia como features comuns de previsão
```

Ou seja, na modelagem Poisson, essas colunas não devem ser passadas como informação do jogo futuro. Elas indicam apenas o quanto cada jogo histórico importa durante o treinamento.

## Schema da tabela

```sql
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
```

## Critérios de aceite

A Feature 03 será considerada correta quando:

1. `silver_ponderado` tiver o mesmo número de linhas de `silver_jogos`.
2. `peso_torneio` assumir somente os valores `1`, `2` e `3`.
3. `peso_recencia` estiver sempre no intervalo `0 < peso_recencia <= 1`.
4. Jogos mais recentes tiverem `peso_recencia` maior que jogos antigos.
5. Jogos de torneios mais importantes tiverem `peso_torneio` maior.
6. A tabela preservar o vínculo com `silver_jogos` por meio de `jogo_id`.
7. Nenhum jogo da Copa 2026 futura entrar nesta tabela.
8. Nenhuma coluna necessária da Silver for perdida.
9. Os pesos não forem normalizados.
10. Os pesos forem documentados como pesos de treino, não como features preditivas futuras.

## Verificação SQL

### Verificar quantidade de linhas

```sql
SELECT
    (SELECT COUNT(*) FROM silver_jogos) AS silver_jogos,
    (SELECT COUNT(*) FROM silver_ponderado) AS silver_ponderado;
```

Os dois valores devem ser iguais.

### Verificar distribuição de `peso_torneio`

```sql
SELECT peso_torneio, COUNT(*)
FROM silver_ponderado
GROUP BY peso_torneio
ORDER BY peso_torneio;
```

Resultado esperado:

```text
somente 1, 2 e 3
```

Referência aproximada:

```text
nível 1 ≈ 9.192
nível 2 ≈ 10.085
nível 3 ≈ 369
```

Os valores podem variar se o dataset for atualizado.

### Verificar intervalo de `peso_recencia`

```sql
SELECT MIN(peso_recencia) AS menor_peso,
       MAX(peso_recencia) AS maior_peso
FROM silver_ponderado;
```

Resultado esperado:

```text
menor_peso > 0
maior_peso <= 1
```

### Verificar jogos mais recentes

```sql
SELECT data,
       time_casa,
       time_visitante,
       torneio,
       peso_torneio,
       ROUND(peso_recencia::numeric, 4) AS peso_recencia
FROM silver_ponderado
ORDER BY data DESC, id DESC
LIMIT 10;
```

Jogos mais próximos de `2026-06-11` devem ter `peso_recencia` próximo de 1.

### Verificar jogos mais antigos da Silver

```sql
SELECT data,
       time_casa,
       time_visitante,
       torneio,
       peso_torneio,
       ROUND(peso_recencia::numeric, 4) AS peso_recencia
FROM silver_ponderado
ORDER BY data ASC, id ASC
LIMIT 10;
```

Jogos de 2006 devem ter `peso_recencia` bem menor.

### Verificar se não há Copa 2026 futura

```sql
SELECT COUNT(*)
FROM silver_ponderado
WHERE torneio = 'FIFA World Cup'
  AND data >= '2026-06-11';
```

Resultado esperado:

```text
0
```

### Verificar nulos

```sql
SELECT COUNT(*)
FROM silver_ponderado
WHERE peso_torneio IS NULL
   OR peso_recencia IS NULL;
```

Resultado esperado:

```text
0
```

### Verificar vínculo com `silver_jogos`

```sql
SELECT COUNT(*)
FROM silver_ponderado p
LEFT JOIN silver_jogos s
  ON s.id = p.jogo_id
WHERE s.id IS NULL;
```

Resultado esperado:

```text
0
```

## Plano de implementação

1. Ler `silver_jogos`.
2. Criar `jogo_id` a partir do `id` original.
3. Garantir que `data` está em formato datetime.
4. Aplicar `strip()` em `torneio`.
5. Criar função `classificar_peso_torneio`.
6. Gerar `peso_torneio`.
7. Definir `DATA_REF = 2026-06-11`.
8. Calcular `idade_anos`.
9. Aplicar `clip(lower=0)` para evitar idade negativa.
10. Calcular `peso_recencia`.
11. Validar:

    * sem nulos;
    * `peso_torneio` somente em `{1, 2, 3}`;
    * `peso_recencia` em `(0, 1]`;
    * mesma quantidade de linhas de `silver_jogos`.
12. Gravar `silver_ponderado` com `DROP + CREATE + COPY`.

## Para explicar enquanto desenvolve

* `peso_torneio` mede a importância competitiva da partida.
* `peso_recencia` mede o quanto a partida ainda é atual.
* O decaimento exponencial é melhor que uma regra rígida porque reduz o peso aos poucos.
* Um jogo recente não apaga um jogo antigo, apenas pesa mais.
* A Feature 03 ainda não calcula probabilidade nem força de seleção.
* Esses pesos serão usados para ponderar o treino, não para dizer diretamente quem vence uma partida.
