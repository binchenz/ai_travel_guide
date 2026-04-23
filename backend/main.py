#!/usr/bin/env python3
"""
Shanghai Museum AI Guide Backend - Black Box Architecture with Fence
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, AsyncGenerator
from dotenv import load_dotenv
import openai
import os
import json
from pathlib import Path

# Import our new modules
from persona import persona_manager
from fence import fence_manager
from examples import example_manager
from memory_manager import memory_manager
from voice_metrics import metrics as voice_metrics
from volcano_tts import synthesize as tts_synthesize
from volcano_asr import recognize as asr_recognize

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Shanghai Museum AI Guide API", version="0.2.0 - Black Box")

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LLM configuration (Moonshot K2)
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")
model_name = os.getenv("MODEL_NAME", "kimi-k2-turbo-preview")

if openai_api_key:
    client = openai.AsyncOpenAI(api_key=openai_api_key, base_url=openai_base_url)
else:
    print("Warning: OPENAI_API_KEY not set - LLM features will not work")
    client = None

# Ontology-backed exhibit store (loads and validates at startup)
from ontology.loader import load_or_exit
ONTOLOGY = load_or_exit()


def _artifact_list() -> list:
    """Build backward-compatible list for GET /exhibits."""
    out = []
    for a in ONTOLOGY.artifacts.values():
        hall = ONTOLOGY.halls[a.hallId]
        dyn  = ONTOLOGY.dynasties[a.dynastyId]
        qq = a.quickQuestions.en if a.quickQuestions else []
        out.append({
            "id": a.id,
            "originalId": a.id,
            "type": a.type,
            "name": a.name.model_dump(),
            "imageUrl": a.imageUrl,
            "hallId": a.hallId,
            "dynastyId": a.dynastyId,
            "personIds": a.personIds,
            # deprecated legacy flat fields — kept for one release cycle
            "hall": hall.name.en,
            "dynasty": dyn.name.en,
            "period": a.period.label.en if a.period else None,
            "quickQuestions": qq,
        })
    return out


# In-memory session store
sessions: Dict[str, Dict[str, Any]] = {}


# Pydantic models
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    sessionId: str
    exhibitId: str
    userInput: str
    language: Optional[str] = "en"
    depthLevel: Optional[str] = None


class ChatResponse(BaseModel):
    content: str
    quickQuestions: List[str]
    depthLevel: str
    personaVersion: str


class Exhibit(BaseModel):
    id: str
    originalId: str
    name: Dict[str, str]
    imageUrl: str
    dynasty: str
    period: str
    hall: str
    quickQuestions: List[str]


class ExampleReviewRequest(BaseModel):
    approve: bool
    rating: int = 0
    notes: str = ""


# --- Helper functions ---
def get_exhibit_by_id(exhibit_id: str):
    """Get Artifact by ID (supports full artifact/... id or legacy short form)"""
    if exhibit_id in ONTOLOGY.artifacts:
        return ONTOLOGY.artifacts[exhibit_id]
    # Legacy short-id: "artifact-da-ke-ding" → "artifact/da-ke-ding"
    if exhibit_id.startswith("artifact-"):
        converted = "artifact/" + exhibit_id[len("artifact-"):]
        if converted in ONTOLOGY.artifacts:
            return ONTOLOGY.artifacts[converted]
    return None


def get_or_create_session(session_id: str, language: str = "en") -> Dict[str, Any]:
    """Get or create visitor session"""
    if session_id not in sessions:
        sessions[session_id] = {
            "sessionId": session_id,
            "language": language,
            "cultureBackground": "limited_chinese_knowledge",
            "visitedExhibits": [],
            "currentExhibit": None,
            "interests": [],
            "depthLevel": "entry",
            "turnCount": 0,
            "totalTurnCount": 0,
            "history": []
        }
    return sessions[session_id]


def build_enhanced_prompt(session: Dict[str, Any], exhibit, language: str = "en") -> str:
    """Build complete prompt with persona, examples, exhibit data, AND multi-level memory"""
    exhibit_dict = exhibit.model_dump() if hasattr(exhibit, "model_dump") else exhibit
    exhibit_id = exhibit.id if hasattr(exhibit, "id") else exhibit_dict.get("@id", "")

    # 基础人格 + 展品数据
    system_prompt = persona_manager.build_system_prompt(language, exhibit_dict)
    
    # 好例子注入
    relevant_examples = example_manager.get_relevant_examples("", exhibit_id)
    examples_text = example_manager.format_examples_for_prompt(relevant_examples)
    
    # 完整提示词 = 基础 + 例子 + 多层次记忆
    base_full = system_prompt + examples_text
    full_prompt = memory_manager.build_full_prompt(base_full, session)
    
    return full_prompt


# --- API Endpoints ---
@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "openai_configured": bool(openai_api_key),
        "persona_version": persona_manager.get_version(),
        "architecture": "black_box_with_fence"
    }


@app.get("/exhibits")
async def get_exhibits():
    """Get all exhibits"""
    return _artifact_list()


@app.get("/exhibits/{exhibit_id}")
async def get_exhibit(exhibit_id: str):
    """Get single exhibit by ID"""
    exhibit = get_exhibit_by_id(exhibit_id)
    if not exhibit:
        raise HTTPException(status_code=404, detail="Exhibit not found")
    return exhibit.model_dump()


async def generate_streaming_response(
    messages: List[Dict], 
    session: Dict, 
    exhibit: Dict, 
    user_input: str, 
    language: str
) -> AsyncGenerator[str, None]:
    """Generate streaming response with fence and evolution"""
    
    full_response = ""
    
    if client:
        try:
            # Stream from LLM
            completion = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.75,
                max_tokens=600,
                stream=True
            )
            
            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    full_response += delta
                    yield delta
        except Exception as e:
            print(f"LLM error: {e}")
            full_response = fence_manager.get_fallback_response(language)
            yield full_response
    else:
        # Fallback without LLM
        full_response = f"Welcome! I'm your guide for {exhibit.name.en}. How can I help you explore this artifact?"
        yield full_response
    
    # --- Fence 2: Output Check (after full response) ---
    output_check = fence_manager.check_output(full_response, language, exhibit.model_dump())
    if not output_check.passed:
        print("[Fence] Output failed check")
        pass
    
    # --- Evolution: Auto-Extract for Review ---
    if len(full_response) > 50:
        example_manager.add_pending_example(user_input, full_response, exhibit.id)
    
    # Update session AFTER streaming completes
    session["history"].append({"role": "user", "content": user_input})
    session["history"].append({"role": "assistant", "content": full_response})
    session["turnCount"] += 1
    session["totalTurnCount"] += 1
    
    # 保底深度调整
    if session["turnCount"] == 2 and session["depthLevel"] == "entry":
        session["depthLevel"] = "deeper"
    if session["turnCount"] == 5 and session["depthLevel"] == "deeper":
        session["depthLevel"] = "expert"


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests with fence, persona, AND multi-level memory"""
    
    session = get_or_create_session(request.sessionId, request.language)
    
    # --- 手动深度切换支持 ---
    if request.depthLevel and request.depthLevel in ["entry", "deeper", "expert"]:
        session["depthLevel"] = request.depthLevel
    
    # --- Fence 1: Input Filter ---
    input_check = fence_manager.filter_input(request.userInput, request.language)
    if not input_check.passed:
        return ChatResponse(
            content=fence_manager.get_fallback_response(request.language),
            quickQuestions=[],
            depthLevel=session["depthLevel"],
            personaVersion=persona_manager.get_version()
        )
    
    # Get exhibit
    exhibit = get_exhibit_by_id(request.exhibitId)
    if not exhibit:
        raise HTTPException(status_code=404, detail="Exhibit not found")
    
    # Update session: 展品切换逻辑
    if session["currentExhibit"] != exhibit.id:
        session["currentExhibit"] = exhibit.id
        session["turnCount"] = 0
        if exhibit.id not in session["visitedExhibits"]:
            session["visitedExhibits"].append(exhibit.id)
    
    # --- 记忆增强 1: 推断用户兴趣 ---
    session["interests"] = memory_manager.infer_user_interests(
        request.userInput, 
        session.get("interests", [])
    )
    
    # --- 记忆增强 2: 智能调整深度 (仅在没有手动设置时) ---
    if not request.depthLevel:
        depth_adjustment = memory_manager.should_adjust_depth(session, request.userInput)
        if depth_adjustment and depth_adjustment != session["depthLevel"]:
            session["depthLevel"] = depth_adjustment
            print(f"[Memory] Depth adjusted: {depth_adjustment}")
    
    # Build enhanced prompt WITH FULL MEMORY
    system_prompt = build_enhanced_prompt(session, exhibit, request.language)
    
    # Build messages
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": request.userInput})
    
    # Generate response
    response_content = ""
    
    if client:
        try:
            completion = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.75,
                max_tokens=600
            )
            response_content = completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM error: {e}")
            response_content = fence_manager.get_fallback_response(request.language)
    else:
        # Fallback without LLM
        response_content = f"Welcome! I'm your guide for {exhibit.name.en}. How can I help you explore this artifact?"
    
    # --- Fence 2: Output Check ---
    output_check = fence_manager.check_output(response_content, request.language, exhibit.model_dump())
    if not output_check.passed:
        response_content = fence_manager.get_fallback_response(request.language)
    
    # --- Evolution: Auto-Extract for Review ---
    if len(response_content) > 50:
        example_manager.add_pending_example(request.userInput, response_content, exhibit.id)
    
    # Update session
    session["history"].append({"role": "user", "content": request.userInput})
    session["history"].append({"role": "assistant", "content": response_content})
    session["turnCount"] += 1
    session["totalTurnCount"] += 1
    
    # 保底深度调整（如果记忆调整没有触发）
    if session["turnCount"] == 2 and session["depthLevel"] == "entry":
        session["depthLevel"] = "deeper"
    if session["turnCount"] == 5 and session["depthLevel"] == "deeper":
        session["depthLevel"] = "expert"
    
    return ChatResponse(
        content=response_content,
        quickQuestions=exhibit.quickQuestions.en if exhibit.quickQuestions else [],
        depthLevel=session["depthLevel"],
        personaVersion=persona_manager.get_version()
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Handle streaming chat requests with reduced latency"""
    
    session = get_or_create_session(request.sessionId, request.language)
    
    # --- 手动深度切换支持 ---
    if request.depthLevel and request.depthLevel in ["entry", "deeper", "expert"]:
        session["depthLevel"] = request.depthLevel
    
    # --- Fence 1: Input Filter ---
    input_check = fence_manager.filter_input(request.userInput, request.language)
    if not input_check.passed:
        # Non-streaming fallback
        response_content = fence_manager.get_fallback_response(request.language)
        async def fallback_generator():
            yield response_content
        return StreamingResponse(fallback_generator(), media_type="text/plain")
    
    # Get exhibit
    exhibit = get_exhibit_by_id(request.exhibitId)
    if not exhibit:
        raise HTTPException(status_code=404, detail="Exhibit not found")
    
    # Update session
    if session["currentExhibit"] != exhibit.id:
        session["currentExhibit"] = exhibit.id
        session["turnCount"] = 0
        if exhibit.id not in session["visitedExhibits"]:
            session["visitedExhibits"].append(exhibit.id)
    
    # --- 记忆增强 ---
    session["interests"] = memory_manager.infer_user_interests(
        request.userInput, 
        session.get("interests", [])
    )
    
    if not request.depthLevel:
        depth_adjustment = memory_manager.should_adjust_depth(session, request.userInput)
        if depth_adjustment and depth_adjustment != session["depthLevel"]:
            session["depthLevel"] = depth_adjustment
    
    # Build prompt
    system_prompt = build_enhanced_prompt(session, exhibit, request.language)
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": request.userInput})
    
    # Return streaming response
    return StreamingResponse(
        generate_streaming_response(messages, session, exhibit, request.userInput, request.language),
        media_type="text/plain"
    )


# --- Management API Endpoints ---
@app.get("/api/persona/versions")
async def get_persona_versions():
    """Get all persona versions"""
    return persona_manager.get_all_versions()


@app.post("/api/persona/rollback/{version}")
async def rollback_persona(version: str):
    """Rollback to a specific persona version"""
    if persona_manager.rollback_to_version(version):
        return {"status": "success", "rolled_back_to": version}
    raise HTTPException(status_code=404, detail="Version not found")


@app.get("/api/examples/good")
async def get_good_examples():
    """Get all good examples"""
    return example_manager.get_all_good()


@app.get("/api/examples/pending")
async def get_pending_examples():
    """Get all pending examples for review"""
    return example_manager.get_all_pending()


@app.post("/api/examples/{example_id}/review")
async def review_example(example_id: str, review: ExampleReviewRequest):
    """Review a pending example"""
    if example_manager.review_pending_example(example_id, review.approve, review.rating, review.notes):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Example not found")


@app.post("/tts")
async def text_to_speech(request: Request):
    """Text-to-speech. Default backend is Edge TTS; Volcano opt-in via env.

    Returns:
        {"audio": base64, "format": "mp3", "backend": "edge"|"volcano"}
    """
    body = await request.json()
    text = (body.get("text") or "").strip()
    language = body.get("language", "zh")

    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    try:
        return await tts_synthesize(text, language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger = __import__("logging").getLogger("voice.tts")
        logger.exception("TTS endpoint failed")
        raise HTTPException(status_code=502, detail="tts_backend_unavailable")


@app.post("/asr")
async def speech_to_text(request: Request):
    """Speech-to-text via Volcano SAUC bigmodel.

    Returns ``{"text": str, "language": str}``. A successful call with
    pure silence will yield an empty string; transport or auth errors
    surface as 502 rather than being hidden behind an empty result.
    """
    body = await request.json()
    audio_data = body.get("audio")
    language = body.get("language", "zh")

    if not audio_data:
        raise HTTPException(status_code=400, detail="audio is required")
    if not os.getenv("VOLCANO_ACCESS_TOKEN"):
        raise HTTPException(status_code=503, detail="asr_not_configured")

    try:
        return await asr_recognize(audio_data, language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger = __import__("logging").getLogger("voice.asr")
        logger.exception("ASR endpoint failed")
        raise HTTPException(status_code=502, detail="asr_backend_unavailable")


@app.get("/voice/health")
async def voice_health():
    """Lightweight diagnostic: which backends are configured."""
    return {
        "tts_backend": os.getenv("VOICE_TTS_BACKEND", "edge"),
        "volcano_configured": bool(os.getenv("VOLCANO_ACCESS_TOKEN")),
        "edge_tts_available": _edge_tts_installed(),
    }


@app.get("/voice/metrics")
async def voice_metrics_endpoint():
    """In-process metrics for /tts and /asr. Not persisted across restarts."""
    return voice_metrics.snapshot()


def _edge_tts_installed() -> bool:
    try:
        import edge_tts  # noqa: F401
        return True
    except Exception:
        return False


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
