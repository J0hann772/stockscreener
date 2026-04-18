from fastapi import FastAPI, Depends, HTTPException
from auth.service import get_user
from schemas.analyze_engine import analyze_tickers
from schemas.schemas import AnalyzeRequest, AnalyzeResponse, TickerResult, analyze_tickers_async


app = FastAPI()



@app.post("/analyze/", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, user=Depends(get_user)):
    try:
        matched, details = await analyze_tickers_async(request.tickers, request.strategy_config)

        # конвертация словарей в модели Pydantic
        detail_models = [TickerResult(**d) for d in details]

        return AnalyzeResponse(matched=matched, details=detail_models)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")