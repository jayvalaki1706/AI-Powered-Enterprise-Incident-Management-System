import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../../services/api'
import Button from '../../components/common/Button'
import Loading from '../../components/common/Loading'
import toast from 'react-hot-toast'

const TABS = [
  { id: 'logs', label: '📋 Analyze Logs' },
  { id: 'resolution', label: '🔧 Suggest Fixes' },
  { id: 'sop', label: '📖 Generate SOP' },
  { id: 'rca', label: '🔍 Generate RCA' },
  { id: 'chat', label: '💬 Chat' },
]

export default function AIAssistantPage() {
  const [activeTab, setActiveTab] = useState('logs')

  return (
    <div className="space-y-4">
      {/* AI Status Bar - shown at top of page */}
      <div className="flex items-center justify-between bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl px-5 py-3 text-white">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🤖</span>
          <div>
            <h1 className="text-lg font-bold">AI Assistant</h1>
            <p className="text-xs text-white/70">Powered by Ollama - runs locally, free of cost</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs text-white/80">Model Active</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors ${
              activeTab === tab.id
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'logs' && <LogAnalysisTab />}
      {activeTab === 'resolution' && <ResolutionTab />}
      {activeTab === 'sop' && <SOPTab />}
      {activeTab === 'rca' && <RCATab />}
      {activeTab === 'chat' && <ChatTab />}
    </div>
  )
}

// ─── Log Analysis Tab ────────────────────────────────────────────────────────────

function LogAnalysisTab() {
  const [logs, setLogs] = useState('')
  const [result, setResult] = useState(null)

  const mutation = useMutation({
    mutationFn: (data) => api.post('/ai/analyze-logs', data, { timeout: 300000 }).then((r) => r.data),
    onSuccess: (data) => setResult(data),
    onError: (err) => {
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        toast.error('AI is taking too long. Try with shorter logs or a faster model.')
      } else {
        toast.error(err.response?.data?.message || err.response?.data?.detail || 'Analysis failed. Make sure Ollama is running.')
      }
    },
  })

  return (
    <div className="space-y-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-3">Upload / Paste Logs</h2>
        <textarea
          value={logs}
          onChange={(e) => setLogs(e.target.value)}
          placeholder="Paste your log content here...\n\n2024-07-16 10:23:45 ERROR [app.server] Connection timeout to database\n2024-07-16 10:23:46 WARN [app.pool] Connection pool exhausted..."
          rows={10}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex gap-3 mt-3">
          <Button onClick={() => mutation.mutate({ log_content: logs })} loading={mutation.isPending} disabled={logs.length < 10}>
            🔍 Analyze Logs
          </Button>
          {result && <Button variant="secondary" onClick={() => setResult(null)}>Clear Results</Button>}
        </div>
      </div>

      {mutation.isPending && <LoadingCard text="Analyzing logs with AI..." />}

      {result && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 dark:text-white">Analysis Results</h2>
            <span className={`px-2 py-1 rounded text-xs font-bold ${
              result.severity === 'critical' ? 'bg-red-100 text-red-700' :
              result.severity === 'high' ? 'bg-orange-100 text-orange-700' :
              result.severity === 'medium' ? 'bg-yellow-100 text-yellow-700' :
              'bg-green-100 text-green-700'
            }`}>{result.severity?.toUpperCase()}</span>
          </div>
          <ResultSection title="Summary" content={result.summary} />
          <ResultSection title="Probable Cause" content={result.probable_cause} />
          <ResultList title="Resolution Steps" items={result.resolution_steps} />
          <ResultList title="Affected Components" items={result.affected_components} />
          <p className="text-xs text-gray-500">Confidence: {Math.round((result.confidence || 0) * 100)}%</p>
        </div>
      )}
    </div>
  )
}

// ─── Resolution Tab ──────────────────────────────────────────────────────────────

function ResolutionTab() {
  return <IncidentActionTab endpoint="/ai/suggest-resolution" title="Resolution Suggestions" renderResult={(r) => (
    <div className="space-y-4">
      <ResultSection title="Summary" content={r.summary} />
      <ResultSection title="Root Cause" content={r.root_cause} />
      <ResultList title="Resolution Steps" items={r.resolution_steps} ordered />
      <ResultList title="Preventive Measures" items={r.preventive_measures} />
      <ResultSection title="Estimated Effort" content={r.estimated_effort} />
      <p className="text-xs text-gray-500">Confidence: {Math.round((r.confidence || 0) * 100)}%</p>
    </div>
  )} />
}

// ─── SOP Tab ─────────────────────────────────────────────────────────────────────

function SOPTab() {
  return <IncidentActionTab endpoint="/ai/generate-sop" title="Standard Operating Procedure" renderResult={(r) => (
    <div className="space-y-4">
      <ResultSection title="Title" content={r.title} />
      <ResultSection title="Purpose" content={r.purpose} />
      <ResultSection title="Scope" content={r.scope} />
      <ResultList title="Prerequisites" items={r.prerequisites} />
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Steps</h3>
        <div className="space-y-2">
          {r.steps?.map((step) => (
            <div key={step.step_number} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <p className="font-medium text-gray-900 dark:text-white text-sm">Step {step.step_number}: {step.action}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Expected: {step.expected_result}</p>
            </div>
          ))}
        </div>
      </div>
      <ResultSection title="Escalation Criteria" content={r.escalation_criteria} />
      <ResultSection title="Rollback Procedure" content={r.rollback_procedure} />
      <ResultSection title="Notes" content={r.notes} />
    </div>
  )} />
}

// ─── RCA Tab ─────────────────────────────────────────────────────────────────────

function RCATab() {
  return <IncidentActionTab endpoint="/ai/generate-rca" title="Root Cause Analysis" renderResult={(r) => (
    <div className="space-y-4">
      <ResultSection title="Incident" content={r.incident_title} />
      <ResultSection title="Summary" content={r.summary} />
      <ResultSection title="Root Cause" content={r.root_cause} />
      <ResultList title="Contributing Factors" items={r.contributing_factors} />
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">5 Whys Analysis</h3>
        <div className="space-y-2">
          {r.five_whys?.map((item, idx) => (
            <div key={idx} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <p className="font-medium text-gray-900 dark:text-white text-sm">{item.why}</p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">→ {item.answer}</p>
            </div>
          ))}
        </div>
      </div>
      <ResultSection title="Impact" content={r.impact} />
      <ResultList title="Timeline" items={r.timeline} />
      <ResultList title="Corrective Actions" items={r.corrective_actions} ordered />
      <ResultList title="Preventive Actions" items={r.preventive_actions} ordered />
      <ResultList title="Lessons Learned" items={r.lessons_learned} />
    </div>
  )} />
}

// ─── Chat Tab ────────────────────────────────────────────────────────────────────

function ChatTab() {
  const [message, setMessage] = useState('')
  const [incidentId, setIncidentId] = useState('')
  const [messages, setMessages] = useState([])

  const { data: incidents } = useQuery({
    queryKey: ['incidents-for-chat'],
    queryFn: () => api.get('/incidents/', { params: { page_size: 50 } }).then((r) => r.data.items),
  })

  // Load chat history when incident changes
  const { data: chatHistory } = useQuery({
    queryKey: ['ai-chat-history', incidentId],
    queryFn: () => api.get(`/ai/history/${incidentId}`, { params: { interaction_type: 'chat' } }).then((r) => r.data),
    enabled: !!incidentId,
  })

  // When history loads, populate messages
  useEffect(() => {
    if (chatHistory && chatHistory.length > 0) {
      const restored = []
      chatHistory.forEach((h) => {
        restored.push({ role: 'user', content: h.input_text })
        restored.push({ role: 'assistant', content: h.output_text })
      })
      setMessages(restored)
    } else if (incidentId) {
      setMessages([])
    }
  }, [chatHistory, incidentId])

  const mutation = useMutation({
    mutationFn: (data) => api.post('/ai/chat', data, { timeout: 300000 }).then((r) => r.data),
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response }])
    },
    onError: (err) => {
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        toast.error('AI is taking too long. Try a simpler question.')
      } else {
        toast.error(err.response?.data?.message || err.response?.data?.detail || 'Chat failed. Make sure Ollama is running.')
      }
    },
  })

  const handleSend = () => {
    if (!message.trim()) return
    const newMessages = [...messages, { role: 'user', content: message }]
    setMessages(newMessages)
    mutation.mutate({
      message,
      incident_id: incidentId || null,
      conversation_history: newMessages,
    })
    setMessage('')
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden flex flex-col h-[calc(100vh-280px)] min-h-[500px]">
      {/* Chat Header */}
      <div className="px-4 py-3 border-b dark:border-gray-700 flex items-center gap-3 shrink-0">
        <span className="text-lg">💬</span>
        <h2 className="font-semibold text-gray-900 dark:text-white text-sm">Chat with AI</h2>
        <select
          value={incidentId}
          onChange={(e) => setIncidentId(e.target.value)}
          className="ml-auto text-xs px-2 py-1 border border-gray-300 rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        >
          <option value="">No incident context</option>
          {incidents?.map((inc) => (
            <option key={inc.id} value={inc.id}>{inc.title}</option>
          ))}
        </select>
      </div>

      {/* Messages - scrollable area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 dark:text-gray-500 py-12">
            <p className="text-3xl mb-2">🤖</p>
            <p>Ask me anything about incidents, logs, or troubleshooting.</p>
            <p className="text-xs mt-1">Select an incident for contextual answers.</p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white whitespace-pre-wrap'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
            }`}>
              {msg.role === 'user' ? msg.content : <FormattedAIResponse text={msg.content} />}
            </div>
          </div>
        ))}
        {mutation.isPending && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-2 text-sm text-gray-500">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input - fixed at bottom */}
      <div className="p-3 border-t dark:border-gray-700 bg-white dark:bg-gray-800 shrink-0">
        <form onSubmit={(e) => { e.preventDefault(); handleSend() }} className="flex gap-2 items-end">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
            placeholder="Ask about an incident, paste logs, or ask for help... (Enter to send, Shift+Enter for new line)"
            rows={2}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <Button type="submit" size="sm" loading={mutation.isPending} disabled={!message.trim()}>Send</Button>
        </form>
      </div>
    </div>
  )
}

// ─── Shared: Incident Action Tab ─────────────────────────────────────────────────

function IncidentActionTab({ endpoint, title, renderResult }) {
  const [incidentId, setIncidentId] = useState('')
  const [result, setResult] = useState(null)

  // Map endpoint to interaction type for history lookup
  const typeMap = {
    '/ai/suggest-resolution': 'suggest_fix',
    '/ai/generate-sop': 'generate_sop',
    '/ai/generate-rca': 'generate_rca',
    '/ai/summarize-incident': 'summarize',
  }
  const interactionType = typeMap[endpoint] || ''

  const { data: incidents } = useQuery({
    queryKey: ['incidents-for-ai'],
    queryFn: () => api.get('/incidents/', { params: { page_size: 50 } }).then((r) => r.data.items),
  })

  // Load history when incident is selected
  const { data: history } = useQuery({
    queryKey: ['ai-history', incidentId, interactionType],
    queryFn: () => api.get(`/ai/history/${incidentId}`, { params: { interaction_type: interactionType } }).then((r) => r.data),
    enabled: !!incidentId && !!interactionType,
  })

  // Show last saved result when incident changes
  useEffect(() => {
    if (history && history.length > 0) {
      try {
        const lastResult = JSON.parse(history[history.length - 1].output_text)
        setResult(lastResult)
      } catch {
        setResult(null)
      }
    } else {
      setResult(null)
    }
  }, [history])

  const mutation = useMutation({
    mutationFn: (data) => api.post(endpoint, data, { timeout: 300000 }).then((r) => r.data),
    onSuccess: (data) => setResult(data),
    onError: (err) => {
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        toast.error('AI is taking too long. The model might be loading. Try again.')
      } else {
        toast.error(err.response?.data?.message || err.response?.data?.detail || 'AI request failed. Make sure Ollama is running.')
      }
    },
  })

  return (
    <div className="space-y-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-3">{title}</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Select an incident to generate AI-powered analysis.</p>
        <select
          value={incidentId}
          onChange={(e) => setIncidentId(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white mb-3"
        >
          <option value="">Select an incident...</option>
          {incidents?.map((inc) => (
            <option key={inc.id} value={inc.id}>[{inc.priority}] {inc.title}</option>
          ))}
        </select>
        <div className="flex gap-3">
          <Button onClick={() => mutation.mutate({ incident_id: incidentId })} loading={mutation.isPending} disabled={!incidentId}>
            🤖 Generate {result && history?.length > 0 ? '(Regenerate)' : ''}
          </Button>
          {result && <Button variant="secondary" onClick={() => setResult(null)}>Clear</Button>}
        </div>
        {history?.length > 0 && result && (
          <p className="text-xs text-gray-400 mt-2">
            ↑ Showing {history.length > 1 ? 'latest of ' + history.length + ' generations' : 'saved result'}. Click Generate to create a new one.
          </p>
        )}
      </div>

      {mutation.isPending && <LoadingCard text="AI is analyzing the incident..." />}

      {result && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          {renderResult(result)}
        </div>
      )}
    </div>
  )
}

// ─── Formatted AI Response (Simple Markdown) ────────────────────────────────────

function FormattedAIResponse({ text }) {
  if (!text) return null

  const lines = text.split('\n')
  const elements = []

  lines.forEach((line, idx) => {
    const trimmed = line.trim()

    // Bold: **text**
    const renderInline = (str) => {
      const parts = str.split(/(\*\*.*?\*\*)/g)
      return parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i}>{part.slice(2, -2)}</strong>
        }
        return part
      })
    }

    // Heading: lines starting with # or ##
    if (trimmed.startsWith('### ')) {
      elements.push(<p key={idx} className="font-semibold mt-2 mb-1">{renderInline(trimmed.slice(4))}</p>)
    } else if (trimmed.startsWith('## ')) {
      elements.push(<p key={idx} className="font-bold mt-3 mb-1 text-base">{renderInline(trimmed.slice(3))}</p>)
    } else if (trimmed.startsWith('# ')) {
      elements.push(<p key={idx} className="font-bold mt-3 mb-1 text-lg">{renderInline(trimmed.slice(2))}</p>)
    }
    // Bullet points: * or - or •
    else if (trimmed.startsWith('* ') || trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
      elements.push(
        <div key={idx} className="flex gap-2 ml-2 my-0.5">
          <span className="text-blue-500 dark:text-blue-400 shrink-0">•</span>
          <span>{renderInline(trimmed.slice(2))}</span>
        </div>
      )
    }
    // Numbered list: 1. 2. etc.
    else if (/^\d+[\.\)] /.test(trimmed)) {
      const content = trimmed.replace(/^\d+[\.\)] /, '')
      const num = trimmed.match(/^\d+/)[0]
      elements.push(
        <div key={idx} className="flex gap-2 ml-2 my-0.5">
          <span className="text-blue-500 dark:text-blue-400 font-medium shrink-0">{num}.</span>
          <span>{renderInline(content)}</span>
        </div>
      )
    }
    // Code block
    else if (trimmed.startsWith('```')) {
      // Skip code fence markers
    }
    // Empty line = spacing
    else if (trimmed === '') {
      elements.push(<div key={idx} className="h-2" />)
    }
    // Normal text
    else {
      elements.push(<p key={idx} className="my-0.5">{renderInline(trimmed)}</p>)
    }
  })

  return <div className="space-y-0">{elements}</div>
}

// ─── Shared UI Components ────────────────────────────────────────────────────────

function ResultSection({ title, content }) {
  if (!content) return null
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{title}</h3>
      <p className="text-sm text-gray-900 dark:text-white mt-1">{content}</p>
    </div>
  )
}

function ResultList({ title, items, ordered }) {
  if (!items?.length) return null
  const Tag = ordered ? 'ol' : 'ul'
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">{title}</h3>
      <Tag className={`text-sm text-gray-900 dark:text-white space-y-1 ${ordered ? 'list-decimal' : 'list-disc'} list-inside`}>
        {items.map((item, idx) => <li key={idx}>{item}</li>)}
      </Tag>
    </div>
  )
}

function LoadingCard({ text }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm text-center">
      <div className="animate-spin inline-block w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mb-2" />
      <p className="text-sm text-gray-500 dark:text-gray-400">{text}</p>
    </div>
  )
}
