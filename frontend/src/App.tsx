import { useState, useEffect, useRef, type ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition
    webkitSpeechRecognition: typeof SpeechRecognition
  }
}

const API_BASE_URL = "http://127.0.0.1:8080"

interface Bilingual { en: string; zh: string }
interface BilingualList { en: string[]; zh: string[] }

interface Exhibit {
  id: string
  originalId?: string
  type?: string
  name: Bilingual
  imageUrl?: string
  hallId: string
  dynastyId: string
  personIds: string[]
  // Legacy fields returned during deprecation window:
  hall?: string
  dynasty?: string
  period?: string | { start: number; end: number; label: Bilingual }
  quickQuestions?: string[] | BilingualList
}

interface Hall    { id: string; name: Bilingual; floor: number; theme?: Bilingual }
interface Dynasty {
  id: string
  name: Bilingual
  period: { start: number; end: number; label: Bilingual }
  predecessor?: string | null
  successor?: string | null
  shortDesc?: Bilingual | null
}
interface Person  {
  id: string
  name: Bilingual
  role: Bilingual
  dynastyId: string
  shortDesc?: Bilingual | null
}

interface Message {
  role: "user" | "assistant"
  content: string
  isStreaming?: boolean
}

interface Toast {
  id: string
  type: "success" | "error" | "info"
  message: string
}

type DepthLevel = "entry" | "deeper" | "expert"

type TTSSpeed = 0.75 | 0.9 | 1.0 | 1.1 | 1.25

function EntityDrawer({
  target,
  onClose,
  language,
  halls,
  dynasties,
  persons,
  onPickExhibit,
}: {
  target: { type: "hall" | "dynasty" | "person"; id: string } | null
  onClose: () => void
  language: "en" | "zh"
  halls: Record<string, Hall>
  dynasties: Record<string, Dynasty>
  persons: Record<string, Person>
  onPickExhibit: (ex: Exhibit) => void
}) {
  const [relatedArtifacts, setRelatedArtifacts] = useState<Exhibit[]>([])

  useEffect(() => {
    if (!target) { setRelatedArtifacts([]); return }
    const { type, id } = target
    fetch(`${API_BASE_URL}/ontology/${type}s/${id}/artifacts`)
      .then(r => r.json())
      .then(setRelatedArtifacts)
      .catch(() => setRelatedArtifacts([]))
  }, [target])

  if (!target) return null
  const { type, id } = target

  let body: ReactNode = null
  if (type === "hall" && halls[id]) {
    const h = halls[id]
    body = (
      <>
        <h2 className="text-2xl font-semibold mb-2">{h.name[language]}</h2>
        <p className="text-sm text-gray-600 mb-4">
          {language === "en" ? `Floor ${h.floor}` : `${h.floor} 层`}
        </p>
        {h.theme && <p className="mb-4 italic">{h.theme[language]}</p>}
      </>
    )
  } else if (type === "dynasty" && dynasties[id]) {
    const d = dynasties[id]
    body = (
      <>
        <h2 className="text-2xl font-semibold mb-2">{d.name[language]}</h2>
        <p className="text-sm text-gray-600 mb-2">{d.period.label[language]}</p>
        <p className="text-sm text-gray-500 mb-4">
          {d.predecessor ? `← ${d.predecessor}` : ""}
          {d.predecessor && d.successor ? "  " : ""}
          {d.successor ? `→ ${d.successor}` : ""}
        </p>
        {d.shortDesc && <p className="mb-4">{d.shortDesc[language]}</p>}
      </>
    )
  } else if (type === "person" && persons[id]) {
    const p = persons[id]
    body = (
      <>
        <h2 className="text-2xl font-semibold mb-2">{p.name[language]}</h2>
        <p className="text-sm text-gray-600 mb-4">{p.role[language]}</p>
        {p.shortDesc && <p className="mb-4">{p.shortDesc[language]}</p>}
      </>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/40" onClick={onClose} />
      <div className="w-full sm:w-96 bg-white p-6 shadow-xl overflow-y-auto">
        <button className="text-gray-500 hover:text-gray-800 mb-4 text-lg" onClick={onClose}>✕</button>
        {body}
        <h3 className="text-lg font-medium mt-6 mb-3">
          {language === "en" ? "Related artifacts" : "相关展品"}
        </h3>
        {relatedArtifacts.length === 0 && (
          <p className="text-sm text-gray-400">
            {language === "en" ? "None loaded yet." : "暂无相关展品"}
          </p>
        )}
        <div className="grid grid-cols-2 gap-3">
          {relatedArtifacts.map(ex => (
            <button
              key={ex.id}
              onClick={() => { onPickExhibit(ex); onClose() }}
              className="border rounded-lg p-2 text-left hover:bg-gray-50 transition"
            >
              <div className="text-sm font-medium">{ex.name[language]}</div>
              <div className="text-xs text-gray-500">{ex.id.replace("artifact/", "")}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function EntityChip({
  label, onClick,
}: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center px-3 py-1 mr-2 mb-2 rounded-full text-sm bg-amber-50 text-amber-900 border border-amber-200 hover:bg-amber-100 transition"
    >
      {label}
    </button>
  )
}

function App() {
  const [exhibits, setExhibits] = useState<Exhibit[]>([])
  const [exhibitsLoading, setExhibitsLoading] = useState(true)
  const [exhibitsError, setExhibitsError] = useState<string | null>(null)
  const [currentExhibit, setCurrentExhibit] = useState<Exhibit | null>(null)
  const [language, setLanguage] = useState<"en" | "zh">('en')
  const [sessionId] = useState<string>(() => `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputText, setInputText] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [playingIndex, setPlayingIndex] = useState(-1)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [chatError, setChatError] = useState<string | null>(null)
  const [depthLevel, setDepthLevel] = useState<DepthLevel>("entry")
  const [ttsSpeed, setTtsSpeed] = useState<TTSSpeed>(0.9)
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [drawerTarget, setDrawerTarget] =
    useState<{ type: "hall" | "dynasty" | "person"; id: string } | null>(null)
  const [halls,     setHalls]     = useState<Record<string, Hall>>({})
  const [dynasties, setDynasties] = useState<Record<string, Dynasty>>({})
  const [persons,   setPersons]   = useState<Record<string, Person>>({})
  
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)
  const streamBufferRef = useRef<string>("")
  const currentPlayIndexRef = useRef<number>(-1)
  const isAutoPlayingRef = useRef<boolean>(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  // Pre-fetched audio for the next TTS segment — eliminates gap between sentences.
  const nextAudioPromiseRef = useRef<Promise<HTMLAudioElement | null> | null>(null)
  // Currently playing <audio> element — needed to stop it before starting a new one.
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  // Abort controller for the in-flight /tts fetch — cancels it when user clicks again.
  const ttsAbortRef = useRef<AbortController | null>(null)
  // Active MediaRecorder — kept in a ref so stopVoiceInput() can actually call .stop().
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)

  // Toast notification
  const showToast = (type: "success" | "error" | "info", message: string) => {
    const id = Math.random().toString(36).substr(2, 9)
    setToasts(prev => [...prev, { id, type, message }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 4000)
  }

  // Load exhibits
  useEffect(() => {
    const loadExhibits = async () => {
      setExhibitsLoading(true)
      setExhibitsError(null)
      
      try {
        const res = await fetch(`${API_BASE_URL}/exhibits`)
        if (!res.ok) {
          throw new Error(language === "en" ? "Failed to load exhibits" : "加载展品失败")
        }
        const data = await res.json()
        setExhibits(data)
      } catch (err) {
        console.error("Failed to load exhibits:", err)
        setExhibitsError(language === "en" ? "Unable to load exhibits. Please check your connection." : "无法加载展品。请检查网络连接。")
      } finally {
        setExhibitsLoading(false)
      }
    }
    
    loadExhibits()
  }, [language])

  // Load ontology entity caches
  useEffect(() => {
    const toMap = <T extends { id: string }>(arr: T[]) =>
      Object.fromEntries(arr.map(x => [x.id, x]))
    Promise.all([
      fetch(`${API_BASE_URL}/ontology/halls`).then(r => r.json()),
      fetch(`${API_BASE_URL}/ontology/dynasties`).then(r => r.json()),
      fetch(`${API_BASE_URL}/ontology/persons`).then(r => r.json()),
    ]).then(([h, d, p]) => {
      setHalls(toMap(h as Hall[]))
      setDynasties(toMap(d as Dynasty[]))
      setPersons(toMap(p as Person[]))
    }).catch(err => console.error("Failed to load ontology entities", err))
  }, [])

  // Stop speaking on unmount
  useEffect(() => {
    return () => {
      if (speechSynthesis.speaking) {
        speechSynthesis.cancel()
      }
    }
  }, [])

  // Encode an AudioBuffer as a 16 kHz mono 16-bit PCM WAV Blob.
  // MediaRecorder outputs WebM/OGG, not WAV — this converts it properly.
  const encodeWav = async (rawBlob: Blob): Promise<Blob> => {
    const arrayBuf = await rawBlob.arrayBuffer()
    const ctx = new AudioContext()
    const decoded = await ctx.decodeAudioData(arrayBuf)
    ctx.close()

    const TARGET_SR = 16000
    const offlineCtx = new OfflineAudioContext(1, Math.ceil(decoded.duration * TARGET_SR), TARGET_SR)
    const src = offlineCtx.createBufferSource()
    src.buffer = decoded
    src.connect(offlineCtx.destination)
    src.start()
    const resampled = await offlineCtx.startRendering()

    const samples = resampled.getChannelData(0)
    const pcm = new Int16Array(samples.length)
    for (let i = 0; i < samples.length; i++) {
      pcm[i] = Math.max(-32768, Math.min(32767, Math.round(samples[i] * 32767)))
    }

    // WAV container
    const wavBuf = new ArrayBuffer(44 + pcm.byteLength)
    const v = new DataView(wavBuf)
    const str = (off: number, s: string) => { for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i)) }
    str(0, 'RIFF'); v.setUint32(4, 36 + pcm.byteLength, true); str(8, 'WAVE')
    str(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true)
    v.setUint16(22, 1, true); v.setUint32(24, TARGET_SR, true)
    v.setUint32(28, TARGET_SR * 2, true); v.setUint16(32, 2, true)
    v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, pcm.byteLength, true)
    new Int16Array(wavBuf, 44).set(pcm)
    return new Blob([wavBuf], { type: 'audio/wav' })
  }

  // Voice input functions
  const startVoiceInput = async () => {
    try {
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream)
      const audioChunks: Blob[] = []
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data)
        }
      }
      
      mediaRecorder.onstop = async () => {
        mediaRecorderRef.current = null
        setIsRecording(false)
        setIsTranscribing(true)

        try {
          // MediaRecorder produces WebM/OGG, not WAV. Convert to 16kHz mono PCM WAV.
          const rawBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' })
          const wavBlob = await encodeWav(rawBlob)

          // Convert WAV to base64
          const arrayBuf = await wavBlob.arrayBuffer()
          const base64Audio = btoa(String.fromCharCode(...new Uint8Array(arrayBuf)))

          // Send proper WAV to backend ASR
          const response = await fetch(`${API_BASE_URL}/asr`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audio: base64Audio, language }),
          })

          if (response.ok) {
            const data = await response.json()
            if (data.text && data.text.trim()) {
              setInputText(prev => prev + data.text)
              showToast('success', language === 'en' ? 'Voice recognized' : '语音已识别')
            } else {
              showToast('info', language === 'en' ? 'No speech detected' : '未检测到语音，请重试')
            }
          } else {
            showToast('error', language === 'en' ? 'ASR service error' : '语音识别服务错误')
          }
        } catch (error) {
          console.error('ASR error:', error)
          showToast('error', language === 'en' ? 'Error processing audio' : '处理音频时出错')
        } finally {
          stream.getTracks().forEach(track => track.stop())
          setIsTranscribing(false)
        }
      }
      
      mediaRecorder.onerror = (error) => {
        console.error('MediaRecorder error:', error)
        setIsRecording(false)
        showToast('error', language === 'en' ? 'Error starting recorder' : '启动录音失败')
        stream.getTracks().forEach(track => track.stop())
      }
      
      // Store instance so stopVoiceInput() can call .stop() immediately.
      mediaRecorderRef.current = mediaRecorder

      // Start recording
      mediaRecorder.start()
      setIsRecording(true)
      
      // Safety timeout: auto-stop after 10 seconds if user forgets
      setTimeout(() => {
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.stop()
        }
      }, 10000)
      
    } catch (error) {
      console.error('Error accessing microphone:', error)
      setIsRecording(false)
      showToast('error', language === 'en' ? 'Microphone access denied' : '麦克风访问被拒绝')
    }
  }

  const stopVoiceInput = () => {
    // Actually stop the recorder — this triggers onstop which sends audio to ASR.
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    mediaRecorderRef.current = null
    setIsRecording(false)
  }

  // Depth label
  const getDepthLabel = (depth: DepthLevel) => {
    if (language === "en") {
      return depth === "entry" ? "Beginner" : depth === "deeper" ? "Intermediate" : "Expert"
    }
    return depth === "entry" ? "入门" : depth === "deeper" ? "进阶" : "专家"
  }

  // Stop every active audio source (HTMLAudioElement + browser speech synthesis).
  // Also cancels any in-flight /tts fetch and clears the streaming pipeline.
  const stopAllAudio = () => {
    // Stop in-flight fetch
    ttsAbortRef.current?.abort()
    ttsAbortRef.current = null
    // Stop HTMLAudioElement
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current.src = ""
      currentAudioRef.current = null
    }
    // Stop browser speech synthesis
    if (speechSynthesis.speaking) speechSynthesis.cancel()
    // Stop streaming pipeline
    isAutoPlayingRef.current = false
    nextAudioPromiseRef.current = null
    streamBufferRef.current = ""
    setIsPlaying(false)
    setPlayingIndex(-1)
  }

  // TTS functions - with speed support!
  const speakText = async (text: string, index: number) => {
    // Toggle off if already playing this message
    if (isPlaying && playingIndex === index) {
      stopAllAudio()
      return
    }
    // Always stop whatever is currently playing before starting a new utterance
    stopAllAudio()

    currentPlayIndexRef.current = index

    const controller = new AbortController()
    ttsAbortRef.current = controller

    try {
      // Use Volcano Engine TTS service
      const response = await fetch(`${API_BASE_URL}/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language }),
        signal: controller.signal,
      })
      
      if (response.ok) {
        const data = await response.json()
        
        if (data.audio) {
          // Abort has already fired — another click happened while fetching, bail out.
          if (controller.signal.aborted) return

          try {
            const audio = new Audio(`data:audio/mp3;base64,${data.audio}`)
            currentAudioRef.current = audio

            audio.onplay = () => {
              setIsPlaying(true)
              setPlayingIndex(index)
            }
            
            audio.onended = () => {
              currentAudioRef.current = null
              setIsPlaying(false)
              setPlayingIndex(-1)
            }
            
            audio.onerror = () => {
              currentAudioRef.current = null
              setIsPlaying(false)
              setPlayingIndex(-1)
              showToast('warning', language === 'en' ? 'Using browser TTS (audio failed)' : '使用浏览器TTS（音频播放失败）')
              // Fallback to browser TTS
              const utterance = new SpeechSynthesisUtterance(text)
              utterance.lang = language === 'en' ? 'en-US' : 'zh-CN'
              utterance.rate = ttsSpeed
              utterance.pitch = 1.0

              utterance.onstart = () => {
                setIsPlaying(true)
                setPlayingIndex(index)
              }

              utterance.onend = () => {
                setIsPlaying(false)
                setPlayingIndex(-1)
              }

              utterance.onerror = () => {
                setIsPlaying(false)
                setPlayingIndex(-1)
                showToast('error', language === 'en' ? 'Failed to play audio' : '播放语音失败')
              }

              utteranceRef.current = utterance
              speechSynthesis.speak(utterance)
            }
            
            await audio.play()
          } catch (error) {
            console.error('Error creating audio element:', error)
            // Fallback to browser TTS if audio creation fails
            showToast('warning', language === 'en' ? 'Using browser TTS (Volcano Engine audio failed)' : '使用浏览器TTS（火山引擎音频失败）')
            const utterance = new SpeechSynthesisUtterance(text)
            utterance.lang = language === 'en' ? 'en-US' : 'zh-CN'
            utterance.rate = ttsSpeed
            utterance.pitch = 1.0

            utterance.onstart = () => {
              console.log('Browser TTS fallback playing')
              setIsPlaying(true)
              setPlayingIndex(index)
            }

            utterance.onend = () => {
              setIsPlaying(false)
              setPlayingIndex(-1)
            }

            utterance.onerror = (event) => {
              console.error('Fallback TTS Error:', event)
              setIsPlaying(false)
              setPlayingIndex(-1)
              showToast('error', language === 'en' ? 'Failed to play audio' : '播放语音失败')
            }

            utteranceRef.current = utterance
            speechSynthesis.speak(utterance)
          }
        } else if (data.error) {
          showToast('error', data.error)
          setIsPlaying(false)
          setPlayingIndex(-1)
        }
      } else {
        console.error('TTS service error:', response.status)
        showToast('error', language === 'en' ? 'TTS service error' : '语音合成服务错误')
        setIsPlaying(false)
        setPlayingIndex(-1)
      }
    } catch (error: unknown) {
      // AbortError means user clicked stop/replay — don't start a fallback.
      if (error instanceof DOMException && error.name === 'AbortError') return
      console.error('TTS Error:', error)
      // Fallback to browser TTS if backend fails
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = language === 'en' ? 'en-US' : 'zh-CN'
      utterance.rate = ttsSpeed
      utterance.pitch = 1.0

      utterance.onstart = () => {
        setIsPlaying(true)
        setPlayingIndex(index)
      }

      utterance.onend = () => {
        setIsPlaying(false)
        setPlayingIndex(-1)
      }

      utterance.onerror = () => {
        setIsPlaying(false)
        setPlayingIndex(-1)
        showToast('error', language === 'en' ? 'Failed to play audio' : '播放语音失败')
      }

      utteranceRef.current = utterance
      speechSynthesis.speak(utterance)
    }
  }

  // Manual depth switch
  const changeDepth = (newDepth: DepthLevel) => {
    setDepthLevel(newDepth)
    showToast("info", language === "en" ? `Level changed to ${getDepthLabel(newDepth)}` : `深度已切换为${getDepthLabel(newDepth)}`)
  }

  // Select exhibit
  const selectExhibit = (exhibit: Exhibit) => {
    setCurrentExhibit(exhibit)
    setMessages([])
    setChatError(null)
    if (speechSynthesis.speaking) {
      speechSynthesis.cancel()
      isAutoPlayingRef.current = false
      setIsPlaying(false)
      setPlayingIndex(-1)
    }
    setDepthLevel("entry") // reset to entry for new exhibit
    const targetId = (exhibit as any).originalId || exhibit.id
    sendMessage(language === "en" ? "Tell me about this object" : "介绍一下这个文物", targetId, true)
  }

  // Smart sentence breaks for streaming TTS
  const findSentenceBreaks = (text: string): number[] => {
    const breaks: number[] = []
    const sentenceEnds = /[.!?。！？、；，]+/g
    let match
    while ((match = sentenceEnds.exec(text)) !== null) {
      breaks.push(match.index + match[0].length)
    }
    return breaks
  }

  // Fetch a TTS audio element from the backend without blocking.
  const fetchAudioElement = async (text: string): Promise<HTMLAudioElement | null> => {
    try {
      const response = await fetch(`${API_BASE_URL}/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language }),
      })
      if (!response.ok) return null
      const data = await response.json()
      if (!data.audio) return null
      return new Audio(`data:audio/mp3;base64,${data.audio}`)
    } catch {
      return null
    }
  }

  // Start fetching the next sentence into nextAudioPromiseRef so it is ready
  // (or nearly ready) by the time the current sentence finishes playing.
  const prefetchNextSegment = (buffer: string, breakIndex: number) => {
    const remaining = buffer.substring(breakIndex)
    if (remaining.length < 30) return
    const nextBreaks = findSentenceBreaks(remaining)
    if (nextBreaks.length === 0 || nextBreaks[0] < 15) return
    const nextText = remaining.substring(0, nextBreaks[0])
    nextAudioPromiseRef.current = fetchAudioElement(nextText)
  }

  // Play buffered SSE content sentence-by-sentence with 1-segment lookahead.
  // `preloaded` is an already-fetched audio element from the previous segment's
  // pre-fetch; passing it skips the network round-trip entirely.
  const playBufferedContent = async (preloaded?: HTMLAudioElement | null) => {
    if (speechSynthesis.speaking || isAutoPlayingRef.current) return

    const buffer = streamBufferRef.current
    if (buffer.length < 50) return

    const breaks = findSentenceBreaks(buffer)
    if (breaks.length === 0) return

    const breakIndex = Math.min(breaks[0], buffer.length)
    const textToSpeak = buffer.substring(0, breakIndex)
    if (textToSpeak.trim().length < 10) return

    isAutoPlayingRef.current = true

    // Use pre-fetched audio when available, otherwise fetch now.
    const audio = preloaded !== undefined ? preloaded : await fetchAudioElement(textToSpeak)

    if (!audio) {
      // Backend unavailable — fall back to browser speech synthesis.
      const utterance = new SpeechSynthesisUtterance(textToSpeak)
      utterance.lang = language === "en" ? "en-US" : "zh-CN"
      utterance.rate = ttsSpeed
      utterance.pitch = 1.0
      utterance.onstart = () => {
        setIsPlaying(true)
        setPlayingIndex(currentPlayIndexRef.current)
      }
      utterance.onend = () => {
        streamBufferRef.current = streamBufferRef.current.substring(breakIndex)
        isAutoPlayingRef.current = false
        setIsPlaying(false)
        if (streamBufferRef.current.length > 50) setTimeout(() => playBufferedContent(), 100)
      }
      utterance.onerror = () => { isAutoPlayingRef.current = false; setIsPlaying(false) }
      speechSynthesis.speak(utterance)
      return
    }

    // Kick off next-segment pre-fetch immediately so it runs in parallel
    // with the current audio playing (~1-2 s overlap eliminates the gap).
    prefetchNextSegment(buffer, breakIndex)

    // Register as the current audio so stopAllAudio() can cancel it.
    currentAudioRef.current = audio

    audio.onplay = () => {
      setIsPlaying(true)
      setPlayingIndex(currentPlayIndexRef.current)
    }

    audio.onended = () => {
      if (currentAudioRef.current === audio) currentAudioRef.current = null
      streamBufferRef.current = streamBufferRef.current.substring(breakIndex)
      isAutoPlayingRef.current = false
      setIsPlaying(false)

      if (streamBufferRef.current.length > 50) {
        const promise = nextAudioPromiseRef.current
        nextAudioPromiseRef.current = null
        if (promise) {
          // Hand off the pre-fetched audio — zero gap when already resolved.
          promise.then(next => playBufferedContent(next))
        } else {
          setTimeout(() => playBufferedContent(), 100)
        }
      }
    }

    audio.onerror = () => {
      if (currentAudioRef.current === audio) currentAudioRef.current = null
      isAutoPlayingRef.current = false
      setIsPlaying(false)
    }

    try {
      await audio.play()
    } catch {
      if (currentAudioRef.current === audio) currentAudioRef.current = null
      isAutoPlayingRef.current = false
      setIsPlaying(false)
    }
  }

  // Send chat message with streaming + real-time TTS!
  const sendMessage = async (text: string, exhibitId?: string, isInitial = false) => {
    const exId = exhibitId || (currentExhibit as any).originalId || currentExhibit?.id
    if (!exId) return

    const userMessage = text.trim()
    if (!userMessage) return

    if (!isInitial) {
      setMessages(prev => [...prev, { role: "user", content: userMessage }])
    }
    
    setInputText("")
    setIsLoading(true)
    setChatError(null)

    // Stop all previous audio (HTMLAudioElement + speech synthesis + streaming pipeline)
    stopAllAudio()
    
    // New message index
    const currentMessageIndex = isInitial ? 0 : messages.length + (isInitial ? 0 : 1)
    currentPlayIndexRef.current = currentMessageIndex

    // Add placeholder for streaming
    if (!isInitial) {
      setMessages(prev => [...prev, { role: "assistant", content: "", isStreaming: true }])
    } else {
      setMessages([{ role: "assistant", content: "", isStreaming: true }])
    }

    try {
      const res = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId,
          exhibitId: exId,
          userInput: userMessage,
          language,
          depthLevel
        })
      })

      if (!res.ok) {
        throw new Error(language === "en" ? "Server error" : "服务器错误")
      }

      // Streaming response + real-time TTS!
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let done = false
      let fullText = ""
      let hasStartedTTS = false

      while (!done && reader) {
        const { done: doneReading, value } = await reader.read()
        done = doneReading
        
        if (value) {
          const chunk = decoder.decode(value, { stream: true })
          fullText += chunk
          
          // --- Real-time TTS integration! ---
          streamBufferRef.current += chunk
          
          // Try to start playing if we have enough content
          if (!hasStartedTTS && streamBufferRef.current.length > 50) {
            hasStartedTTS = true
            const breaks = findSentenceBreaks(streamBufferRef.current)
            if (breaks.length > 0 && breaks[0] > 20) {
              playBufferedContent()
            }
          }
          // Don't auto-trigger playBufferedContent here - let audio.onended handle continuation
          
          setMessages(prev => {
            const newMessages = [...prev]
            newMessages[newMessages.length - 1] = { 
              role: "assistant", 
              content: fullText,
              isStreaming: true
            }
            return newMessages
          })
        }
      }
      
      // Mark as complete
      setMessages(prev => {
        const newMessages = [...prev]
        newMessages[newMessages.length - 1] = { 
          role: "assistant", 
          content: fullText,
          isStreaming: false
        }
        return newMessages
      })
      
      // Play any remaining content
      if (streamBufferRef.current.length > 30) {
        setTimeout(playBufferedContent, 300)
      }
    } catch (err) {
      console.error("Failed to send message:", err)
      setChatError(language === "en" ? "Unable to send message. Please check your connection." : "无法发送消息。请检查网络连接。")
      showToast("error", language === "en" ? "Failed to send message" : "发送消息失败")
    } finally {
      setIsLoading(false)
    }
  }

  // Retry loading exhibits
  const retryLoadExhibits = () => {
    setExhibitsLoading(true)
    setExhibitsError(null)
    fetch(`${API_BASE_URL}/exhibits`)
      .then(res => res.json())
      .then(setExhibits)
      .catch(() => setExhibitsError(language === "en" ? "Unable to load exhibits." : "无法加载展品。"))
      .finally(() => setExhibitsLoading(false))
  }

  // Exhibit skeleton loader
  const ExhibitSkeleton = () => (
    <>
      {[1, 2, 3, 4, 5, 6].map(i => (
        <motion.div 
          key={i} 
          className="bg-white rounded-xl shadow-xl overflow-hidden"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1 }}
        >
          <div className="w-full h-64 bg-gray-200" />
          <div className="p-6 space-y-3">
            <div className="h-6 bg-gray-200 rounded w-3/4" />
            <div className="h-4 bg-gray-200 rounded w-1/2" />
            <div className="h-3 bg-gray-200 rounded w-1/3" />
          </div>
        </motion.div>
      ))}
    </>
  )

  // Toast container
  const ToastContainer = () => (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      <AnimatePresence>
        {toasts.map(toast => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 100 }}
            className={`px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 ${
              toast.type === "success" ? "bg-green-500 text-white" :
              toast.type === "error" ? "bg-red-500 text-white" :
              "bg-blue-500 text-white"
            }`}
          >
            {toast.type === "success" && (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            )}
            {toast.type === "error" && (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
            {toast.type === "info" && (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
            <span className="font-medium">{toast.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )

  // Loading spinner
  const LoadingSpinner = () => (
    <div className="flex justify-center items-center py-10">
      <div className="w-10 h-10 border-4 border-t-[#FCD34D] border-slate-700 rounded-full animate-spin" />
    </div>
  )

  // Exhibit list view
  if (!currentExhibit) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0F172A] to-[#1E293B]">
        <ToastContainer />
        <header className="py-16">
          <div className="max-w-5xl mx-auto px-6 text-center">
            <motion.h1 
              className="text-5xl font-serif font-bold text-[#FCD34D] mb-4"
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
            >
              Shanghai Museum
            </motion.h1>
            <motion.p 
              className="text-xl font-light text-slate-200 mb-10"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              AI Tour Guide
            </motion.p>
            <motion.div 
              className="flex gap-4 justify-center flex-wrap"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
            >
              <button
                onClick={() => setLanguage("en")}
                className={`px-8 py-3 rounded-full font-medium transition-all ${
                  language === "en" ? "bg-gradient-to-r from-[#FCD34D] to-[#FBBF24] text-[#0F172A] shadow-lg" : "bg-white/10 text-slate-200 hover:bg-white/20"
                }`}
              >
                English
              </button>
              <button
                onClick={() => setLanguage("zh")}
                className={`px-8 py-3 rounded-full font-medium transition-all ${
                  language === "zh" ? "bg-gradient-to-r from-[#FCD34D] to-[#FBBF24] text-[#0F172A] shadow-lg" : "bg-white/10 text-slate-200 hover:bg-white/20"
                }`}
              >
                中文
              </button>
            </motion.div>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-6 py-12">
          <motion.h2 
            className="text-3xl font-serif font-semibold mb-12 text-center text-slate-100"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            {language === "en" ? "Select an exhibit to begin" : "选择一件展品开始游览"}
          </motion.h2>
          
          {exhibitsError && (
            <motion.div 
              className="bg-red-900/20 backdrop-blur-sm border border-red-500/30 rounded-xl p-8 text-center mb-12"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <div className="text-red-400 mb-6">
                <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-xl font-serif font-semibold text-red-300 mb-4">
                {language === "en" ? "Oops! Something went wrong" : "出了点问题！"}
              </h3>
              <p className="text-red-300 mb-6">{exhibitsError}</p>
              <button
                onClick={retryLoadExhibits}
                className="px-8 py-3 bg-gradient-to-r from-[#FCD34D] to-[#FBBF24] text-[#0F172A] rounded-full font-medium hover:from-[#F59E0B] hover:to-[#D97706] transition-colors flex items-center gap-2 mx-auto"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {language === "en" ? "Retry" : "重试"}
              </button>
            </motion.div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {exhibitsLoading ? (
              <ExhibitSkeleton />
            ) : (
              exhibits.map((exhibit, index) => (
                <motion.div
                  key={exhibit.id}
                  onClick={() => selectExhibit(exhibit)}
                  className="bg-slate-800/50 backdrop-blur-sm rounded-xl overflow-hidden cursor-pointer hover:bg-slate-700/50 transition-all group border border-slate-700/50"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ 
                    y: -10, 
                    boxShadow: "0 20px 25px -5px rgba(252, 211, 77, 0.1), 0 10px 10px -5px rgba(252, 211, 77, 0.04)"
                  }}
                >
                  <div className="relative overflow-hidden h-64">
                    {exhibit.imageUrl ? (
                      <img
                        src={exhibit.imageUrl}
                        alt={exhibit.name.en}
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                      />
                    ) : (
                      <div className="w-full h-full bg-slate-700 flex items-center justify-center">
                        <svg className="w-16 h-16 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </div>
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-90" />
                    <div className="absolute bottom-4 left-4 right-4 text-white">
                      <h3 className="text-lg font-serif font-semibold mb-1 text-slate-100">
                        {language === "en" ? exhibit.name.en : exhibit.name.zh}
                      </h3>
                      {exhibit.dynasty && <p className="text-sm text-slate-300">{exhibit.dynasty}</p>}
                    </div>
                  </div>
                  <div className="p-5 border-t border-slate-700/50">
                    <p className="text-sm text-slate-400">{exhibit.hall ?? exhibit.hallId}</p>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </main>
        <footer className="py-8 text-center text-slate-500 text-sm">
          <p>Shanghai Museum AI Guide © 2026</p>
        </footer>
      </div>
    )
  }

  // Normalize quickQuestions to a flat string array for the current language
  const questions: string[] = Array.isArray(currentExhibit?.quickQuestions)
    ? (currentExhibit.quickQuestions as string[])
    : ((currentExhibit?.quickQuestions as BilingualList)?.[language] ?? [])

  // Chat view with Louvre style!
  return (
    <div className="min-h-screen bg-[#0F172A]">
      <ToastContainer />
      
      {/* Hero section with exhibit image */}
      <div className="relative h-[40vh] min-h-[300px] overflow-hidden">
        <div className="absolute inset-0">
          {currentExhibit.imageUrl ? (
            <img
              src={currentExhibit.imageUrl}
              alt={currentExhibit.name.en}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full bg-slate-800" />
          )}
          <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-black/60 to-black/80" />
        </div>
        
        {/* Navigation */}
        <div className="absolute inset-0 flex items-center px-6">
          <div className="max-w-5xl mx-auto w-full flex items-center justify-between">
            <motion.button
              onClick={() => setCurrentExhibit(null)}
              className="p-3 bg-slate-800/80 backdrop-blur-sm rounded-full text-slate-200 hover:bg-slate-700/80 transition-colors"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </motion.button>
            
            <div className="text-center flex-1">
              <motion.h1 
                className="text-3xl font-serif font-bold text-slate-100 mb-2"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                {language === "en" ? currentExhibit.name.en : currentExhibit.name.zh}
              </motion.h1>
              <motion.p 
                className="text-sm text-slate-300"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
              >
                {currentExhibit.dynasty ?? currentExhibit.dynastyId}
                {" • "}
                {currentExhibit.hall ?? currentExhibit.hallId}
              </motion.p>
            </div>
            
            <div className="w-12"></div> {/* Spacer */}
          </div>
        </div>
      </div>
      
      {/* Entity chips for hall / dynasty / persons */}
      {currentExhibit && (
        <div className="bg-[#1E293B] px-6 pt-4 pb-2 max-w-5xl mx-auto flex flex-wrap">
          {currentExhibit.hallId && halls[currentExhibit.hallId] && (
            <EntityChip
              label={halls[currentExhibit.hallId].name[language]}
              onClick={() => setDrawerTarget({ type: "hall", id: currentExhibit.hallId })}
            />
          )}
          {currentExhibit.dynastyId && dynasties[currentExhibit.dynastyId] && (
            <EntityChip
              label={dynasties[currentExhibit.dynastyId].name[language]}
              onClick={() => setDrawerTarget({ type: "dynasty", id: currentExhibit.dynastyId })}
            />
          )}
          {(currentExhibit.personIds || []).map(pid => persons[pid] ? (
            <EntityChip
              key={pid}
              label={persons[pid].name[language]}
              onClick={() => setDrawerTarget({ type: "person", id: pid })}
            />
          ) : null)}
        </div>
      )}

      {/* Control bar */}
      <div className="bg-[#1E293B] border-b border-[#FCD34D]/20 py-4">
        <div className="max-w-5xl mx-auto px-6 flex items-center justify-between flex-wrap gap-4">
          {/* Depth control */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-[#FCD34D] font-medium">
              {language === "en" ? "Level:" : "深度:"}
            </span>
            <div className="flex gap-2">
              {(["entry", "deeper", "expert"] as DepthLevel[]).map(d => (
                <motion.button
                  key={d}
                  onClick={() => changeDepth(d)}
                  className={`px-5 py-2 rounded-full text-sm font-medium transition-all ${
                    depthLevel === d 
                      ? "bg-gradient-to-r from-[#FCD34D] to-[#FBBF24] text-[#0F172A] shadow-lg" 
                      : "bg-slate-700/50 text-slate-300 hover:bg-slate-600/50"
                  }`}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {getDepthLabel(d)}
                </motion.button>
              ))}
            </div>
          </div>
          
          {/* TTS speed */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-[#FCD34D] font-medium">
              {language === "en" ? "Speed:" : "语速:"}
            </span>
            <select
              value={ttsSpeed}
              onChange={(e) => setTtsSpeed(parseFloat(e.target.value) as TTSSpeed)}
              className="px-4 py-2 bg-slate-700/50 text-slate-200 rounded-full text-sm border border-[#FCD34D]/30"
            >
              <option value={0.75}>0.75x {language === "en" ? "Slow" : "慢"}</option>
              <option value={0.9}>0.9x {language === "en" ? "Normal" : "正常"}</option>
              <option value={1.0}>1.0x</option>
              <option value={1.1}>1.1x</option>
              <option value={1.25}>1.25x {language === "en" ? "Fast" : "快"}</option>
            </select>
          </div>
        </div>
      </div>
      
      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex-1 overflow-y-auto space-y-6 mb-6 max-h-[60vh]">
          {messages.map((msg, idx) => (
            <motion.div
              key={idx}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div
                className={`max-w-[80%] px-6 py-4 rounded-2xl relative ${
                  msg.role === "user"
                    ? "bg-gradient-to-r from-[#3B82F6] to-[#2563EB] text-white shadow-lg"
                    : "bg-slate-800/80 text-slate-200 shadow-lg border border-slate-700/50"
                }`}
              >
                <p className="whitespace-pre-line leading-relaxed">{msg.content}</p>
                {msg.isStreaming && (
                  <div className="flex gap-1 mt-2">
                    {[1, 2, 3].map((dot, i) => (
                      <span 
                        key={i} 
                        className="w-2 h-2 bg-[#FCD34D] rounded-full animate-bounce"
                        style={{ animationDelay: `${i * 0.1}s` }}
                      />
                    ))}
                  </div>
                )}
                {msg.role === "assistant" && !msg.isStreaming && (
                  <div className="flex gap-2 justify-end mt-3">
                    <motion.button
                      onClick={() => speakText(msg.content, idx)}
                      className={`p-2 rounded-full transition-all ${
                        isPlaying && playingIndex === idx 
                          ? "bg-[#FCD34D] text-[#0F172A]"
                          : "bg-slate-700/50 text-slate-300 hover:bg-[#FCD34D]/20 hover:text-[#FCD34D]"
                      }`}
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                    >
                      {isPlaying && playingIndex === idx ? (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      )}
                    </motion.button>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
          {isLoading && messages.length === 0 && (
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          )}
          {chatError && !isLoading && (
            <motion.div 
              className="bg-red-900/20 border border-red-500/30 rounded-lg p-5"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-red-400 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div className="flex-1">
                  <p className="text-red-300 mb-3">{chatError}</p>
                  <motion.button
                    onClick={() => {
                      setChatError(null)
                      if (messages.length > 0) {
                        const lastUserMsg = messages.slice().reverse().find(m => m.role === "user")
                        if (lastUserMsg) {
                          sendMessage(lastUserMsg.content)
                        }
                      }
                    }}
                    className="text-[#FCD34D] hover:text-[#FBBF24] text-sm font-medium flex items-center gap-1"
                    whileHover={{ scale: 1.05 }}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    {language === "en" ? "Retry" : "重试"}
                  </motion.button>
                </div>
              </div>
            </motion.div>
          )}
        </div>
        
        {/* Quick questions */}
        <div className="flex flex-wrap gap-3 mb-6">
          {questions.map((q, idx) => (
            <motion.button
              key={idx}
              onClick={() => sendMessage(q)}
              disabled={isLoading}
              className="px-4 py-2 bg-slate-700/50 text-slate-300 text-sm rounded-full hover:bg-[#FCD34D]/20 hover:text-[#FCD34D] disabled:opacity-50 disabled:cursor-not-allowed transition-all border border-slate-600/50"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {q}
            </motion.button>
          ))}
        </div>

        {/* Input form */}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            sendMessage(inputText)
          }}
          className="flex gap-3"
        >
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={language === "en" ? "Ask a question..." : "询问问题..."}
            className="flex-1 px-5 py-3 bg-slate-800 border border-slate-700 rounded-full focus:outline-none focus:border-[#FCD34D] focus:ring-2 focus:ring-[#FCD34D]/30 text-slate-200"
          />
          <motion.button
            type="button"
            onClick={isRecording ? stopVoiceInput : startVoiceInput}
            disabled={isTranscribing}
            title={isTranscribing ? (language === 'en' ? 'Recognizing…' : '识别中…') : isRecording ? (language === 'en' ? 'Stop recording' : '停止录音') : (language === 'en' ? 'Start recording' : '开始录音')}
            className={`p-3 rounded-full transition-all ${
              isTranscribing
                ? "bg-yellow-500 text-white animate-pulse cursor-wait"
                : isRecording
                  ? "bg-red-500 text-white animate-pulse"
                  : "bg-slate-700 text-slate-200 hover:bg-slate-600"
            }`}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
          >
            {isTranscribing ? (
              <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin block" />
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {isRecording ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                )}
              </svg>
            )}
          </motion.button>
          <motion.button
            type="submit"
            disabled={!inputText.trim() || isLoading}
            className="px-6 py-3 bg-gradient-to-r from-[#FCD34D] to-[#FBBF24] text-[#0F172A] font-medium rounded-full hover:from-[#F59E0B] hover:to-[#D97706] disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-[#0F172A] border-t-transparent rounded-full animate-spin" />
                {language === "en" ? "Speaking..." : "发送中..."}
              </span>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                {language === "en" ? "Send" : "发送"}
              </>
            )}
          </motion.button>
        </form>
      </main>

      <EntityDrawer
        target={drawerTarget}
        onClose={() => setDrawerTarget(null)}
        language={language}
        halls={halls}
        dynasties={dynasties}
        persons={persons}
        onPickExhibit={(ex) => selectExhibit(ex)}
      />
    </div>
  )
}

export default App
