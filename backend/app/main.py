from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from .collector import collect_news
from .ai import generate_analysis
from .config import settings

app = FastAPI(title="Itaú Pulse Live API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE = {
    "updated_at": None,
    "news": [],
    "summary": None,
    "insights": [],
    "metrics": [
        {"id":"itau_profit","name":"Lucro Itaú","bank":"Itaú","period":"1T26","value":12.3,"unit":"R$ bi"},
        {"id":"itau_roe","name":"ROE Itaú","bank":"Itaú","period":"1T26","value":24.8,"unit":"%"},
        {"id":"nu_clients","name":"Clientes Nu","bank":"Nubank","period":"1T26","value":135,"unit":"mi+"},
        {"id":"nu_eff","name":"Eficiência Nu","bank":"Nubank","period":"1T26","value":17.6,"unit":"%"}
    ]
}

def build_insights(summary):
    return [
        {
            "id":"itau-meaning",
            "title":"O que isso significa para o Itaú",
            "subtitle":"Conexão estratégica automática",
            "body": summary.get("itau_meaning",""),
            "impact_level":"high",
            "key_numbers":["Itaú","Cartões","Pix","Pagamentos"],
            "recommended_actions": summary.get("opportunities", [])[:4]
        },
        {
            "id":"risk-radar",
            "title":"Radar de riscos",
            "subtitle":"Pontos que merecem acompanhamento",
            "body": " | ".join(summary.get("risks", [])),
            "impact_level":"high",
            "key_numbers":["Fraude","Crédito","Concorrência"],
            "recommended_actions":["Monitorar alertas críticos", "Separar impacto de curto e longo prazo", "Conectar notícia a jornada/indicador"]
        }
    ]

async def refresh_cache():
    news = await collect_news()
    summary = await generate_analysis(news)
    CACHE["updated_at"] = datetime.utcnow().isoformat()
    CACHE["news"] = news
    CACHE["summary"] = summary
    CACHE["insights"] = build_insights(summary)
    return {"updated_at": CACHE["updated_at"], "news_count": len(news)}

@app.on_event("startup")
async def startup():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(refresh_cache, "interval", minutes=settings.refresh_minutes)
    scheduler.start()
    await refresh_cache()

@app.get("/health")
async def health():
    return {"status":"ok", "updated_at": CACHE["updated_at"]}

@app.post("/jobs/refresh")
async def force_refresh():
    return await refresh_cache()

@app.get("/brief/live")
async def live_brief():
    if not CACHE["news"]:
        await refresh_cache()

    relevant_news = CACHE["news"][:30]

    recent_news = sorted(
        CACHE["news"],
        key=lambda x: x.get("published_at", ""),
        reverse=True
    )[:30]

    return {
        "updated_at": CACHE["updated_at"],
        "summary": CACHE["summary"],
        "top_news": relevant_news,
        "recent_news": recent_news,
        "insights": CACHE["insights"],
        "metrics": CACHE["metrics"]
    }

@app.get("/news")
async def news():
    return CACHE["news"]

@app.get("/insights")
async def insights():
    return CACHE["insights"]
