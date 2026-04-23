import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition
    webkitSpeechRecognition: typeof SpeechRecognition
  }
}

const API_BASE_URL = "http://127.0.0.1:8080"

interface Exhibit {
  id: string
  originalId?: string
  name: { en: string; zh: string }
  imageUrl: string
  dynasty: string
  period: string
  hall: string
  quickQuestions: string[]
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
  
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)
  const streamBufferRef = useRef<string>("")
  const currentPlayIndexRef = useRef<number>(-1)
  const isAutoPlayingRef = useRef<boolean>(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

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

  // Stop speaking on unmount
  useEffect(() => {
    return () => {
      if (speechSynthesis.speaking) {
        speechSynthesis.cancel()
      }
    }
  }, [])

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
        setIsRecording(false)
        
        try {
          // Create audio blob
          const audioBlob = new Blob(audioChunks, { type: 'audio/wav' })
          
          // Convert to base64
          const reader = new FileReader()
          reader.onloadend = async () => {
            const base64Audio = (reader.result as string).split(',')[1]
            
            // Send to backend ASR
            const response = await fetch(`${API_BASE_URL}/asr`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                audio: base64Audio,
                language: language
              })
            })
            
            if (response.ok) {
              const data = await response.json()
              if (data.text) {
                setInputText(prev => prev + data.text)
                showToast('success', language === 'en' ? 'Voice recognized' : '语音已识别')
              } else if (data.error) {
                showToast('error', data.error)
              }
            } else {
              showToast('error', language === 'en' ? 'ASR service error' : '语音识别服务错误')
            }
          }
          reader.readAsDataURL(audioBlob)
        } catch (error) {
          console.error('Error processing audio:', error)
          showToast('error', language === 'en' ? 'Error processing audio' : '处理音频时出错')
        } finally {
          // Stop all tracks
          stream.getTracks().forEach(track => track.stop())
        }
      }
      
      mediaRecorder.onerror = (error) => {
        console.error('MediaRecorder error:', error)
        setIsRecording(false)
        showToast('error', language === 'en' ? 'Error starting recorder' : '启动录音失败')
        stream.getTracks().forEach(track => track.stop())
      }
      
      // Start recording
      mediaRecorder.start()
      setIsRecording(true)
      
      // Stop recording after 10 seconds (timeout)
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
    // MediaRecorder will automatically stop after recording
    setIsRecording(false)
  }

  // Depth label
  const getDepthLabel = (depth: DepthLevel) => {
    if (language === "en") {
      return depth === "entry" ? "Beginner" : depth === "deeper" ? "Intermediate" : "Expert"
    }
    return depth === "entry" ? "入门" : depth === "deeper" ? "进阶" : "专家"
  }

  // TTS functions - with speed support!
  const speakText = async (text: string, index: number) => {
    if (speechSynthesis.speaking) {
      speechSynthesis.cancel()
      isAutoPlayingRef.current = false
      if (isPlaying && playingIndex === index) {
        setIsPlaying(false)
        setPlayingIndex(-1)
        return
      }
    }

    currentPlayIndexRef.current = index
    isAutoPlayingRef.current = false
    streamBufferRef.current = text
    
    try {
      // Use Volcano Engine TTS service
      const response = await fetch(`${API_BASE_URL}/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text,
          language: language
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        console.log('TTS Response:', data)
        
        if (data.audio) {
          // Create audio element and play
          try {
            const audio = new Audio(`data:audio/mp3;base64,${data.audio}`)
            
            audio.onplay = () => {
              console.log('Volcano Engine TTS playing')
              setIsPlaying(true)
              setPlayingIndex(index)
            }
            
            audio.onended = () => {
              setIsPlaying(false)
              setPlayingIndex(-1)
            }
            
            audio.onerror = () => {
              console.error('Audio playback error')
              setIsPlaying(false)
              setPlayingIndex(-1)
              showToast('warning', language === 'en' ? 'Using browser TTS (Volcano Engine audio failed)' : '使用浏览器TTS（火山引擎音频失败）')
              // Fallback to browser TTS
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
    } catch (error) {
      console.error('TTS Error:', error)
      // Fallback to browser TTS if Volcano Engine fails
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

      utterance.onerror = (event) => {
        console.error('Fallback TTS Error:', event)
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

  // Play buffered content - with speed support!
  const playBufferedContent = async () => {
    if (speechSynthesis.speaking || isAutoPlayingRef.current) return
    
    const buffer = streamBufferRef.current
    if (buffer.length < 50) return // Need enough content
    
    // Find good sentence breaks
    const breaks = findSentenceBreaks(buffer)
    if (breaks.length === 0) return
    
    // Take first break point
    const breakIndex = Math.min(breaks[0], buffer.length)
    const textToSpeak = buffer.substring(0, breakIndex)
    
    if (textToSpeak.trim().length < 10) return
    
    // Start auto-play!
    isAutoPlayingRef.current = true
    
    try {
      // Use Volcano Engine TTS service
      const response = await fetch(`${API_BASE_URL}/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: textToSpeak,
          language: language
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        
        if (data.audio) {
          // Create audio element and play
          const audio = new Audio(`data:audio/mp3;base64,${data.audio}`)
          
          audio.onplay = () => {
            setIsPlaying(true)
            setPlayingIndex(currentPlayIndexRef.current)
          }
          
          audio.onended = () => {
            // Remove spoken part from buffer
            streamBufferRef.current = streamBufferRef.current.substring(breakIndex)
            isAutoPlayingRef.current = false
            setIsPlaying(false)
            
            // Continue playing remaining content if any
            if (streamBufferRef.current.length > 50) {
              setTimeout(playBufferedContent, 100)
            }
          }
          
          audio.onerror = () => {
            isAutoPlayingRef.current = false
            setIsPlaying(false)
          }
          
          await audio.play()
        } else {
          isAutoPlayingRef.current = false
          setIsPlaying(false)
        }
      } else {
        // Fallback to browser TTS if Volcano Engine fails
        const utterance = new SpeechSynthesisUtterance(textToSpeak)
        utterance.lang = language === "en" ? "en-US" : "zh-CN"
        utterance.rate = ttsSpeed
        utterance.pitch = 1.0
        
        utterance.onstart = () => {
          setIsPlaying(true)
          setPlayingIndex(currentPlayIndexRef.current)
        }
        
        utterance.onend = () => {
          // Remove spoken part from buffer
          streamBufferRef.current = streamBufferRef.current.substring(breakIndex)
          isAutoPlayingRef.current = false
          setIsPlaying(false)
          
          // Continue playing remaining content if any
          if (streamBufferRef.current.length > 50) {
            setTimeout(playBufferedContent, 100)
          }
        }
        
        utterance.onerror = () => {
          isAutoPlayingRef.current = false
          setIsPlaying(false)
        }
        
        speechSynthesis.speak(utterance)
      }
    } catch (error) {
      console.error('Auto-play TTS Error:', error)
      // Fallback to browser TTS
      const utterance = new SpeechSynthesisUtterance(textToSpeak)
      utterance.lang = language === "en" ? "en-US" : "zh-CN"
      utterance.rate = ttsSpeed
      utterance.pitch = 1.0
      
      utterance.onstart = () => {
        setIsPlaying(true)
        setPlayingIndex(currentPlayIndexRef.current)
      }
      
      utterance.onend = () => {
        // Remove spoken part from buffer
        streamBufferRef.current = streamBufferRef.current.substring(breakIndex)
        isAutoPlayingRef.current = false
        setIsPlaying(false)
        
        // Continue playing remaining content if any
        if (streamBufferRef.current.length > 50) {
          setTimeout(playBufferedContent, 100)
        }
      }
      
      utterance.onerror = () => {
        isAutoPlayingRef.current = false
        setIsPlaying(false)
      }
      
      speechSynthesis.speak(utterance)
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

    // Stop previous playback
    if (speechSynthesis.speaking) {
      speechSynthesis.cancel()
      isAutoPlayingRef.current = false
    }
    streamBufferRef.current = ""
    
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
                    <img
                      src={exhibit.imageUrl}
                      alt={exhibit.name.en}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-90" />
                    <div className="absolute bottom-4 left-4 right-4 text-white">
                      <h3 className="text-lg font-serif font-semibold mb-1 text-slate-100">
                        {language === "en" ? exhibit.name.en : exhibit.name.zh}
                      </h3>
                      <p className="text-sm text-slate-300">{exhibit.dynasty}</p>
                    </div>
                  </div>
                  <div className="p-5 border-t border-slate-700/50">
                    <p className="text-sm text-slate-400">{exhibit.hall}</p>
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

  // Chat view with Louvre style!
  return (
    <div className="min-h-screen bg-[#0F172A]">
      <ToastContainer />
      
      {/* Hero section with exhibit image */}
      <div className="relative h-[40vh] min-h-[300px] overflow-hidden">
        <div className="absolute inset-0">
          <img
            src={currentExhibit.imageUrl}
            alt={currentExhibit.name.en}
            className="w-full h-full object-cover"
          />
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
                {currentExhibit.dynasty} • {currentExhibit.hall}
              </motion.p>
            </div>
            
            <div className="w-12"></div> {/* Spacer */}
          </div>
        </div>
      </div>
      
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
          {currentExhibit.quickQuestions.map((q, idx) => (
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
            className={`p-3 rounded-full transition-all ${
              isRecording 
                ? "bg-red-500 text-white animate-pulse" 
                : "bg-slate-700 text-slate-200 hover:bg-slate-600"
            }`}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isRecording ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              )}
            </svg>
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
    </div>
  )
}

export default App
