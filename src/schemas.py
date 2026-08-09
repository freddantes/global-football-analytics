from typing import Optional
from pydantic import BaseModel, Field, field_validator

# =====================================================================
# 1. CONTRATO PARA A TABELA DE CLASSIFICAÇÃO (Já existente)
# =====================================================================
class StandingRowSchema(BaseModel):
    position: int = Field(..., ge=1, description="A posição na tabela deve ser maior ou igual a 1")
    team: str = Field(..., min_length=1, description="O nome do time não pode ser vazio")
    crest: Optional[str] = Field(None, description="URL da imagem do escudo do time (pode ser nulo caso a API não forneça)") # <- NOVA COLUNA ADICIONADA AQUI
    points: int = Field(..., ge=0, description="Os pontos não podem ser negativos")
    playedGames: int = Field(..., ge=0)
    won: int = Field(..., ge=0)
    draw: int = Field(..., ge=0)
    lost: int = Field(..., ge=0)
    goalsFor: int = Field(..., ge=0)
    goalsAgainst: int = Field(..., ge=0)
    goalDifference: int

    @field_validator('points', 'playedGames')
    @classmethod
    def validate_not_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError('O valor não pode ser negativo')
        return v


# =====================================================================
# 2. NOVO CONTRATO PARA AS PARTIDAS / JOGOS (Etapa 3)
# =====================================================================
class MatchRowSchema(BaseModel):
    match_id: int = Field(..., description="ID único e exclusivo da partida na API")
    utc_date: str = Field(..., description="Data e hora oficial do jogo no formato ISO 8601 (ex: 2026-07-27T20:00:00Z)")
    status: str = Field(..., description="Status da partida (ex: FINISHED, SCHEDULED, TIMED, IN_PLAY)")
    matchday: Optional[int] = Field(None, ge=1, description="Número da rodada (pode ser nulo em copas ou fases eliminatórias)")
    home_team: str = Field(..., min_length=1, description="Nome do time mandante (dono da casa)")
    away_team: str = Field(..., min_length=1, description="Nome do time visitante")
    
    # Campos Opcionais: Usamos Optional[int] porque jogos futuros não possuem gols nem vencedor definidos
    home_goals: Optional[int] = Field(None, ge=0, description="Gols marcados pelo time mandante (None se o jogo não ocorreu)")
    away_goals: Optional[int] = Field(None, ge=0, description="Gols marcados pelo time visitante (None se o jogo não ocorreu)")
    winner: Optional[str] = Field(None, description="Resultado final: 'HOME_TEAM', 'AWAY_TEAM' ou 'DRAW' (Empate)")

    @field_validator('home_goals', 'away_goals')
    @classmethod
    def validate_goals_not_negative(cls, v: Optional[int]) -> Optional[int]:
        """
        Regra de Validação: Se o número de gols existir (não for None), 
        ele obrigatoriamente precisa ser maior ou igual a zero.
        """
        if v is not None and v < 0:
            raise ValueError('O número de gols de uma partida nunca pode ser negativo.')
        return v