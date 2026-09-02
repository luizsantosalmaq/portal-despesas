import os
import json
import mimetypes
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from google import genai
from google.genai import types
import traceback

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class DespesaResponse(BaseModel):
    arquivo: str
    data_hora: str
    categoria: str
    valor: float

@app.post("/processar-recibos/", response_model=List[DespesaResponse])
async def processar_recibos(files: List[UploadFile] = File(..., description="Selecione os arquivos de recibo")):
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="O limite máximo é de 50 arquivos por vez.")
    
    resultados = []
    
    for file in files:
        conteudo_arquivo = await file.read()
        
        mime_type, _ = mimetypes.guess_type(file.filename)
        if not mime_type:
            mime_type = file.content_type or "application/octet-stream"
        if file.filename.lower().endswith(".jpg") or file.filename.lower().endswith(".jpeg"):
            mime_type = "image/jpeg"
        elif file.filename.lower().endswith(".pdf"):
            mime_type = "application/pdf"

        prompt = (
            "Analise este recibo ou nota fiscal e extraia as seguintes informações em formato JSON estrito: "
            "data_hora (formato DD/MM/AAAA HH:MM ou apenas a data se não houver hora), "
            "categoria (escolha estritamente entre: Alimentação, Hospedagem, Estadia, Pedágio, Transporte, Outros), "
            "valor (número float contendo o valor total da nota/comprovante). "
            "Retorne APENAS o JSON válido contendo exatamente as chaves: data_hora, categoria, valor."
        )
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=conteudo_arquivo,
                        mime_type=mime_type,
                    ),
                    prompt
                ]
            )
            
            texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
            dados = json.loads(texto_limpo)
            
            resultados.append({
                "arquivo": file.filename,
                "data_hora": str(dados.get("data_hora", "Não identificada")),
                "categoria": str(dados.get("categoria", "Outros")),
                "valor": float(dados.get("valor", 0.0))
            })
        except Exception as e:
            print("=== ERRO DETALHADO ===")
            traceback.print_exc()
            resultados.append({
                "arquivo": file.filename,
                "data_hora": "Erro na leitura",
                "categoria": "Outros",
                "valor": 0.0
            })
            
    return resultados