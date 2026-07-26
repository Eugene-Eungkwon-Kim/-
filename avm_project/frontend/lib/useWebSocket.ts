import { useEffect, useRef, useCallback, useState } from 'react'

interface WebSocketMessage {
  type: string
  timestamp: string
  [key: string]: any
}

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void
  onError?: (error: Event) => void
  onClose?: () => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export const useWebSocket = (
  url: string,
  options: UseWebSocketOptions = {}
) => {
  const {
    onMessage,
    onError,
    onClose,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options

  const ws = useRef<WebSocket | null>(null)
  const reconnectCount = useRef(0)
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)

  const connect = useCallback(() => {
    try {
      const wsUrl = url.replace(/^http/, 'ws')
      ws.current = new WebSocket(wsUrl)

      ws.current.onopen = () => {
        setIsConnected(true)
        setIsReconnecting(false)
        reconnectCount.current = 0
      }

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          if (onMessage) {
            onMessage(message)
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.current.onerror = (error) => {
        setIsConnected(false)
        if (onError) {
          onError(error)
        }
      }

      ws.current.onclose = () => {
        setIsConnected(false)
        if (onClose) {
          onClose()
        }

        // 자동 재연결 로직
        if (reconnectCount.current < maxReconnectAttempts) {
          setIsReconnecting(true)
          reconnectCount.current += 1
          reconnectTimer.current = setTimeout(
            () => {
              connect()
            },
            reconnectInterval * (reconnectCount.current - 1)
          )
        }
      }
    } catch (error) {
      console.error('WebSocket connection error:', error)
      setIsConnected(false)
    }
  }, [url, onMessage, onError, onClose, reconnectInterval, maxReconnectAttempts])

  const send = useCallback((message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(
        typeof message === 'string' ? message : JSON.stringify(message)
      )
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
    }
    if (ws.current) {
      ws.current.close()
      ws.current = null
    }
    setIsConnected(false)
    setIsReconnecting(false)
  }, [])

  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    isConnected,
    isReconnecting,
    send,
    disconnect,
  }
}
