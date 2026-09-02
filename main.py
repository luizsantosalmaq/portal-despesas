import os
import json
import mimetypes
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import google.generativeai as genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    for file in files:
        conteudo_arquivo = await file.read()
        
        # Identifica o MIME correto pelo nome do arquivo
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
            "Retorne APENAS o JSON com as chaves: data_hora, categoria, valor."
        )
        
        try:
            response = model.generate_content([
                {"mime_type": mime_type, "data": conteudo_arquivo},
                prompt
            ])
            
            texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
            dados = json.loads(texto_limpo)
            
            resultados.append({
                "arquivo": file.filename,
                "data_hora": str(dados.get("data_hora", "Não identificada")),
                "categoria": str(dados.get("categoria", "Outros")),
                "valor": float(dados.get("valor", 0.0))
            })
        except Exception as e:
            print(f"Erro ao processar arquivo {file.filename}: {str(e)}")
            resultados.append({
                "arquivo": file.filename,
                "data_hora": "Erro na leitura",
                "categoria": "Outros",
                "valor": 0.0
            })
            
    return resultados