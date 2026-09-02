import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import google.generativeai as genai
import json

app = FastAPI()

# Configuração do CORS para permitir acesso do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure sua chave da API do Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "SUA_CHAVE_API_AQUI"))

class DespesaResponse(BaseModel):
    arquivo: str
    data_hora: str
    categoria: str
    valor: float

@app.post("/processar-recibos/", response_model=List[DespesaResponse])
async def processar_recibos(files: List[UploadFile] = File(...)):
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="O limite máximo é de 50 arquivos por vez.")
    
    resultados = []
    
    # Modelo multimodal para leitura de imagens e PDFs
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    for file in files:
        conteudo_arquivo = await file.read()
        
        prompt = (
            "Analise este recibo ou nota fiscal e extraia as seguintes informações em formato JSON estrito: "
            "data_hora (formato DD/MM/AAAA HH:MM ou apenas a data se não houver hora), "
            "categoria (escolha entre: Alimentação, Hospedagem, Estadia, Pedágio, Transporte, Outros), "
            "valor (número float contendo o valor total ou a soma dos itens se houver múltiplos). "
            "Retorne APENAS o JSON com as chaves: data_hora, categoria, valor."
        )
        
        try:
            # Envia o arquivo e o prompt para o Gemini
            response = model.generate_content([
                {"mime_type": file.content_type, "data": conteudo_arquivo},
                prompt
            ])
            
            # Limpa o texto retornado para garantir que seja um JSON válido
            texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
            dados = json.loads(texto_limpo)
            
            resultados.append({
                "arquivo": file.filename,
                "data_hora": dados.get("data_hora", "Não identificada"),
                "categoria": dados.get("categoria", "Outros"),
                "valor": float(dados.get("valor", 0.0))
            })
        except Exception as e:
            # Em caso de erro na leitura do arquivo específico
            resultados.append({
                "arquivo": file.filename,
                "data_hora": "Erro na leitura",
                "categoria": "Outros",
                "valor": 0.0
            })
            
    return resultados