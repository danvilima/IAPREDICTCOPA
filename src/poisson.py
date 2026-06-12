import math

MAX_GOLS = 10

def poisson_pmf(k, lamb):
    """
    Função de Massa de Probabilidade da distribuição Poisson.
    Utilizando apenas a biblioteca padrão 'math' por performance e pureza.
    """
    return math.exp(-lamb) * (lamb ** k) / math.factorial(k)

def probabilidades_resultado(lambda_casa, lambda_visitante, max_gols=MAX_GOLS):
    prob_vitoria = 0.0
    prob_empate = 0.0
    prob_derrota = 0.0

    for gols_casa in range(max_gols + 1):
        p_casa = poisson_pmf(gols_casa, lambda_casa)

        for gols_visitante in range(max_gols + 1):
            p_visitante = poisson_pmf(gols_visitante, lambda_visitante)
            p = p_casa * p_visitante

            if gols_casa > gols_visitante:
                prob_vitoria += p
            elif gols_casa == gols_visitante:
                prob_empate += p
            else:
                prob_derrota += p

    soma = prob_vitoria + prob_empate + prob_derrota

    if soma > 0:
        prob_vitoria /= soma
        prob_empate /= soma
        prob_derrota /= soma

    return {
        "prob_vitoria": prob_vitoria,
        "prob_empate": prob_empate,
        "prob_derrota": prob_derrota,
    }

def resultado_previsto(lambda_casa, lambda_visitante, max_gols=MAX_GOLS):
    probs = probabilidades_resultado(lambda_casa, lambda_visitante, max_gols=max_gols)

    mapa = {
        "V": probs["prob_vitoria"],
        "E": probs["prob_empate"],
        "D": probs["prob_derrota"],
    }

    return max(mapa, key=mapa.get)

def resultado_real(gols_casa, gols_visitante):
    if gols_casa > gols_visitante:
        return "V"
    if gols_casa == gols_visitante:
        return "E"
    return "D"
