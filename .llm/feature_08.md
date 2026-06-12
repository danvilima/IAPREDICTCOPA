# Feature 08 — Monte Carlo: simulação do torneio

## Contexto

Uma simulação isolada da Copa não significa quase nada, porque é apenas um caminho possível.

Mas quando repetimos o torneio milhares de vezes, a frequência com que cada seleção alcança cada fase pode ser interpretada como probabilidade estimada.

Esta feature usa Monte Carlo para simular a Copa do Mundo 2026 muitas vezes e gerar uma tabela final de probabilidades por seleção.

## Objetivo

Simular a Copa 2026 várias vezes e gravar a probabilidade de cada seleção alcançar cada fase.

A saída principal será:

```text
gold_probabilidades_copa
```

Essa tabela será usada pelo dashboard para mostrar o “palpite da máquina”.

## Entrada

A Feature 08 usa quatro tipos de entrada.

### 1. Jogos da fase de grupos

Tabela:

```text
silver_copa2026
```

Contém os 72 jogos da fase de grupos da Copa 2026.

Colunas importantes:

```text
data
time_casa
time_visitante
neutro
```

### 2. Grupos da Copa

Arquivo:

```text
data/grupos_copa2026.csv
```

Colunas esperadas:

```text
group
position
nation
```

Exemplo:

```text
A,1,Mexico
A,2,South Africa
A,3,South Korea
A,4,Denmark
```

### 3. Calendário do mata-mata

Arquivo:

```text
data/calendario_copa2026.csv
```

Contém os jogos do mata-mata, de M73 até M104.

Colunas esperadas, conforme o projeto:

```text
match
round
home_slot
away_slot
winner_advances_to
loser_advances_to
```

Os slots podem ter formatos como:

```text
1A
2B
3ABCD
W73
RU101
```

### 4. Modelos e módulos

Arquivos/modelos:

```text
models/modelo_poisson_casa.pkl
models/modelo_poisson_visitante.pkl
models/colunas_atributos.pkl
```

Módulos:

```text
src/previsao.py
src/poisson.py
src/monte_carlo.py
```

A simulação deve usar a função `prever_jogo` corrigida na Feature 07.

Importante:

```text
prever_jogo não recebe peso_torneio.
prever_jogo não recebe peso_recencia.
```

## Saída

Tabela:

```text
gold_probabilidades_copa
```

Colunas:

```text
id
selecao
prob_grupo
prob_oitavas
prob_quartas
prob_semi
prob_final
prob_campea
```

Cada linha representa uma das 48 seleções.

## Interpretação das probabilidades

As colunas significam:

```text
prob_grupo   = probabilidade de passar da fase de grupos e chegar ao R32
prob_oitavas = probabilidade de vencer o R32 e chegar ao R16
prob_quartas = probabilidade de vencer o R16 e chegar às quartas
prob_semi    = probabilidade de vencer as quartas e chegar à semifinal
prob_final   = probabilidade de vencer a semifinal e chegar à final
prob_campea  = probabilidade de vencer a final
```

Observação:

```text
prob_grupo não significa disputar a fase de grupos.
Todas as seleções disputam a fase de grupos.
prob_grupo significa passar da fase de grupos.
```

## Constantes da feature

Usar:

```python
N_SIMULACOES = 60000
SEED = 42
MAX_GOLS = 10
```

Para testes rápidos durante desenvolvimento, pode existir uma constante separada:

```python
N_SIMULACOES_TESTE = 1000
```

Mas a geração oficial de `gold_probabilidades_copa` deve usar:

```python
N_SIMULACOES = 60000
```

Motivo:

```text
1000 simulações é pouco para estimar probabilidade de campeão com estabilidade.
60000 simulações reduzem bastante o ruído.
```

Se o tempo de execução ficar aceitável, pode usar:

```python
N_SIMULACOES = 100000
```

## Requisitos

### 1. Usar gerador aleatório reprodutível

Usar o gerador moderno do NumPy:

```python
rng = np.random.default_rng(SEED)
```

Não usar aleatoriedade global com:

```python
np.random.seed(42)
```

A versão pré-computada deve ser reprodutível.

A simulação ao vivo do Streamlit, na Feature 09, não deve usar seed fixa.

### 2. Carregar as 48 seleções

As seleções devem vir de:

```text
data/grupos_copa2026.csv
```

A tabela final deve ter exatamente:

```text
48 linhas
```

Uma para cada seleção.

### 3. Simular os 72 jogos da fase de grupos

Para cada jogo de `silver_copa2026`:

1. buscar `time_casa`;
2. buscar `time_visitante`;
3. buscar `neutro`;
4. obter os gols esperados com `prever_jogo`;
5. sortear placar usando Poisson.

Exemplo:

```python
prev = prever_jogo(time_casa, time_visitante, neutro=True)

gols_casa = rng.poisson(prev["gols_esperados_casa"])
gols_visitante = rng.poisson(prev["gols_esperados_visitante"])
```

Como a Copa é em campo neutro, a função `prever_jogo` deve usar a simetrização definida na Feature 07.

### 4. Cachear lambdas dos confrontos

A simulação chama a previsão muitas vezes. Para evitar recalcular os modelos repetidamente, criar cache de lambdas.

Chave sugerida:

```python
chave = (time_casa, time_visitante, bool(neutro))
```

Exemplo:

```python
cache_lambdas = {}

def obter_lambdas(time_casa, time_visitante, neutro):
    chave = (time_casa, time_visitante, bool(neutro))

    if chave not in cache_lambdas:
        prev = prever_jogo(time_casa, time_visitante, neutro=neutro)
        cache_lambdas[chave] = (
            prev["gols_esperados_casa"],
            prev["gols_esperados_visitante"],
        )

    return cache_lambdas[chave]
```

Esse cache deve ser usado tanto na fase de grupos quanto no mata-mata.

### 5. Adicionar função de sorteio em `src/poisson.py`

O módulo `src/poisson.py` já contém a grade de probabilidades.

Adicionar também uma função de sorteio de placar:

```python
def sortear_placar(lambda_casa, lambda_visitante, rng):
    gols_casa = rng.poisson(lambda_casa)
    gols_visitante = rng.poisson(lambda_visitante)
    return int(gols_casa), int(gols_visitante)
```

A simulação deve usar essa função para manter a lógica centralizada.

### 6. Classificação da fase de grupos

Para cada grupo, criar uma tabela com:

```text
selecao
jogos
vitorias
empates
derrotas
gols_pro
gols_contra
saldo_gols
pontos
```

Pontuação:

```text
vitória = 3 pontos
empate = 1 ponto
derrota = 0 pontos
```

Critérios de ordenação:

```text
1. pontos
2. saldo de gols
3. gols pró
4. sorteio aleatório
```

O sorteio aleatório deve usar o mesmo `rng`, não `random` global.

Exemplo:

```python
tabela["sorteio"] = rng.random(len(tabela))
```

Ordenação:

```python
tabela = tabela.sort_values(
    ["pontos", "saldo_gols", "gols_pro", "sorteio"],
    ascending=[False, False, False, False]
)
```

### 7. Classificar 1º, 2º e 3º de cada grupo

Após ordenar cada grupo:

```text
1º colocado → slot 1A, 1B, ..., 1L
2º colocado → slot 2A, 2B, ..., 2L
3º colocado → candidato a melhor terceiro
```

Criar um dicionário de slots:

```python
slots["1A"] = vencedor_do_grupo_A
slots["2A"] = segundo_do_grupo_A
```

Guardar também os 12 terceiros para o ranking geral.

### 8. Escolher os 8 melhores terceiros

Rankear os 12 terceiros usando o mesmo critério:

```text
1. pontos
2. saldo de gols
3. gols pró
4. sorteio aleatório
```

Selecionar os 8 primeiros.

Esses 8 devem entrar no mata-mata.

### 9. Mapear melhores terceiros para os slots `3xxxx`

Os slots de terceiros no calendário podem aparecer como:

```text
3ABCD
3EFGH
3IJKL
```

Cada slot indica quais grupos são elegíveis para aquela vaga.

Exemplo:

```text
3ABCD aceita terceiros dos grupos A, B, C ou D.
```

Criar função própria:

```python
def slots_terceiros(melhores_terceiros, calendario, rng):
    ...
```

Essa função deve:

1. identificar todos os slots do calendário que começam com `3`;
2. extrair os grupos elegíveis de cada slot;
3. montar matriz de custo;
4. usar `scipy.optimize.linear_sum_assignment`;
5. garantir que cada terceiro seja usado uma única vez;
6. garantir que cada slot receba uma seleção válida.

### 10. Matching bipartido dos terceiros

Usar:

```python
from scipy.optimize import linear_sum_assignment
```

Matriz de custo:

```text
custo alto para terceiro inelegível
custo baixo para terceiro elegível
```

Para evitar arbitrariedade forte, o custo pode considerar a posição do terceiro no ranking e a ordem do slot.

Exemplo conceitual:

```python
CUSTO_INVALIDO = 10**9
```

Se o terceiro é elegível ao slot:

```python
custo = ranking_terceiro * 100 + ordem_slot
```

Se não é elegível:

```python
custo = CUSTO_INVALIDO
```

Depois do matching, validar que nenhum custo inválido foi selecionado.

Se não existir matching válido, a simulação deve parar com erro claro.

### 11. Preencher slots do mata-mata

Antes do mata-mata, o dicionário de slots deve conter:

```text
1A, 2A, ..., 1L, 2L
slots de terceiros, como 3ABCD, 3EFGH etc.
```

Durante o mata-mata, adicionar:

```text
W73, W74, ...
RU101, RU102
```

Onde:

```text
W = winner, vencedor da partida
RU = runner-up, perdedor da semifinal
```

### 12. Resolver slots do calendário

Criar função:

```python
def resolver_slot(slot, slots):
    ...
```

Ela deve receber textos como:

```text
1A
2B
3ABCD
W73
RU101
```

E retornar a seleção correspondente.

Se o slot não existir no dicionário, lançar erro claro.

### 13. Simular mata-mata em ordem

Processar as partidas do calendário em ordem de rodada e número do jogo.

Ordem esperada:

```text
R32
R16
QF
SF
Third Place
Final
```

Ou conforme os nomes do arquivo:

```text
Round of 32
Round of 16
Quarter-finals
Semi-finals
Third-place match
Final
```

O importante é respeitar a ordem dos jogos.

### 14. Mata-mata em campo neutro

Todos os jogos de mata-mata devem ser simulados com:

```python
neutro = True
```

A previsão deve usar a função simetrizada da Feature 07.

### 15. Empate no mata-mata

Se o placar sorteado terminar empatado, o vencedor será decidido nos pênaltis.

Em vez de usar 50/50 puro, aplicar leve vantagem por ELO.

Função sugerida:

```python
def prob_penaltis(time_a, time_b, elos):
    diff = elos[time_a] - elos[time_b]
    p = 0.5 + diff / 2000
    return float(np.clip(p, 0.40, 0.60))
```

Interpretação:

```text
Se os ELOs forem iguais, p = 0.50.
Se um time for mais forte, pode chegar perto de 0.55 ou 0.60.
O limite evita que pênaltis deixem de ser aleatórios.
```

Uso:

```python
p_a = prob_penaltis(time_a, time_b, elos)

if rng.random() < p_a:
    vencedor = time_a
    perdedor = time_b
else:
    vencedor = time_b
    perdedor = time_a
```

Também marcar que a decisão foi nos pênaltis, pois a Feature 09 pode exibir isso na simulação ao vivo.

### 16. Registrar avanço por fase

A cada simulação, contar quais seleções alcançaram cada fase.

Contadores:

```text
grupo
oitavas
quartas
semi
final
campea
```

Interpretação:

```text
grupo   → passou da fase de grupos e chegou ao R32
oitavas → venceu o R32 e chegou ao R16
quartas → venceu o R16 e chegou ao QF
semi    → venceu o QF e chegou ao SF
final   → venceu o SF e chegou à final
campea  → venceu a final
```

Em cada simulação, os totais devem ser:

```text
grupo   = 32 seleções
oitavas = 16 seleções
quartas = 8 seleções
semi    = 4 seleções
final   = 2 seleções
campea  = 1 seleção
```

### 17. Simular N vezes

Rodar:

```python
for i in range(N_SIMULACOES):
    resultado = simular_torneio(...)
    acumular_resultado(resultado)
```

Com:

```python
N_SIMULACOES = 60000
```

### 18. Converter contagens em probabilidades

Depois de todas as simulações:

```python
prob = contagem / N_SIMULACOES
```

Exemplo:

```python
prob_campea = contagem_campea[selecao] / N_SIMULACOES
```

As probabilidades devem ficar em escala 0–1, não 0–100.

Exemplo:

```text
0.153 = 15,3%
```

### 19. Validar monotonicidade

Para cada seleção, deve valer:

```text
prob_grupo >= prob_oitavas >= prob_quartas >= prob_semi >= prob_final >= prob_campea
```

Se isso não acontecer, a contagem de fases está errada.

### 20. Validar somas globais

Após gerar a tabela:

```text
SUM(prob_grupo)   ≈ 32
SUM(prob_oitavas) ≈ 16
SUM(prob_quartas) ≈ 8
SUM(prob_semi)    ≈ 4
SUM(prob_final)   ≈ 2
SUM(prob_campea)  ≈ 1
```

E:

```text
SUM(prob_campea * 100) ≈ 100%
```

### 21. Gravar tabela final

Gravar:

```text
gold_probabilidades_copa
```

A gravação deve ser idempotente:

```sql
DROP TABLE IF EXISTS gold_probabilidades_copa;
CREATE TABLE gold_probabilidades_copa (...);
COPY ...
```

## Schema da tabela

```sql
CREATE TABLE gold_probabilidades_copa (
    id bigint generated always as identity primary key,
    selecao text,
    prob_grupo double precision,
    prob_oitavas double precision,
    prob_quartas double precision,
    prob_semi double precision,
    prob_final double precision,
    prob_campea double precision
);
```

## Critérios de aceite

A Feature 08 será considerada correta quando:

1. `gold_probabilidades_copa` tiver exatamente 48 linhas.

2. A soma de `prob_campea` for aproximadamente 1.

3. A soma de `prob_grupo` for aproximadamente 32.

4. A soma de `prob_oitavas` for aproximadamente 16.

5. A soma de `prob_quartas` for aproximadamente 8.

6. A soma de `prob_semi` for aproximadamente 4.

7. A soma de `prob_final` for aproximadamente 2.

8. Para cada seleção, as probabilidades forem monotônicas:

   * `prob_grupo >= prob_oitavas >= prob_quartas >= prob_semi >= prob_final >= prob_campea`

9. As favoritas aparecerem de forma coerente no topo.

10. A simulação usar `prever_jogo` corrigida, sem `peso_torneio` e sem `peso_recencia`.

11. Jogos neutros usarem previsão simetrizada.

12. Mata-mata usar leve vantagem por ELO nos pênaltis.

13. O matching dos terceiros respeitar os slots elegíveis.

14. O resultado for reprodutível com `SEED = 42`.

15. A versão oficial usar pelo menos `N_SIMULACOES = 60000`.

## Verificação SQL

### Top 10 campeãs

```sql
SELECT
    selecao,
    ROUND((prob_campea * 100)::numeric, 2) AS pct_campea
FROM gold_probabilidades_copa
ORDER BY prob_campea DESC
LIMIT 10;
```

Resultado esperado:

```text
seleções favoritas no topo, como Espanha, Argentina, França, Brasil, Inglaterra, Portugal, Alemanha, Holanda etc.
```

A ordem exata pode variar, mas o topo precisa fazer sentido.

### Total da probabilidade de campeã

```sql
SELECT ROUND(SUM(prob_campea)::numeric, 4) AS total
FROM gold_probabilidades_copa;
```

Resultado esperado:

```text
aproximadamente 1.0000
```

### Total em percentual

```sql
SELECT ROUND((SUM(prob_campea) * 100)::numeric, 2) AS total_pct
FROM gold_probabilidades_copa;
```

Resultado esperado:

```text
aproximadamente 100.00
```

### Soma de classificados por fase

```sql
SELECT
    ROUND(SUM(prob_grupo)::numeric, 2) AS grupo,
    ROUND(SUM(prob_oitavas)::numeric, 2) AS oitavas,
    ROUND(SUM(prob_quartas)::numeric, 2) AS quartas,
    ROUND(SUM(prob_semi)::numeric, 2) AS semi,
    ROUND(SUM(prob_final)::numeric, 2) AS final,
    ROUND(SUM(prob_campea)::numeric, 2) AS campea
FROM gold_probabilidades_copa;
```

Resultado esperado:

```text
grupo   ≈ 32
oitavas ≈ 16
quartas ≈ 8
semi    ≈ 4
final   ≈ 2
campea  ≈ 1
```

### Verificar monotonicidade

```sql
SELECT *
FROM gold_probabilidades_copa
WHERE NOT (
    prob_grupo >= prob_oitavas
    AND prob_oitavas >= prob_quartas
    AND prob_quartas >= prob_semi
    AND prob_semi >= prob_final
    AND prob_final >= prob_campea
);
```

Resultado esperado:

```text
nenhuma linha
```

### Verificar quantidade de seleções

```sql
SELECT COUNT(*)
FROM gold_probabilidades_copa;
```

Resultado esperado:

```text
48
```

### Verificar seleções com maior probabilidade de passar do grupo

```sql
SELECT
    selecao,
    ROUND((prob_grupo * 100)::numeric, 1) AS pct_grupo
FROM gold_probabilidades_copa
ORDER BY prob_grupo DESC
LIMIT 12;
```

### Verificar seleções com menor probabilidade de título

```sql
SELECT
    selecao,
    ROUND((prob_campea * 100)::numeric, 3) AS pct_campea
FROM gold_probabilidades_copa
ORDER BY prob_campea ASC
LIMIT 12;
```

## Testes de diagnóstico recomendados

### 1. Testar previsão de confronto manual

Antes de rodar Monte Carlo, testar:

```python
prever_jogo("France", "Scotland", neutro=True)
prever_jogo("Scotland", "France", neutro=True)
```

A inversão dos times em campo neutro não deve mudar drasticamente a força relativa.

### 2. Testar favoritos contra médios

```python
prever_jogo("Brazil", "Scotland", neutro=True)
prever_jogo("Argentina", "Scotland", neutro=True)
prever_jogo("Spain", "Scotland", neutro=True)
prever_jogo("France", "Scotland", neutro=True)
```

As favoritas devem ter vantagem clara, embora ainda exista chance de zebra.

### 3. Testar uma simulação única

Rodar uma única simulação e conferir:

```text
32 classificados ao R32
16 classificados ao R16
8 classificados às quartas
4 semifinalistas
2 finalistas
1 campeã
```

### 4. Testar matching dos terceiros

Para cada simulação, validar:

```text
8 terceiros classificados
8 slots de terceiros preenchidos
nenhum terceiro duplicado
nenhum slot de terceiro vazio
todos os terceiros respeitam a elegibilidade do slot
```

## Plano de implementação

1. Carregar:

   * `silver_copa2026`;
   * `data/grupos_copa2026.csv`;
   * `data/calendario_copa2026.csv`;
   * modelos Poisson;
   * `silver_elo_atual`.

2. Criar `rng = np.random.default_rng(SEED)`.

3. Criar cache de lambdas.

4. Implementar `obter_lambdas`.

5. Implementar `sortear_placar` em `src/poisson.py`.

6. Implementar simulação da fase de grupos.

7. Implementar classificação por grupo.

8. Implementar ranking dos terceiros.

9. Implementar `slots_terceiros` com matching bipartido.

10. Implementar resolução dos slots do mata-mata.

11. Implementar simulação do mata-mata.

12. Implementar pênaltis com leve vantagem por ELO.

13. Implementar função `simular_torneio`.

14. Rodar `N_SIMULACOES = 60000`.

15. Acumular contagens por fase.

16. Converter contagens em probabilidades.

17. Validar somas globais e monotonicidade.

18. Gravar `gold_probabilidades_copa`.

## Para explicar enquanto desenvolve

* Monte Carlo é repetir um processo aleatório muitas vezes.
* Uma simulação é só uma história possível.
* Muitas simulações viram frequência, e frequência vira probabilidade estimada.
* A seed permite reproduzir o mesmo resultado.
* Aumentar o número de simulações reduz o ruído.
* A fase de grupos usa pontos, saldo, gols pró e sorteio.
* O mata-mata é mais instável porque um empate pode ir para pênaltis.
* Pênaltis continuam aleatórios, mas o ELO pode dar uma leve vantagem.
* A tabela final representa o palpite agregado da máquina, não uma certeza.
