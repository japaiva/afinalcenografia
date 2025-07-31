{
  "projeto_info": {
    "nome": "Hair Summit 2025",
    "empresa": "Beauty Fair",
    "area_total": 220.0,
    "tipo_stand": "ilha"
  },
  
  "dimensoes_stand": {
    "frente": 20.0,
    "fundo": 11.0,
    "area_calculada": 220.0
  },
  
  "areas_posicionadas": [
    {
      "id": "area_001",
      "tipo": "exposicao", 
      "nome": "Área Principal",
      "coordenadas": {
        "x": 0.0,
        "y": 0.0,
        "largura": 12.0,
        "profundidade": 8.0
      },
      "area_m2": 96.0,
      "elementos": {
        "lounge": true,
        "mesas_atendimento": true,
        "balcao_cafe": true
      },
      "equipamentos": ["tv", "ledss"]
    },
    
    {
      "id": "area_002", 
      "tipo": "sala_reuniao",
      "nome": "Sala VIP",
      "coordenadas": {
        "x": 12.0,
        "y": 0.0,
        "largura": 8.0,
        "profundidade": 6.0
      },
      "area_m2": 48.0,
      "capacidade": 8,
      "equipamentos": ["mesa", "cadeiras"]
    },
    
    {
      "id": "area_003",
      "tipo": "copa",
      "nome": "Copa Técnica", 
      "coordenadas": {
        "x": 12.0,
        "y": 6.0,
        "largura": 4.0,
        "profundidade": 5.0
      },
      "area_m2": 20.0,
      "equipamentos": ["pia", "bancada", "geladeira"]
    },
    
    {
      "id": "area_004",
      "tipo": "deposito",
      "nome": "Depósito",
      "coordenadas": {
        "x": 16.0,
        "y": 6.0,
        "largura": 4.0,
        "profundidade": 5.0
      },
      "area_m2": 20.0,
      "equipamentos": ["prateleiras", "armarios"]
    },
    
    {
      "id": "area_005",
      "tipo": "circulacao",
      "nome": "Área Central",
      "coordenadas": {
        "x": 0.0,
        "y": 8.0,
        "largura": 20.0,
        "profundidade": 3.0
      },
      "area_m2": 60.0,
      "elementos": {
        "entrada_principal": {
          "posicao": {"x": 9.0, "y": 8.0},
          "largura": 2.0
        }
      }
    }
  ],
  
  "validacao_layout": {
    "areas_dentro_limites": true,
    "sobreposicoes": false,
    "soma_areas": 244.0,
    "area_livre": 36.0,
    "percentual_ocupacao": 87.3,
    "acessibilidade": {
      "largura_minima_corredores": 1.5,
      "entrada_acessivel": true
    }
  },
  
  "metadados_geracao": {
    "algoritmo": "distribuicao_otimizada_v2",
    "validado": true,
    "timestamp": "2025-07-30T23:49:00Z",
    "agente": "calculador_coordenadas"
  }
}